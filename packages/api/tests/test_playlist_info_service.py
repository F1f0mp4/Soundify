"""Tests for PlaylistInfoService."""

from typing import Any
from unittest.mock import MagicMock

import pytest
from soundify import ContentKind
from soundify.models.enums import MusicSource
from soundify.services.apple_music import AppleMusicClient
from soundify.services.external import ExternalContent, ExternalTrack
from soundify.services.soundcloud import SoundCloudClient
from soundify.services.sources import ExternalSourceReader
from soundify.services.spotify import SpotifyEmbedClient
from soundify_api.services.playlist_info_service import PlaylistInfoService

SPOTIFY_SHARE_URL = (
    "https://open.spotify.com/playlist/6NGLj0PxieSRLWZC5eWbkr?si=0rNJRv7oTi6PEkwqxAJAtg"
)
APPLE_PLAYLIST_URL = "https://music.apple.com/us/playlist/todays-hits/pl.f4d106fed2bd41149aaacabb233eb5eb"
SOUNDCLOUD_SET_URL = "https://soundcloud.com/flume/sets/selected-by-flume"


def _content(
    source: MusicSource, kind: str = "playlist", **kwargs: Any
) -> ExternalContent:
    defaults: dict[str, Any] = {
        "source_id": "id1",
        "title": "Long Drives",
        "subtitle": "Some Owner",
        "tracks": [
            ExternalTrack(source_id="t1", title="Song", artists=["A"], duration_ms=1)
        ],
        "thumbnail_url": "https://example.com/cover.jpg",
    }
    return ExternalContent(source=source, kind=kind, **{**defaults, **kwargs})


@pytest.fixture
def spotify_client() -> MagicMock:
    client = MagicMock(spec=SpotifyEmbedClient)
    client.fetch.return_value = _content(
        MusicSource.SPOTIFY,
        source_id="6NGLj0PxieSRLWZC5eWbkr",
        thumbnail_url="https://mosaic.scdn.co/640/abc",
    )
    return client


@pytest.fixture
def apple_client() -> MagicMock:
    client = MagicMock(spec=AppleMusicClient)
    client.fetch.return_value = _content(
        MusicSource.APPLE_MUSIC, title="Today's Hits", total_tracks=50
    )
    return client


@pytest.fixture
def soundcloud_client() -> MagicMock:
    client = MagicMock(spec=SoundCloudClient)
    client.fetch.return_value = _content(
        MusicSource.SOUNDCLOUD, title="Selected By...", total_tracks=27
    )
    return client


@pytest.fixture
def service(
    spotify_client: MagicMock, apple_client: MagicMock, soundcloud_client: MagicMock
) -> PlaylistInfoService:
    return PlaylistInfoService(
        sources=ExternalSourceReader(
            spotify=spotify_client,
            apple_music=apple_client,
            soundcloud=soundcloud_client,
        )
    )


class TestSpotify:
    def test_playlist_metadata_from_share_link(
        self, service: PlaylistInfoService, spotify_client: MagicMock
    ) -> None:
        """Spotify share links must not go through the YouTube list= parser."""
        metadata = service.get_playlist_metadata(SPOTIFY_SHARE_URL)

        spotify_client.fetch.assert_called_once_with(
            "playlist", "6NGLj0PxieSRLWZC5eWbkr"
        )
        assert metadata.title == "Long Drives"
        assert metadata.thumbnail_url == "https://mosaic.scdn.co/640/abc"
        assert metadata.kind == ContentKind.PLAYLIST

    def test_content_info_from_share_link(self, service: PlaylistInfoService) -> None:
        info = service.get_content_info(SPOTIFY_SHARE_URL)

        assert info.title == "Long Drives"
        assert info.artist == "Some Owner"
        assert info.track_count == 1
        assert info.playlist_id == "6NGLj0PxieSRLWZC5eWbkr"
        assert info.kind == ContentKind.PLAYLIST

    def test_spotify_client_argument_still_works(
        self, spotify_client: MagicMock
    ) -> None:
        service = PlaylistInfoService(spotify_client=spotify_client)

        assert service.get_playlist_metadata(SPOTIFY_SHARE_URL).title == "Long Drives"


class TestAppleMusic:
    def test_playlist_metadata(
        self, service: PlaylistInfoService, apple_client: MagicMock
    ) -> None:
        metadata = service.get_playlist_metadata(APPLE_PLAYLIST_URL)

        apple_client.fetch.assert_called_once_with(
            "playlist", "pl.f4d106fed2bd41149aaacabb233eb5eb", "us"
        )
        assert metadata.title == "Today's Hits"
        assert metadata.thumbnail_url == "https://example.com/cover.jpg"

    def test_content_info_uses_declared_track_count(
        self, service: PlaylistInfoService
    ) -> None:
        info = service.get_content_info(APPLE_PLAYLIST_URL)

        assert info.track_count == 50
        assert info.kind == ContentKind.PLAYLIST


class TestSoundCloud:
    def test_metadata_reads_summary_only(
        self, service: PlaylistInfoService, soundcloud_client: MagicMock
    ) -> None:
        """Previews must not pay one request per track on SoundCloud."""
        metadata = service.get_playlist_metadata(SOUNDCLOUD_SET_URL)

        soundcloud_client.fetch.assert_called_once_with(
            SOUNDCLOUD_SET_URL, summary=True
        )
        assert metadata.title == "Selected By..."

    def test_content_info_track_count(self, service: PlaylistInfoService) -> None:
        assert service.get_content_info(SOUNDCLOUD_SET_URL).track_count == 27


class TestSingleTracks:
    def test_external_track_reports_track_kind(
        self, service: PlaylistInfoService, spotify_client: MagicMock
    ) -> None:
        spotify_client.fetch.return_value = _content(MusicSource.SPOTIFY, "track")

        metadata = service.get_playlist_metadata(
            "https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT"
        )

        assert metadata.kind == ContentKind.TRACK

    def test_youtube_watch_link_reports_track_kind(
        self, service: PlaylistInfoService
    ) -> None:
        metadata = service.get_playlist_metadata(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )

        assert metadata.kind == ContentKind.TRACK
