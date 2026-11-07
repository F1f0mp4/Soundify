"""Tests for Apple Music links and metadata extraction."""

import json
from typing import Any
from unittest.mock import patch

import httpx
import pytest
from soundify.exceptions import PlaylistNotFoundError, UpstreamAPIError
from soundify.models.enums import ContentKind, MusicSource
from soundify.services.apple_music import AppleMusicClient, split_artist_credit
from soundify.utils.url import is_apple_music_url, parse_apple_music_url

ARTWORK_TEMPLATE = (
    "https://is1-ssl.mzstatic.com/image/thumb/a/b/cover.jpg/{w}x{h}bb.{f}"
)


def _response(
    text: str = "", status: int = 200, json_body: Any | None = None
) -> httpx.Response:
    request = httpx.Request("GET", "https://music.apple.com/")
    if json_body is not None:
        return httpx.Response(status, json=json_body, request=request)
    return httpx.Response(status, text=text, request=request)


def _page(header: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    """Build an Apple Music page carrying the given header and track rows."""
    state = {
        "data": [
            {
                "data": {
                    "sections": [
                        {"itemKind": "containerDetailHeaderLockup", "items": [header]},
                        {"itemKind": "trackLockup", "items": rows},
                        {"itemKind": "squareLockup", "items": [{"title": "Ignore"}]},
                    ]
                }
            }
        ]
    }
    return (
        '<html><script type="application/json" id="serialized-server-data">'
        f"{json.dumps(state)}</script></html>"
    )


def _row(title: str, artist: str | None, duration: int, store_id: str) -> dict:
    return {
        "title": title,
        "artistName": artist,
        "duration": duration,
        "showExplicitBadge": False,
        "contentDescriptor": {"identifiers": {"storeAdamID": store_id}},
    }


class TestParseAppleMusicUrl:
    @pytest.mark.parametrize(
        ("url", "expected"),
        [
            (
                "https://music.apple.com/us/album/random-access-memories/617154241",
                ("album", "617154241", "us"),
            ),
            (
                "https://music.apple.com/gb/album/617154241",
                ("album", "617154241", "gb"),
            ),
            (
                "https://music.apple.com/us/song/get-lucky/617154366",
                ("song", "617154366", "us"),
            ),
            (
                "https://music.apple.com/de/album/ram/617154241?i=617154366",
                ("song", "617154366", "de"),
            ),
            (
                "https://music.apple.com/us/playlist/todays-hits/pl.f4d106fed2bd41149aaacabb233eb5eb",
                ("playlist", "pl.f4d106fed2bd41149aaacabb233eb5eb", "us"),
            ),
            (
                "https://music.apple.com/us/playlist/mine/pl.u-8aAVZAxCLgo2Ze",
                ("playlist", "pl.u-8aAVZAxCLgo2Ze", "us"),
            ),
            (
                "https://geo.music.apple.com/album/ram/617154241",
                ("album", "617154241", "us"),
            ),
        ],
    )
    def test_supported_links(self, url: str, expected: tuple[str, str, str]) -> None:
        assert parse_apple_music_url(url) == expected
        assert is_apple_music_url(url)

    @pytest.mark.parametrize(
        "url",
        [
            "https://music.apple.com/us/artist/daft-punk/5468295",
            "https://music.apple.com/us/curator/apple-music-hits/1526756058",
            "https://music.apple.com/us/browse",
            "https://music.apple.com/us/playlist/hits/12345",
            "https://music.apple.com/us/album/ram/pl.abc",
            "https://apple.com/us/album/ram/617154241",
            "",
        ],
    )
    def test_unsupported_links(self, url: str) -> None:
        assert parse_apple_music_url(url) is None


class TestSplitArtistCredit:
    def test_single_act_with_ampersand_is_kept_whole(self) -> None:
        assert split_artist_credit("Simon & Garfunkel") == [
            "Simon & Garfunkel",
            "Simon",
            "Garfunkel",
        ]

    def test_several_artists_keep_full_credit_first(self) -> None:
        assert split_artist_credit("Daft Punk, Pharrell Williams & Nile Rodgers") == [
            "Daft Punk, Pharrell Williams & Nile Rodgers",
            "Daft Punk",
            "Pharrell Williams",
            "Nile Rodgers",
        ]

    def test_single_artist(self) -> None:
        assert split_artist_credit("Daft Punk") == ["Daft Punk"]

    def test_empty(self) -> None:
        assert split_artist_credit(None) == []


class TestAppleMusicClient:
    def test_album_page(self) -> None:
        html = _page(
            {
                "title": "Random Access Memories",
                "subtitleLinks": [{"title": "Daft Punk"}],
                "artwork": {"dictionary": {"url": ARTWORK_TEMPLATE}},
                "trackCount": 2,
            },
            [
                _row("Give Life Back to Music", "Daft Punk", 274403, "1"),
                # Album rows without their own artist inherit the album artist.
                _row("The Game of Love", None, 322149, "2"),
            ],
        )

        with patch("httpx.get", return_value=_response(html)) as get:
            content = AppleMusicClient().fetch("album", "617154241", "us")

        assert get.call_args.args[0] == "https://music.apple.com/us/album/617154241"
        assert content.source is MusicSource.APPLE_MUSIC
        assert content.content_kind is ContentKind.ALBUM
        assert content.title == "Random Access Memories"
        assert content.subtitle == "Daft Punk"
        assert content.thumbnail_url == (
            "https://is1-ssl.mzstatic.com/image/thumb/a/b/cover.jpg/1200x1200bb.jpg"
        )
        assert [t.title for t in content.tracks] == [
            "Give Life Back to Music",
            "The Game of Love",
        ]
        assert content.tracks[1].artists == ["Daft Punk"]
        assert content.tracks[0].duration_seconds == 274
        assert content.truncated is False

    def test_playlist_flags_missing_tracks(self) -> None:
        html = _page(
            {
                "title": "Big List",
                "subtitleLinks": [{"title": "Me"}],
                "trackCount": 300,
            },
            [_row("Song", "Artist", 200000, "1")],
        )

        with patch("httpx.get", return_value=_response(html)):
            content = AppleMusicClient().fetch("playlist", "pl.abc", "us")

        assert content.truncated is True
        assert content.track_count == 300
        assert len(content.tracks) == 1

    def test_song_uses_lookup_api(self) -> None:
        body = {
            "resultCount": 1,
            "results": [
                {
                    "wrapperType": "track",
                    "trackId": 617154366,
                    "trackName": "Get Lucky",
                    "artistName": "Daft Punk",
                    "trackTimeMillis": 369629,
                    "trackExplicitness": "notExplicit",
                    "artworkUrl100": "https://is1-ssl.mzstatic.com/x/100x100bb.jpg",
                }
            ],
        }

        with patch("httpx.get", return_value=_response(json_body=body)) as get:
            content = AppleMusicClient().fetch("song", "617154366", "gb")

        assert get.call_args.kwargs["params"]["country"] == "gb"
        assert content.content_kind is ContentKind.TRACK
        assert content.tracks[0].title == "Get Lucky"
        assert content.tracks[0].duration_ms == 369629
        assert content.thumbnail_url == "https://is1-ssl.mzstatic.com/x/1200x1200bb.jpg"

    def test_song_missing_from_lookup(self) -> None:
        body = {"resultCount": 0, "results": []}
        with (
            patch("httpx.get", return_value=_response(json_body=body)),
            pytest.raises(PlaylistNotFoundError),
        ):
            AppleMusicClient().fetch("song", "1", "us")

    def test_not_found_page(self) -> None:
        with (
            patch("httpx.get", return_value=_response(status=404)),
            pytest.raises(PlaylistNotFoundError),
        ):
            AppleMusicClient().fetch("album", "1", "us")

    def test_page_without_data_is_an_upstream_error(self) -> None:
        with (
            patch("httpx.get", return_value=_response("<html></html>")),
            pytest.raises(UpstreamAPIError),
        ):
            AppleMusicClient().fetch("playlist", "pl.abc", "us")
