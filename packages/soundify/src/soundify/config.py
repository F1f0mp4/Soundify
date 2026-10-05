"""Configuration for soundify."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class AudioCodec(StrEnum):
    """Supported audio output codecs."""

    OPUS = "opus"
    MP3 = "mp3"
    M4A = "m4a"


@dataclass(frozen=True)
class APIConfig:
    """YouTube Music API configuration.

    Attributes:
        search_limit: Maximum number of search results to return.
        ignore_spelling: Whether to ignore spelling in search queries.
    """

    search_limit: int = 1
    ignore_spelling: bool = True


# Only these two clients serve audio without a PO token. Verified against yt-dlp
# 2026.8.19: tv, tv_simply, android_vr, mweb and ios all return "Requested format
# is not available", while web, web_music and web_creator need a GVS PO token and
# fail with HTTP 403. web_embedded additionally unlocks age-restricted tracks that
# are embeddable, with no account of any kind.
DEFAULT_PLAYER_CLIENTS: tuple[str, ...] = ("visionos", "web_embedded")


@dataclass(frozen=True)
class DownloadConfig:
    """Download service configuration.

    Attributes:
        base_path: Base directory for downloaded files.
        codec: Audio codec for output files.
        quality: Audio quality (0 = best, 10 = worst). Only applies to lossy codecs.
        quiet: Suppress yt-dlp output.
        fetch_lyrics: Whether to fetch lyrics from lrclib.net.
        ytmusic_lyrics_fallback: When fetch_lyrics is enabled, fall back to
            YouTube Music's lyrics if lrclib.net has no match.
        ascii_filenames: Transliterate unicode to ASCII in filenames.
        player_clients: yt-dlp YouTube clients to extract from, in order.
        pot_provider_url: Base URL of a PO token provider (bgutil). When set,
            the mweb client is added, which can serve age-restricted formats.
        sleep_interval: Seconds to sleep between downloads (0 disables).
    """

    base_path: Path
    codec: AudioCodec = AudioCodec.OPUS
    quality: int = 0
    quiet: bool = True
    fetch_lyrics: bool = True
    ytmusic_lyrics_fallback: bool = True
    ascii_filenames: bool = False
    download_ugc: bool = False
    player_clients: tuple[str, ...] = DEFAULT_PLAYER_CLIENTS
    pot_provider_url: str | None = None
    sleep_interval: float = 0.0


@dataclass(frozen=True)
class PlaylistDownloadConfig:
    """Playlist download service configuration.

    Combines download settings with playlist-specific options.

    Attributes:
        download: Download configuration for tracks.
        generate_m3u: Whether to generate M3U playlist file.
        save_cover: Whether to save playlist cover image.
        skip_album_m3u: Skip M3U generation for album playlists.
        max_items: Maximum number of tracks to download.
        apply_replaygain: Whether to apply ReplayGain tags using rsgain.
        cache_path: Directory for extraction cache. None disables caching.
    """

    download: DownloadConfig
    generate_m3u: bool = True
    save_cover: bool = True
    skip_album_m3u: bool = True
    max_items: int | None = None
    apply_replaygain: bool = True
    cache_path: Path | None = None
