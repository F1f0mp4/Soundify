"""URL parsing utilities."""

import re
from urllib.parse import urlparse

from soundify.exceptions import PlaylistParseError
from soundify.models.enums import MusicSource

PLAYLIST_ID_PATTERN = re.compile(r"list=([A-Za-z0-9_-]+)")
VIDEO_ID_PATTERN = re.compile(r"v=([A-Za-z0-9_-]+)")

# Path-based video ID patterns (youtu.be, shorts, live, embed)
_PATH_VIDEO_ID_PATTERN = re.compile(r"^/(?:shorts|live|embed|e|v|vi)/([A-Za-z0-9_-]+)")

# Recognized YouTube hostnames for path-based video ID extraction
_YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
}

# Maximum URL length to prevent potential abuse (standard browser limit)
MAX_URL_LENGTH = 2048

# Spotify entity kinds soundify can resolve. Artist and show links are not
# supported: they have no single track list to work from.
SPOTIFY_KINDS = frozenset({"track", "album", "playlist"})

_SPOTIFY_HOSTS = {"open.spotify.com", "play.spotify.com"}

# spotify:track:ID
_SPOTIFY_URI_PATTERN = re.compile(r"^spotify:(track|album|playlist):([A-Za-z0-9]+)$")

# /track/ID, optionally behind a locale prefix such as /intl-de/
_SPOTIFY_PATH_PATTERN = re.compile(
    r"^/(?:intl-[A-Za-z-]+/)?(track|album|playlist)/([A-Za-z0-9]+)"
)


def parse_spotify_url(url: str) -> tuple[str, str] | None:
    """Extract the entity kind and ID from a Spotify URL or URI.

    Accepts share links carrying the ``?si=`` tracking parameter,
    locale-prefixed links such as ``/intl-de/track/...``, and ``spotify:`` URIs.

    Args:
        url: Spotify URL or URI.

    Returns:
        Tuple of (kind, spotify_id), or None if this is not a supported
        Spotify link.
    """
    if not url or len(url) > MAX_URL_LENGTH:
        return None

    url = url.strip()

    if match := _SPOTIFY_URI_PATTERN.match(url):
        return match.group(1), match.group(2)

    parsed = urlparse(url if "//" in url else f"https://{url}")
    if (parsed.hostname or "").lower() not in _SPOTIFY_HOSTS:
        return None

    if match := _SPOTIFY_PATH_PATTERN.match(parsed.path or ""):
        return match.group(1), match.group(2)

    return None


def is_spotify_url(url: str) -> bool:
    """Check whether a URL points at a supported Spotify entity."""
    return parse_spotify_url(url) is not None


# --- Apple Music ---------------------------------------------------------------

# Apple Music entity kinds soundify can resolve. Artist, curator and station
# pages have no single track list to work from.
APPLE_MUSIC_KINDS = frozenset({"song", "album", "playlist"})

_APPLE_MUSIC_HOSTS = {
    "music.apple.com",
    "geo.music.apple.com",
    "embed.music.apple.com",
    "itunes.apple.com",
}

# /us/album/some-slug/1440857781, /us/album/1440857781, /us/song/slug/1440857786,
# /us/playlist/slug/pl.f4d106fed2bd41149aaacabb233eb5eb (or pl.u-... for user
# playlists). The storefront prefix is optional on some share links.
_APPLE_MUSIC_PATH_PATTERN = re.compile(
    r"^/(?:(?P<storefront>[a-z]{2})/)?(?P<kind>album|song|playlist)"
    r"(?:/[^/]+)?/(?P<id>pl\.[A-Za-z0-9-]+|\d+)/?$"
)

_APPLE_MUSIC_TRACK_PARAM = re.compile(r"(?:^|&)i=(\d+)")

DEFAULT_APPLE_MUSIC_STOREFRONT = "us"


def parse_apple_music_url(url: str) -> tuple[str, str, str] | None:
    """Extract the entity kind, ID and storefront from an Apple Music URL.

    An album link carrying ``?i=SONG_ID`` points at one song on that album, which
    is how the Apple Music app shares a single track, so it is reported as a
    song.

    Args:
        url: Apple Music URL.

    Returns:
        Tuple of (kind, apple_id, storefront), where kind is one of "song",
        "album" or "playlist", or None if this is not a supported Apple Music
        link.
    """
    if not url or len(url) > MAX_URL_LENGTH:
        return None

    url = url.strip()
    parsed = urlparse(url if "//" in url else f"https://{url}")
    if (parsed.hostname or "").lower() not in _APPLE_MUSIC_HOSTS:
        return None

    match = _APPLE_MUSIC_PATH_PATTERN.match(parsed.path or "")
    if not match:
        return None

    kind = match.group("kind")
    apple_id = match.group("id")
    storefront = match.group("storefront") or DEFAULT_APPLE_MUSIC_STOREFRONT

    # Playlist IDs start with "pl."; album and song IDs are numeric.
    if (kind == "playlist") != apple_id.startswith("pl."):
        return None

    if kind == "album" and (track := _APPLE_MUSIC_TRACK_PARAM.search(parsed.query)):
        return "song", track.group(1), storefront

    return kind, apple_id, storefront


def is_apple_music_url(url: str) -> bool:
    """Check whether a URL points at a supported Apple Music entity."""
    return parse_apple_music_url(url) is not None


# --- SoundCloud ----------------------------------------------------------------

_SOUNDCLOUD_HOSTS = {"soundcloud.com", "www.soundcloud.com", "m.soundcloud.com"}
_SOUNDCLOUD_SHORT_HOSTS = {"on.soundcloud.com"}

# First path segments that are SoundCloud pages, not user profiles.
_SOUNDCLOUD_RESERVED_ROOTS = frozenset(
    {
        "discover",
        "stream",
        "search",
        "upload",
        "you",
        "charts",
        "pages",
        "settings",
        "messages",
        "notifications",
        "people",
        "tags",
        "terms-of-use",
        "imprint",
        "jobs",
        "pro",
        "mobile",
        "popular",
        "signin",
        "logout",
    }
)

# Second path segments that are profile tabs rather than a track slug.
_SOUNDCLOUD_PROFILE_TABS = frozenset(
    {
        "likes",
        "tracks",
        "albums",
        "sets",
        "reposts",
        "followers",
        "following",
        "comments",
        "popular-tracks",
        "spotlight",
        "playlists",
    }
)

_SOUNDCLOUD_SLUG = re.compile(r"^[A-Za-z0-9_-]+$")
_SOUNDCLOUD_SECRET = re.compile(r"^s-[A-Za-z0-9]+$")


def parse_soundcloud_url(url: str) -> str | None:
    """Classify a SoundCloud URL as a track or a playlist.

    Accepts track links (``/artist/track``), set links (``/artist/sets/name``,
    which is how SoundCloud stores both playlists and albums), private links
    carrying a ``/s-SECRET`` suffix, and ``on.soundcloud.com`` short links.
    Profiles, likes and other profile tabs are rejected: they are feeds, not a
    fixed track list.

    Args:
        url: SoundCloud URL.

    Returns:
        "track" or "playlist"; "link" for an ``on.soundcloud.com`` short link,
        whose kind is only known once it has been resolved; or None if this is
        not a supported SoundCloud link.
    """
    if not url or len(url) > MAX_URL_LENGTH:
        return None

    url = url.strip()
    parsed = urlparse(url if "//" in url else f"https://{url}")
    host = (parsed.hostname or "").lower()
    segments = [s for s in (parsed.path or "").split("/") if s]

    if host in _SOUNDCLOUD_SHORT_HOSTS:
        return "link" if len(segments) == 1 else None

    if host not in _SOUNDCLOUD_HOSTS or not segments:
        return None

    # Private share links append /s-SECRET to the normal path.
    if len(segments) > 2 and _SOUNDCLOUD_SECRET.match(segments[-1]):
        segments = segments[:-1]

    if not all(_SOUNDCLOUD_SLUG.match(s) for s in segments):
        return None

    user = segments[0].lower()
    if user in _SOUNDCLOUD_RESERVED_ROOTS:
        return None

    match segments:
        case [_, "sets", _]:
            return "playlist"
        case [_, slug] if slug.lower() not in _SOUNDCLOUD_PROFILE_TABS:
            return "track"
        case _:
            return None


def is_soundcloud_url(url: str) -> bool:
    """Check whether a URL points at a supported SoundCloud track or set."""
    return parse_soundcloud_url(url) is not None


def detect_source(url: str) -> MusicSource | None:
    """Work out which service a supported link belongs to.

    Args:
        url: Any URL.

    Returns:
        The service, or None when soundify does not support the link.
    """
    if is_spotify_url(url):
        return MusicSource.SPOTIFY
    if is_apple_music_url(url):
        return MusicSource.APPLE_MUSIC
    if is_soundcloud_url(url):
        return MusicSource.SOUNDCLOUD
    if is_supported_url(url):
        return MusicSource.YOUTUBE
    return None


def _parse_video_id_from_path(url: str) -> str | None:
    """Extract video ID from path-based YouTube URLs.

    Handles youtu.be short URLs and path-based formats like /shorts/, /live/,
    /embed/, /e/, /v/, /vi/ on YouTube domains.

    Args:
        url: Full URL to parse.

    Returns:
        Video ID string, or None if not a recognized path-based URL.
    """
    parsed = urlparse(url)
    host = parsed.hostname or ""
    path = parsed.path or ""

    # youtu.be/VIDEO_ID
    if host == "youtu.be" and len(path) > 1:
        # Path is /VIDEO_ID — strip leading slash
        video_id = path.split("/")[1]
        if re.fullmatch(r"[A-Za-z0-9_-]+", video_id):
            return video_id
        return None

    # /shorts/ID, /live/ID, /embed/ID, /e/ID, /v/ID, /vi/ID on YouTube hosts
    if host in _YOUTUBE_HOSTS:
        if match := _PATH_VIDEO_ID_PATTERN.match(path):
            return match.group(1)

    return None


def parse_playlist_id(url: str) -> str:
    """Extract playlist ID from YouTube Music URL.

    Args:
        url: Full YouTube Music playlist URL.

    Returns:
        The playlist ID string.

    Raises:
        PlaylistParseError: If playlist ID cannot be extracted or URL is too long.
    """
    if not url or len(url) > MAX_URL_LENGTH:
        raise PlaylistParseError(f"Could not extract playlist ID from: {url}")
    if match := PLAYLIST_ID_PATTERN.search(url):
        return match.group(1)
    raise PlaylistParseError(f"Could not extract playlist ID from: {url}")


def parse_video_id(url: str) -> str | None:
    """Extract video ID from a YouTube URL.

    Supports standard watch URLs (v= parameter), youtu.be short URLs,
    and path-based formats (/shorts/, /live/, /embed/, /e/, /v/, /vi/).

    Args:
        url: YouTube, YouTube Music, or youtu.be URL.

    Returns:
        The video ID string, or None if not found or URL is too long.
    """
    # Validate URL length
    if not url or len(url) > MAX_URL_LENGTH:
        return None

    # Extract video ID from v= parameter
    if match := VIDEO_ID_PATTERN.search(url):
        return match.group(1)

    # Extract video ID from path-based URLs (youtu.be, shorts, live, embed)
    return _parse_video_id_from_path(url)


def is_single_track_url(url: str) -> bool:
    """Check if URL is a single track (not a playlist).

    Args:
        url: YouTube or YouTube Music URL.

    Returns:
        True if the URL is a single track URL, False otherwise.
    """
    return parse_video_id(url) is not None


def is_supported_url(url: str) -> bool:
    """Check if URL is supported by soundify (playlist, album, or single track).

    Args:
        url: YouTube, YouTube Music, or Spotify URL.

    Returns:
        True if the URL can be processed by soundify, False otherwise.
    """
    if not url or len(url) > MAX_URL_LENGTH:
        return False

    url = url.strip()

    # Spotify, Apple Music and SoundCloud links, resolved via YouTube Music
    if is_spotify_url(url) or is_apple_music_url(url) or is_soundcloud_url(url):
        return True

    # Playlist URL (has list= parameter)
    if PLAYLIST_ID_PATTERN.search(url):
        return True
    # Single track URL (has v= parameter without list=)
    if VIDEO_ID_PATTERN.search(url):
        return True
    # Path-based video URL (youtu.be, shorts, live, embed)
    if _parse_video_id_from_path(url):
        return True
    # Browse URL (album pages on music.youtube.com)
    parsed = urlparse(url)
    host = parsed.hostname or ""
    path = parsed.path or ""
    if "/browse/" in path and host == "music.youtube.com":
        return True
    return False
