"""Data models for soundify.

Public API:
    TrackMetadata - Extracted track metadata (title, artist, album, etc.)
    VideoType - Video type enum (ATV/OMV)
    ContentKind - Content classification (ALBUM/PLAYLIST)

Internal (not exported):
    ytmusic.py - Models for parsing ytmusicapi responses
"""

from soundify.models.enums import ContentKind, VideoType
from soundify.models.track import TrackMetadata

__all__ = [
    "ContentKind",
    "TrackMetadata",
    "VideoType",
]
