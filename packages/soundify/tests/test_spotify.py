"""Tests for Spotify metadata extraction via embed pages."""

import json
from typing import Any
from unittest.mock import patch

import httpx
import pytest
from soundify.exceptions import (
    PlaylistNotFoundError,
    PlaylistParseError,
    UpstreamAPIError,
)
from soundify.services.spotify import (
    EMBED_TRACK_LIMIT,
    SpotifyEmbedClient,
    _split_artists,
)
from soundify.utils.url import is_spotify_url, parse_spotify_url


def _embed_html(entity: dict[str, Any]) -> str:
    """Build an embed page carrying the given entity, as Spotify serves it."""
    payload = {"props": {"pageProps": {"state": {"data": {"entity": entity}}}}}
    return (
        "<html><body>"
        '<script id="__NEXT_DATA__" type="application/json">'
        f"{json.dumps(payload)}"
        "</script></body></html>"
    )


def _response(html: str, status_code: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code,
        text=html,
        request=httpx.Request("GET", "https://open.spotify.com/embed/track/x"),
    )


class TestParseSpotifyUrl:
    """Tests for Spotify URL and URI parsing."""

    @pytest.mark.parametrize(
        ("url", "expected"),
        [
            (
                "https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT",
                ("track", "4cOdK2wGLETKBW3PvgPWqT"),
            ),
            # Share links carry a tracking parameter
            (
                "https://open.spotify.com/album/1ATL5GLyefJaxhQzSPVrLX?si=abc123",
                ("album", "1ATL5GLyefJaxhQzSPVrLX"),
            ),
            # Localised links are served with a locale prefix
            (
                "https://open.spotify.com/intl-de/playlist/37i9dQZF1DXcBWIGoYBM5M",
                ("playlist", "37i9dQZF1DXcBWIGoYBM5M"),
            ),
            (
                "spotify:track:4cOdK2wGLETKBW3PvgPWqT",
                ("track", "4cOdK2wGLETKBW3PvgPWqT"),
            ),
        ],
    )
    def test_parses_supported_links(self, url: str, expected: tuple[str, str]) -> None:
        assert parse_spotify_url(url) == expected

    @pytest.mark.parametrize(
        "url",
        [
            "https://music.youtube.com/watch?v=20UpB7XwQv4",
            # Artists have no single track list, so they are not supported
            "https://open.spotify.com/artist/0gxyHStUsqpMadRV0Di1Qt",
            "https://evil.example.com/track/abc",
            "",
        ],
    )
    def test_rejects_unsupported_links(self, url: str) -> None:
        assert parse_spotify_url(url) is None
        assert is_spotify_url(url) is False

    def test_rejects_overlong_url(self) -> None:
        assert parse_spotify_url("https://open.spotify.com/track/" + "a" * 3000) is None


class TestSplitArtists:
    """Tests for turning a subtitle string into artist names."""

    def test_splits_on_non_breaking_spaces(self) -> None:
        """Spotify joins artists with a comma and a non-breaking space."""
        assert _split_artists("KAROL G,\xa0Judeline,\xa0rusowsky") == [
            "KAROL G",
            "Judeline",
            "rusowsky",
        ]

    def test_handles_single_artist(self) -> None:
        assert _split_artists("Drake") == ["Drake"]

    def test_handles_missing_subtitle(self) -> None:
        assert _split_artists(None) == []
        assert _split_artists("") == []


class TestSpotifyEmbedClient:
    """Tests for fetching and parsing embed pages."""

    def test_fetches_single_track(self) -> None:
        """A track page exposes structured artists rather than a subtitle."""
        entity = {
            "type": "track",
            "id": "4cOdK2wGLETKBW3PvgPWqT",
            "name": "Never Gonna Give You Up",
            "uri": "spotify:track:4cOdK2wGLETKBW3PvgPWqT",
            "duration": 213573,
            "isExplicit": False,
            "artists": [{"name": "Rick Astley"}],
        }

        with patch("httpx.get", return_value=_response(_embed_html(entity))):
            content = SpotifyEmbedClient().fetch("track", "4cOdK2wGLETKBW3PvgPWqT")

        assert content.kind == "track"
        assert content.title == "Never Gonna Give You Up"
        assert len(content.tracks) == 1

        track = content.tracks[0]
        assert track.artists == ["Rick Astley"]
        assert track.duration_ms == 213573
        assert track.duration_seconds == 214
        assert track.search_query == "Rick Astley Never Gonna Give You Up"
        assert content.truncated is False

    def test_fetches_album_track_list(self) -> None:
        entity = {
            "type": "album",
            "id": "album1",
            "name": "Scorpion",
            "subtitle": "Drake",
            "trackList": [
                {
                    "uri": "spotify:track:t1",
                    "title": "Survival",
                    "subtitle": "Drake",
                    "duration": 136186,
                    "isExplicit": True,
                },
                {
                    "uri": "spotify:track:t2",
                    "title": "Nonstop",
                    "subtitle": "Drake",
                    "duration": 238640,
                    "isExplicit": True,
                },
            ],
        }

        with patch("httpx.get", return_value=_response(_embed_html(entity))):
            content = SpotifyEmbedClient().fetch("album", "album1")

        assert content.subtitle == "Drake"
        assert [t.title for t in content.tracks] == ["Survival", "Nonstop"]
        assert content.tracks[0].spotify_id == "t1"
        assert content.tracks[0].explicit is True
        assert content.truncated is False

    def test_flags_truncated_playlists(self) -> None:
        """Playlist embeds stop at 100 tracks, which must not pass unnoticed."""
        entity = {
            "type": "playlist",
            "id": "p1",
            "name": "Rock Classics",
            "subtitle": "Spotify",
            "trackList": [
                {
                    "uri": f"spotify:track:t{i}",
                    "title": f"Song {i}",
                    "subtitle": "Someone",
                    "duration": 200000,
                }
                for i in range(EMBED_TRACK_LIMIT)
            ],
        }

        with patch("httpx.get", return_value=_response(_embed_html(entity))):
            content = SpotifyEmbedClient().fetch("playlist", "p1")

        assert len(content.tracks) == EMBED_TRACK_LIMIT
        assert content.truncated is True

    def test_skips_rows_without_a_usable_id(self) -> None:
        entity = {
            "type": "playlist",
            "id": "p1",
            "name": "Mixed",
            "trackList": [
                {"uri": "spotify:track:t1", "title": "Good", "duration": 1000},
                {"uri": "", "title": "No id", "duration": 1000},
                {"uri": "spotify:track:t3", "title": "", "duration": 1000},
            ],
        }

        with patch("httpx.get", return_value=_response(_embed_html(entity))):
            content = SpotifyEmbedClient().fetch("playlist", "p1")

        assert [t.title for t in content.tracks] == ["Good"]

    def test_rejects_unsupported_kind(self) -> None:
        with pytest.raises(PlaylistParseError):
            SpotifyEmbedClient().fetch("artist", "abc")

    def test_missing_entity_raises_upstream_error(self) -> None:
        """A changed embed format should fail loudly, not silently return nothing."""
        with patch("httpx.get", return_value=_response("<html>no data here</html>")):
            with pytest.raises(UpstreamAPIError, match="no embedded data"):
                SpotifyEmbedClient().fetch("track", "abc")

    def test_not_found_raises_playlist_not_found(self) -> None:
        with patch("httpx.get", return_value=_response("", status_code=404)):
            with pytest.raises(PlaylistNotFoundError):
                SpotifyEmbedClient().fetch("album", "missing")

    def test_timeout_raises_upstream_error(self) -> None:
        with patch("httpx.get", side_effect=httpx.TimeoutException("slow")):
            with pytest.raises(UpstreamAPIError, match="timed out"):
                SpotifyEmbedClient().fetch("track", "abc")
