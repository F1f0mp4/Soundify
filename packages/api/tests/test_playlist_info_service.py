"""Tests for PlaylistInfoService."""

from unittest.mock import MagicMock

import pytest
from soundify import ContentKind
from soundify.services.spotify import SpotifyContent, SpotifyEmbedClient, SpotifyTrack
from soundify_api.services.playlist_info_service import PlaylistInfoService

SPOTIFY_SHARE_URL = (
    "https://open.spotify.com/playlist/6NGLj0PxieSRLWZC5eWbkr?si=0rNJRv7oTi6PEkwqxAJAtg"
)


@pytest.fixture
def spotify_client() -> MagicMock:
    client = MagicMock(spec=SpotifyEmbedClient)
    client.fetch.return_value = SpotifyContent(
        kind="playlist",
        spotify_id="6NGLj0PxieSRLWZC5eWbkr",
        title="Long Drives",
        subtitle="Some Owner",
        tracks=[
            SpotifyTrack(spotify_id="t1", title="Song", artists=["A"], duration_ms=1)
        ],
        thumbnail_url="https://mosaic.scdn.co/640/abc",
    )
    return client


@pytest.fixture
def service(spotify_client: MagicMock) -> PlaylistInfoService:
    return PlaylistInfoService(spotify_client=spotify_client)


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

    def test_content_info_from_share_link(self, service: PlaylistInfoService) -> None:
        info = service.get_content_info(SPOTIFY_SHARE_URL)

        assert info.title == "Long Drives"
        assert info.artist == "Some Owner"
        assert info.track_count == 1
        assert info.playlist_id == "6NGLj0PxieSRLWZC5eWbkr"
        assert info.kind == ContentKind.PLAYLIST
