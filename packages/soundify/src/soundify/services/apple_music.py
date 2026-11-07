"""Apple Music metadata extraction without credentials.

The Apple Music API needs a developer token, which needs a paid Apple Developer
membership. Two public sources carry everything the matcher needs instead:

- Album and playlist pages on music.apple.com embed their full server state as
  JSON (``<script id="serialized-server-data">``), including every track's
  title, artist and duration.
- Single songs are read from the public iTunes Lookup API, which returns the
  same fields as clean JSON and needs no key.

As with Spotify, album, track number, year and cover art are taken from YouTube
Music once a track has been matched, so Apple Music only has to supply title,
artists and duration.

Known limit: very long playlists are served a first page of tracks only. When
the page reports more tracks than it lists, the content is flagged truncated.
"""

import json
import logging
import re
from typing import Any

import httpx

from soundify.exceptions import (
    PlaylistNotFoundError,
    PlaylistParseError,
    UpstreamAPIError,
)
from soundify.models.enums import MusicSource
from soundify.services.external import ExternalContent, ExternalTrack
from soundify.utils.url import APPLE_MUSIC_KINDS

logger = logging.getLogger(__name__)

PAGE_URL = "https://music.apple.com/{storefront}/{kind}/{apple_id}"
LOOKUP_URL = "https://itunes.apple.com/lookup"

# Cover art size requested from Apple's image CDN.
ARTWORK_SIZE = 1200

_SERVER_DATA_PATTERN = re.compile(
    r'<script[^>]*id="serialized-server-data"[^>]*>(.*?)</script>', re.DOTALL
)

# Artwork URLs from the page are templates: .../{w}x{h}bb.{f}
_ARTWORK_TEMPLATE = re.compile(r"\{w\}x\{h\}(\w*)\.\{f\}")

# Lookup API artwork is a fixed 100px image: .../100x100bb.jpg
_LOOKUP_ARTWORK_SIZE = re.compile(r"/\d+x\d+(\w*)\.(\w+)$")

# Apple joins credits as "A, B & C". A lone "&" is ambiguous ("Simon &
# Garfunkel" is one act), so the full credit is always kept alongside the parts.
_ARTIST_SEPARATOR = re.compile(r",\s*|\s+&\s+")


def split_artist_credit(credit: str | None) -> list[str]:
    """Split a display credit into artist names, keeping the full credit first.

    The matcher scores the best pair of names, so keeping the full credit costs
    nothing when it is one act and the parts win when it is several.

    Args:
        credit: Display credit, e.g. "Daft Punk, Pharrell Williams & Nile Rodgers".

    Returns:
        The full credit followed by each individual name, without duplicates.
    """
    if not credit:
        return []
    full = " ".join(credit.replace("\xa0", " ").split())
    parts = [p.strip() for p in _ARTIST_SEPARATOR.split(full) if p.strip()]
    names = [full, *parts] if len(parts) > 1 else [full]
    return list(dict.fromkeys(names))


def _artwork_from_template(artwork: dict[str, Any] | None) -> str | None:
    """Fill in an artwork URL template from the page JSON."""
    url = ((artwork or {}).get("dictionary") or {}).get("url")
    if not isinstance(url, str) or not url:
        return None
    return _ARTWORK_TEMPLATE.sub(
        lambda m: f"{ARTWORK_SIZE}x{ARTWORK_SIZE}{m.group(1) or 'bb'}.jpg", url
    )


def _upscale_lookup_artwork(url: str | None) -> str | None:
    """Ask the image CDN for a larger version of a Lookup API thumbnail."""
    if not url:
        return None
    return _LOOKUP_ARTWORK_SIZE.sub(
        lambda m: f"/{ARTWORK_SIZE}x{ARTWORK_SIZE}{m.group(1)}.{m.group(2)}", url
    )


def _store_id(item: dict[str, Any]) -> str:
    """Read the catalog ID of a page item."""
    descriptor = item.get("contentDescriptor") or {}
    return str((descriptor.get("identifiers") or {}).get("storeAdamID") or "")


class AppleMusicClient:
    """Reads Apple Music metadata from public pages and the iTunes Lookup API."""

    TIMEOUT = 15.0

    # Apple serves the full page markup, including the embedded JSON, only to
    # browser-shaped clients.
    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
    )

    def fetch(self, kind: str, apple_id: str, storefront: str) -> ExternalContent:
        """Fetch and parse an Apple Music song, album or playlist.

        Args:
            kind: One of "song", "album" or "playlist".
            apple_id: The Apple Music catalog ID (``pl.``-prefixed for playlists).
            storefront: Two-letter storefront from the link, e.g. "us".

        Returns:
            ExternalContent with the entity's tracks.

        Raises:
            PlaylistParseError: If the kind is not supported.
            PlaylistNotFoundError: If Apple Music has no such entity.
            UpstreamAPIError: If the request fails or the response cannot be read.
        """
        if kind not in APPLE_MUSIC_KINDS:
            raise PlaylistParseError(f"Unsupported Apple Music content type: {kind}")

        logger.debug("Fetching Apple Music %s %s (%s)", kind, apple_id, storefront)

        if kind == "song":
            return self._fetch_song(apple_id, storefront)

        url = PAGE_URL.format(storefront=storefront, kind=kind, apple_id=apple_id)
        html = self._get(url, kind, apple_id).text
        root = self._parse_page(html, kind, apple_id)
        return self._build_collection(root, kind, apple_id)

    def _get(
        self,
        url: str,
        kind: str,
        apple_id: str,
        params: dict[str, str] | None = None,
    ) -> httpx.Response:
        """GET a URL, translating transport errors into soundify errors."""
        try:
            response = httpx.get(
                url,
                params=params,
                headers={"User-Agent": self.USER_AGENT},
                timeout=self.TIMEOUT,
                follow_redirects=True,
            )
            if response.status_code == httpx.codes.NOT_FOUND:
                raise PlaylistNotFoundError(f"Apple Music {kind} not found: {apple_id}")
            response.raise_for_status()
        except httpx.TimeoutException as e:
            raise UpstreamAPIError(f"Apple Music request timed out: {url}") from e
        except httpx.HTTPStatusError as e:
            raise UpstreamAPIError(
                f"Apple Music returned {e.response.status_code} for {url}"
            ) from e
        except httpx.RequestError as e:
            raise UpstreamAPIError(f"Apple Music request failed: {e}") from e
        return response

    def _fetch_song(self, apple_id: str, storefront: str) -> ExternalContent:
        """Read one song from the iTunes Lookup API."""
        response = self._get(
            LOOKUP_URL,
            "song",
            apple_id,
            params={"id": apple_id, "country": storefront, "entity": "song"},
        )
        try:
            results = response.json().get("results") or []
        except (json.JSONDecodeError, AttributeError) as e:
            raise UpstreamAPIError(f"Could not read Apple Music song {apple_id}") from e

        song = next(
            (
                r
                for r in results
                if isinstance(r, dict)
                and r.get("wrapperType") == "track"
                and str(r.get("trackId")) == apple_id
            ),
            None,
        )
        if song is None:
            raise PlaylistNotFoundError(f"Apple Music song not found: {apple_id}")

        track = ExternalTrack(
            source_id=apple_id,
            title=song.get("trackName") or "",
            artists=split_artist_credit(song.get("artistName")),
            duration_ms=int(song.get("trackTimeMillis") or 0),
            explicit=song.get("trackExplicitness") == "explicit",
        )
        return ExternalContent(
            source=MusicSource.APPLE_MUSIC,
            kind="track",
            source_id=apple_id,
            title=track.title or apple_id,
            subtitle=song.get("artistName"),
            tracks=[track] if track.title else [],
            thumbnail_url=_upscale_lookup_artwork(song.get("artworkUrl100")),
        )

    def _parse_page(self, html: str, kind: str, apple_id: str) -> dict[str, Any]:
        """Pull the embedded server state out of an Apple Music page.

        Raises:
            UpstreamAPIError: If the page has no readable state, which is how a
                change to Apple's page markup will surface.
        """
        match = _SERVER_DATA_PATTERN.search(html)
        if not match:
            raise UpstreamAPIError(
                f"Apple Music page for {kind} {apple_id} has no embedded data; "
                "the page format may have changed"
            )
        try:
            payload = json.loads(match.group(1))
            root = payload["data"][0]["data"]
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as e:
            raise UpstreamAPIError(
                f"Could not read Apple Music {kind} {apple_id}: {e}"
            ) from e

        if not isinstance(root, dict) or not isinstance(root.get("sections"), list):
            raise UpstreamAPIError(f"Unexpected Apple Music payload for {apple_id}")
        return root

    def _build_collection(
        self, root: dict[str, Any], kind: str, apple_id: str
    ) -> ExternalContent:
        """Turn the page state of an album or playlist into ExternalContent."""
        sections = [s for s in root["sections"] if isinstance(s, dict)]

        header: dict[str, Any] = next(
            (
                item
                for s in sections
                if s.get("itemKind") == "containerDetailHeaderLockup"
                for item in s.get("items") or []
                if isinstance(item, dict)
            ),
            {},
        )
        rows = [
            item
            for s in sections
            if s.get("itemKind") == "trackLockup"
            for item in s.get("items") or []
            if isinstance(item, dict)
        ]

        subtitle_links = header.get("subtitleLinks") or []
        subtitle = next(
            (link.get("title") for link in subtitle_links if isinstance(link, dict)),
            None,
        )

        tracks: list[ExternalTrack] = []
        for row in rows:
            title = (row.get("title") or "").strip()
            if not title:
                continue
            # Album rows usually carry their own artist; fall back to the album
            # artist for the ones that do not.
            credit = row.get("artistName") or (subtitle if kind == "album" else None)
            tracks.append(
                ExternalTrack(
                    source_id=_store_id(row),
                    title=title,
                    artists=split_artist_credit(credit),
                    duration_ms=int(row.get("duration") or 0),
                    explicit=bool(row.get("showExplicitBadge")),
                )
            )

        declared = header.get("trackCount")
        total = declared if isinstance(declared, int) else None
        truncated = total is not None and total > len(rows)
        if truncated:
            logger.warning(
                "Apple Music %s %s lists %d of %d tracks; the rest are missing",
                kind,
                apple_id,
                len(rows),
                total,
            )

        return ExternalContent(
            source=MusicSource.APPLE_MUSIC,
            kind=kind,
            source_id=apple_id,
            title=header.get("title") or apple_id,
            subtitle=subtitle,
            tracks=tracks,
            truncated=truncated,
            thumbnail_url=_artwork_from_template(header.get("artwork")),
            total_tracks=total,
        )
