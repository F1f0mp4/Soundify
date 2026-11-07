"""Track lists read from services soundify cannot download audio from.

Spotify, Apple Music and SoundCloud links all work the same way: soundify reads
the track list (title, artists, duration) from the service, then matches each
track to a YouTube Music song and downloads that. This module holds the shape
every one of those readers returns, so the matcher and the extractor do not have
to care which service a link came from.
"""

from dataclasses import dataclass

from soundify.models.enums import ContentKind, MusicSource

# Service-specific entity names mapped onto soundify's own content kinds.
_CONTENT_KINDS = {
    "track": ContentKind.TRACK,
    "song": ContentKind.TRACK,
    "album": ContentKind.ALBUM,
    "playlist": ContentKind.PLAYLIST,
}


@dataclass(frozen=True)
class ExternalTrack:
    """A single track as described by an external service.

    Attributes:
        source_id: The track's ID on that service.
        title: Track title.
        artists: Artist names, primary artist first.
        duration_ms: Track duration in milliseconds, 0 when unknown.
        explicit: Whether the service marks the track as explicit.
    """

    source_id: str
    title: str
    artists: list[str]
    duration_ms: int
    explicit: bool = False

    @property
    def duration_seconds(self) -> int:
        """Duration rounded to whole seconds, for comparison with YouTube Music."""
        return round(self.duration_ms / 1000)

    @property
    def search_query(self) -> str:
        """Query string used to search YouTube Music for this track."""
        primary = self.artists[0] if self.artists else ""
        return f"{primary} {self.title}".strip()


@dataclass(frozen=True)
class ExternalContent:
    """A track, album or playlist on an external service and its tracks.

    Attributes:
        source: The service the content came from.
        kind: One of "track", "album" or "playlist".
        source_id: The ID of the entity itself on that service.
        title: Display title of the entity.
        subtitle: Album artist for albums, owner for playlists, artists for tracks.
        tracks: The tracks contained in the entity. A single track yields one.
            Empty for a summary fetch, which only reads the header.
        truncated: True when the service returned fewer tracks than the entity
            holds, meaning some tracks are missing.
        thumbnail_url: Largest cover art image, if the service carries one.
        total_tracks: Number of tracks the entity holds, when the service says
            so. Falls back to ``len(tracks)``.
    """

    source: MusicSource
    kind: str
    source_id: str
    title: str
    subtitle: str | None
    tracks: list[ExternalTrack]
    truncated: bool = False
    thumbnail_url: str | None = None
    total_tracks: int | None = None

    @property
    def content_kind(self) -> ContentKind:
        """The entity kind in soundify's own terms."""
        return _CONTENT_KINDS.get(self.kind, ContentKind.PLAYLIST)

    @property
    def track_count(self) -> int:
        """How many tracks the entity holds."""
        return self.total_tracks if self.total_tracks is not None else len(self.tracks)
