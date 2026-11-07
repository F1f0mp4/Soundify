"""SoundCloud metadata extraction through yt-dlp.

Why match instead of downloading from SoundCloud directly: a large share of the
label-uploaded catalogue on SoundCloud is DRM protected or served as a 30 second
preview, so its audio cannot be taken. Treating SoundCloud like Spotify (read
the track list, find each track on YouTube Music) gives full-length audio and
the same album tags as every other source.

yt-dlp already ships and maintains a SoundCloud extractor, and is a dependency
anyway, so it is used to read sets and tracks instead of a second scraper.

Preview-only tracks report the preview length (30 seconds) as their duration.
That number says nothing about the real track, so it is dropped and the matcher
falls back to title and artist.
"""

import logging
import re
from typing import Any

import yt_dlp
from yt_dlp.utils import DownloadError as YTDLPDownloadError

from soundify.exceptions import PlaylistNotFoundError, UpstreamAPIError
from soundify.models.enums import MusicSource
from soundify.services.apple_music import split_artist_credit
from soundify.services.external import ExternalContent, ExternalTrack

logger = logging.getLogger(__name__)

# SoundCloud previews are cut at this length. A reported duration of exactly
# this is the preview, not the track.
_PREVIEW_SECONDS = 30.0
_PREVIEW_TOLERANCE = 0.5

# Set types SoundCloud uses for releases rather than user playlists.
_ALBUM_SET_TYPES = frozenset({"album", "ep", "single", "compilation"})

# Promotional tags uploaders add to titles: "[Free Download]", "(OUT NOW)", ...
_PROMO_TAG = re.compile(
    r"\s*[\[(](?:[^\])]*\b(?:free\s*(?:download|dl)|out\s*now|premiere|"
    r"buy\s*=?\s*free|click\s*buy)\b[^\])]*)[\])]",
    re.IGNORECASE,
)

# Uploads by labels and channels put the artist in the title: "Artist - Title".
_ARTIST_TITLE = re.compile(r"^(?P<artist>.+?)\s+[-\u2013\u2014]\s+(?P<title>.+)$")


class _QuietLogger:
    """Routes yt-dlp output to the debug log instead of stdout.

    With ``ignoreerrors`` set, yt-dlp reports a failed top-level lookup only
    through its logger, so the errors are kept to explain an empty result.
    """

    def __init__(self) -> None:
        self.errors: list[str] = []

    def debug(self, msg: str) -> None:
        logger.debug("yt-dlp: %s", msg)

    def info(self, msg: str) -> None:
        logger.debug("yt-dlp: %s", msg)

    def warning(self, msg: str) -> None:
        logger.debug("yt-dlp: %s", msg)

    def error(self, msg: str) -> None:
        self.errors.append(msg)
        logger.debug("yt-dlp: %s", msg)


def _clean_title(title: str) -> str:
    """Strip promotional tags that would only confuse the search."""
    return " ".join(_PROMO_TAG.sub("", title).split())


def _track_from_info(info: dict[str, Any]) -> ExternalTrack | None:
    """Build a track from a yt-dlp SoundCloud track info dict.

    Returns:
        The track, or None when the entry has no title to search for.
    """
    raw_title = info.get("track") or info.get("title") or ""
    title = _clean_title(raw_title)
    if not title:
        return None

    artists = [a for a in info.get("artists") or [] if a]
    if not artists and info.get("artist"):
        artists = split_artist_credit(info["artist"])

    if not artists and (match := _ARTIST_TITLE.match(title)):
        # No publisher metadata, so the uploader may be a label or a reposting
        # channel. "Artist - Title" in the title is the better signal.
        artists = split_artist_credit(match.group("artist"))
        title = match.group("title").strip()

    if not artists and info.get("uploader"):
        artists = [info["uploader"]]

    duration = info.get("duration") or 0
    # Only the preview length itself is suspect. Short real tracks (intros,
    # skits) keep their duration, which is what stops them matching a full song.
    is_preview = abs(duration - _PREVIEW_SECONDS) <= _PREVIEW_TOLERANCE
    duration_ms = 0 if is_preview else round(duration * 1000)

    return ExternalTrack(
        source_id=str(info.get("id") or ""),
        title=title,
        artists=artists,
        duration_ms=duration_ms,
    )


# SoundCloud artwork sizes: ...-original.png, ...-large.jpg, ...-t500x500.jpg
_ARTWORK_SIZE_SUFFIX = re.compile(r"-(?:original|large|t\d+x\d+|crop)\.(?:jpe?g|png)$")


def _normalise_artwork(url: str) -> str:
    """Request the 500px JPEG rendition of a SoundCloud artwork URL.

    Originals can be PNGs of any size, which would land in a ``.jpg`` cover
    file. The CDN renders every artwork as a 500px JPEG on request.
    """
    if "sndcdn.com" not in url:
        return url
    return _ARTWORK_SIZE_SUFFIX.sub("-t500x500.jpg", url)


def _thumbnail(info: dict[str, Any]) -> str | None:
    """Pick the largest thumbnail yt-dlp reports, as a JPEG."""
    if info.get("thumbnail"):
        return _normalise_artwork(info["thumbnail"])
    thumbnails = [t for t in info.get("thumbnails") or [] if t.get("url")]
    if not thumbnails:
        return None
    best = max(thumbnails, key=lambda t: (t.get("width") or 0, t.get("preference", 0)))
    return _normalise_artwork(best["url"])


def _translate_error(
    message: str, url: str
) -> PlaylistNotFoundError | UpstreamAPIError:
    """Map a yt-dlp error message onto a soundify error."""
    if "404" in message or "Not Found" in message:
        return PlaylistNotFoundError(f"SoundCloud link not found: {url}")
    detail = message.removeprefix("ERROR: ").strip() or "no data returned"
    return UpstreamAPIError(f"Could not read SoundCloud link {url}: {detail}")


class SoundCloudClient:
    """Reads SoundCloud tracks and sets through yt-dlp."""

    def fetch(self, url: str, *, summary: bool = False) -> ExternalContent:
        """Fetch and parse a SoundCloud track or set.

        Args:
            url: SoundCloud track, set or ``on.soundcloud.com`` short link.
            summary: Read only the header and the first track, which is enough
                for a title, cover and track count. Reading every track costs
                one request per track.

        Returns:
            ExternalContent with the entity's tracks (only the first one for a
            summary).

        Raises:
            PlaylistNotFoundError: If SoundCloud has no such track or set.
            UpstreamAPIError: If SoundCloud cannot be reached or read.
        """
        ytdlp_logger = _QuietLogger()
        opts: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "logger": ytdlp_logger,
            # DRM-protected and preview-only tracks have no usable formats, but
            # their metadata is all that is needed here.
            "ignore_no_formats_error": True,
            # One unreadable track must not fail the whole set.
            "ignoreerrors": True,
        }
        if summary:
            opts["playlist_items"] = "1"

        logger.debug("Fetching SoundCloud %s (summary=%s)", url, summary)

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:  # type: ignore[arg-type]
                info = ydl.extract_info(url, download=False)
        except YTDLPDownloadError as e:
            raise _translate_error(str(e), url) from e

        if not isinstance(info, dict):
            message = ytdlp_logger.errors[-1] if ytdlp_logger.errors else ""
            raise _translate_error(message, url)

        return self._build_content(dict(info), url, summary=summary)

    def _build_content(
        self, info: dict[str, Any], url: str, *, summary: bool = False
    ) -> ExternalContent:
        """Turn a yt-dlp info dict into ExternalContent."""
        if info.get("_type") != "playlist":
            track = _track_from_info(info)
            return ExternalContent(
                source=MusicSource.SOUNDCLOUD,
                kind="track",
                source_id=str(info.get("id") or url),
                title=track.title if track else info.get("title") or url,
                subtitle=", ".join(track.artists[:1]) if track else None,
                tracks=[track] if track else [],
                thumbnail_url=_thumbnail(info),
            )

        entries = [e for e in info.get("entries") or [] if isinstance(e, dict)]
        tracks = [t for e in entries if (t := _track_from_info(e))]

        set_type = (info.get("album_type") or "").lower()
        kind = "album" if set_type in _ALBUM_SET_TYPES else "playlist"

        declared = info.get("playlist_count")
        total = declared if isinstance(declared, int) else None

        # Tracks yt-dlp could not read come back as None and are dropped above.
        truncated = not summary and total is not None and len(tracks) < total
        if truncated:
            logger.warning(
                "SoundCloud set %s: read %d of %d tracks; the rest could not be read",
                url,
                len(tracks),
                total,
            )

        return ExternalContent(
            source=MusicSource.SOUNDCLOUD,
            kind=kind,
            source_id=str(info.get("id") or url),
            title=info.get("title") or url,
            subtitle=info.get("uploader"),
            tracks=tracks,
            truncated=truncated,
            # Sets carry no cover of their own when the uploader did not set
            # one; the first track's artwork is what SoundCloud shows instead.
            thumbnail_url=_thumbnail(info)
            or next((_thumbnail(e) for e in entries if _thumbnail(e)), None),
            total_tracks=total,
        )
