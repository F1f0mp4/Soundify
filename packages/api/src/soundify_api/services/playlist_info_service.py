"""Service for fetching playlist information from any supported service."""

import logging
from dataclasses import dataclass
from pathlib import Path

from soundify import ContentKind, parse_playlist_id
from soundify.client import YTMusicClient
from soundify.models.ytmusic import Playlist
from soundify.services.external import ExternalContent
from soundify.services.sources import ExternalSourceReader
from soundify.services.spotify import SpotifyEmbedClient
from soundify.utils.url import PLAYLIST_ID_PATTERN, parse_video_id

from soundify_api.domain.job import ContentInfo

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PlaylistMetadata:
    """Metadata about a playlist.

    Attributes:
        title: Display title.
        thumbnail_url: Cover image, if any.
        kind: Whether the link is a playlist, an album or a single track.
            Subscriptions only make sense for the first two.
    """

    title: str
    thumbnail_url: str | None
    kind: ContentKind = ContentKind.PLAYLIST


@dataclass(frozen=True)
class _Classification:
    """Result of classifying a playlist as album or regular playlist."""

    kind: ContentKind
    year: int | None = None
    artist: str | None = None
    thumbnail_url: str | None = None


class PlaylistInfoService:
    """Service to fetch playlist metadata from any supported service.

    YouTube and YouTube Music links are read through ytmusicapi; Spotify, Apple
    Music and SoundCloud links through their own readers.
    """

    def __init__(
        self,
        cookies_path: Path | None = None,
        spotify_client: SpotifyEmbedClient | None = None,
        sources: ExternalSourceReader | None = None,
    ) -> None:
        """Initialize the service.

        Args:
            cookies_path: Optional path to cookies.txt for authenticated requests.
            spotify_client: Reads metadata from Spotify links. Ignored when
                ``sources`` is given.
            sources: Reads Spotify, Apple Music and SoundCloud links. Defaults
                to the built-in readers.
        """
        self._client = YTMusicClient(cookies_path=cookies_path)
        self._sources = sources or ExternalSourceReader(spotify=spotify_client)

    def get_playlist_metadata(self, url: str) -> PlaylistMetadata:
        """Get the metadata of a playlist from its URL.

        Args:
            url: YouTube, YouTube Music, Spotify, Apple Music or SoundCloud URL.

        Returns:
            PlaylistMetadata containing title, thumbnail URL and kind.

        Raises:
            PlaylistParseError: If URL cannot be parsed (400).
            PlaylistNotFoundError: If playlist doesn't exist (404).
            AuthenticationRequiredError: If authentication is required (401).
            UnsupportedPlaylistError: If playlist type is not supported (422).
            UpstreamAPIError: If API request fails (502).
        """
        if external := self._fetch_external(url):
            return PlaylistMetadata(
                title=external.title,
                thumbnail_url=external.thumbnail_url,
                kind=external.content_kind,
            )

        if parse_video_id(url) and not PLAYLIST_ID_PATTERN.search(url):
            return PlaylistMetadata(
                title=url, thumbnail_url=None, kind=ContentKind.TRACK
            )

        playlist_id = parse_playlist_id(url)
        playlist = self._client.get_playlist(playlist_id)
        title = playlist.title or "Unknown Playlist"
        thumbnail_url = playlist.thumbnails[-1].url if playlist.thumbnails else None
        return PlaylistMetadata(title=title, thumbnail_url=thumbnail_url)

    def get_content_info(self, url: str) -> ContentInfo:
        """Get content info for any supported URL.

        Returns quick metadata (title, artist, kind, track count, year,
        thumbnail) from a single API call without running the full
        extraction pipeline.

        Args:
            url: YouTube, YouTube Music, Spotify, Apple Music or SoundCloud URL
                (playlist, album, or single track).

        Returns:
            ContentInfo with metadata from the URL.

        Raises:
            PlaylistParseError: If URL cannot be parsed (400).
            TrackParseError: If single track URL is invalid (400).
            PlaylistNotFoundError: If playlist doesn't exist (404).
            TrackNotFoundError: If track doesn't exist (404).
            AuthenticationRequiredError: If authentication is required (401).
            UnsupportedPlaylistError: If playlist type is not supported (422).
            UpstreamAPIError: If API request fails (502).
        """
        if external := self._fetch_external(url):
            return ContentInfo(
                title=external.title,
                artist=external.subtitle or "Unknown Artist",
                track_count=external.track_count,
                playlist_id=external.source_id,
                url=url,
                thumbnail_url=external.thumbnail_url,
                kind=external.content_kind,
            )

        video_id = parse_video_id(url)
        if video_id:
            return self._get_track_content_info(video_id, url)
        return self._get_playlist_content_info(url)

    def _fetch_external(self, url: str) -> ExternalContent | None:
        """Fetch the header of an external link, or None for YouTube links.

        Only the title, cover, kind and track count are read here, so readers
        that pay per track can skip the track list.
        """
        return self._sources.fetch(url, summary=True)

    def _get_playlist_content_info(self, url: str) -> ContentInfo:
        """Build ContentInfo from a playlist/album URL."""
        playlist_id = parse_playlist_id(url)
        playlist = self._client.get_playlist(playlist_id)

        cls = self._classify(playlist)

        return ContentInfo(
            title=playlist.title or "Unknown",
            artist=cls.artist
            or (playlist.author.name if playlist.author else "Unknown Artist"),
            year=cls.year,
            track_count=len(playlist.tracks),
            playlist_id=playlist_id,
            url=url,
            thumbnail_url=cls.thumbnail_url
            or (playlist.thumbnails[-1].url if playlist.thumbnails else None),
            kind=cls.kind,
        )

    def _classify(self, playlist: Playlist) -> "_Classification":
        """Classify playlist as album or playlist and extract metadata.

        Uses the same logic as the regular extraction flow:
        1. All tracks must reference the same album ID
        2. The album must be fetchable
        3. The playlist must contain all album tracks

        For confirmed albums, also extracts artist and thumbnail from the
        album object (since album playlists have no author or thumbnails).

        Returns:
            Classification result with kind, year, artist, and thumbnail.
        """
        if not playlist.tracks:
            return _Classification(kind=ContentKind.PLAYLIST)

        # Check if all tracks reference the same album
        album_ids = {t.album.id for t in playlist.tracks if t.album and t.album.id}
        if len(album_ids) != 1:
            return _Classification(kind=ContentKind.PLAYLIST)

        album_id = next(iter(album_ids))
        try:
            album = self._client.get_album(album_id)
        except Exception:
            logger.debug("Could not fetch album %s for classification", album_id)
            return _Classification(kind=ContentKind.PLAYLIST)

        # Verify playlist contains all album tracks
        if len(playlist.tracks) != len(album.tracks):
            return _Classification(kind=ContentKind.PLAYLIST)

        year = None
        if album.year:
            try:
                year = int(album.year)
            except ValueError:
                pass

        artist = album.artists[0].name if album.artists else None
        thumbnail_url = album.thumbnails[-1].url if album.thumbnails else None

        return _Classification(
            kind=ContentKind.ALBUM,
            year=year,
            artist=artist,
            thumbnail_url=thumbnail_url,
        )

    def _get_track_content_info(self, video_id: str, url: str) -> ContentInfo:
        """Build ContentInfo from a single track URL."""
        track = self._client.get_track(video_id)

        return ContentInfo(
            title=track.title,
            artist=(track.artists[0].name if track.artists else "Unknown Artist"),
            playlist_id=video_id,
            url=url,
            thumbnail_url=(track.thumbnails[-1].url if track.thumbnails else None),
            kind=ContentKind.TRACK,
        )
