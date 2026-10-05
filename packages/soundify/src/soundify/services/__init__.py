"""Business logic services for soundify.

Public API:
    MetadataExtractorService - Extract metadata from YouTube Music playlists
    PlaylistDownloadService - Full pipeline: extract + download + compose

Protocols (for dependency injection):
    ReplayGainProtocol - ReplayGain tagging abstraction
    PlaylistArtifactsProtocol - Playlist artifact generation abstraction
    DownloaderProtocol - Download backend abstraction
    LyricsServiceProtocol - Lyrics fetching abstraction

Internal (not exported):
    DownloadService, PlaylistArtifactsService - Used internally
    ReplayGainService - rsgain-based ReplayGain implementation
    YTDLPDownloader - yt-dlp download backend implementation
    LyricsService - lrclib.net lyrics fetching
    AudioFileTaggingService, tag_track - Audio file tagging
"""

from soundify.services.extractor import MetadataExtractorService
from soundify.services.playlist_download_service import PlaylistDownloadService

__all__ = [
    "MetadataExtractorService",
    "PlaylistDownloadService",
]
