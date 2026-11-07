"""Tests for SoundCloud links, metadata extraction and source routing."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from conftest import MockYTMusicClient
from soundify.exceptions import PlaylistNotFoundError, UpstreamAPIError
from soundify.models.enums import ContentKind, MusicSource, SkipReason
from soundify.services import MetadataExtractorService
from soundify.services.external import ExternalContent, ExternalTrack
from soundify.services.soundcloud import (
    SoundCloudClient,
    _normalise_artwork,
    _track_from_info,
)
from soundify.services.sources import ExternalSourceReader, is_external_url
from soundify.services.spotify_match import MatchConfidence, SpotifyMatch
from soundify.utils.url import detect_source, is_supported_url, parse_soundcloud_url


class TestParseSoundCloudUrl:
    @pytest.mark.parametrize(
        ("url", "expected"),
        [
            ("https://soundcloud.com/flume/say-nothing-feat-may-a", "track"),
            ("https://m.soundcloud.com/flume/say-nothing-feat-may-a", "track"),
            ("https://soundcloud.com/flume/sets/selected-by-flume", "playlist"),
            ("https://soundcloud.com/flume/sets/selected-by-flume?si=abc", "playlist"),
            ("https://soundcloud.com/flume/some-track/s-AbC123", "track"),
            ("https://soundcloud.com/flume/sets/private-set/s-AbC123", "playlist"),
            ("https://on.soundcloud.com/AbCdEf123", "link"),
        ],
    )
    def test_supported_links(self, url: str, expected: str) -> None:
        assert parse_soundcloud_url(url) == expected

    @pytest.mark.parametrize(
        "url",
        [
            "https://soundcloud.com/flume",
            "https://soundcloud.com/flume/likes",
            "https://soundcloud.com/flume/tracks",
            "https://soundcloud.com/flume/sets",
            "https://soundcloud.com/discover/sets/charts-top:all-music",
            "https://soundcloud.com/search?q=flume",
            "https://soundcloud.com/",
            "https://soundcloud.com/track/xyz/extra/deep",
            "https://notsoundcloud.com/flume/song",
        ],
    )
    def test_unsupported_links(self, url: str) -> None:
        assert parse_soundcloud_url(url) is None


class TestDetectSource:
    @pytest.mark.parametrize(
        ("url", "source"),
        [
            ("https://music.youtube.com/playlist?list=PLabc", MusicSource.YOUTUBE),
            ("https://youtu.be/dQw4w9WgXcQ", MusicSource.YOUTUBE),
            ("https://open.spotify.com/playlist/abc123", MusicSource.SPOTIFY),
            (
                "https://music.apple.com/us/playlist/x/pl.abc",
                MusicSource.APPLE_MUSIC,
            ),
            ("https://soundcloud.com/flume/sets/x", MusicSource.SOUNDCLOUD),
        ],
    )
    def test_known_services(self, url: str, source: MusicSource) -> None:
        assert detect_source(url) is source
        assert is_supported_url(url)

    def test_unknown_link(self) -> None:
        assert detect_source("https://example.com/playlist") is None

    def test_is_external_url(self) -> None:
        assert is_external_url("https://soundcloud.com/flume/sets/x")
        assert is_external_url("https://music.apple.com/us/album/x/1")
        assert not is_external_url("https://music.youtube.com/playlist?list=PLabc")


class TestTrackFromInfo:
    def test_uses_publisher_artists(self) -> None:
        track = _track_from_info(
            {
                "id": 1,
                "title": "The Daisy",
                "artists": ["Ross from Friends"],
                "uploader": "Some Label",
                "duration": 338.2,
            }
        )
        assert track is not None
        assert track.artists == ["Ross from Friends"]
        assert track.duration_ms == 338200

    def test_preview_duration_is_dropped(self) -> None:
        """A 30 second preview says nothing about the real track's length."""
        track = _track_from_info({"id": 1, "title": "Song", "duration": 30.0})
        assert track is not None
        assert track.duration_ms == 0

    def test_short_real_track_keeps_its_duration(self) -> None:
        """A 7 second intro is not a preview; dropping its length let it match
        a full-length song by the same artist."""
        track = _track_from_info({"id": 1, "title": "Intro", "duration": 7.047})
        assert track is not None
        assert track.duration_ms == 7047

    def test_artist_from_title_when_no_publisher_metadata(self) -> None:
        track = _track_from_info(
            {"id": 1, "title": "Fred again.. - Delilah", "uploader": "Repost Channel"}
        )
        assert track is not None
        assert track.artists == ["Fred again.."]
        assert track.title == "Delilah"

    def test_falls_back_to_uploader(self) -> None:
        track = _track_from_info({"id": 1, "title": "Song", "uploader": "Flume"})
        assert track is not None
        assert track.artists == ["Flume"]

    def test_strips_promo_tags(self) -> None:
        track = _track_from_info(
            {"id": 1, "title": "Song (Remix) [Free Download]", "artists": ["A"]}
        )
        assert track is not None
        assert track.title == "Song (Remix)"

    def test_no_title(self) -> None:
        assert _track_from_info({"id": 1}) is None


def test_artwork_is_requested_as_jpeg() -> None:
    assert (
        _normalise_artwork("https://i1.sndcdn.com/artworks-abc-0-original.png")
        == "https://i1.sndcdn.com/artworks-abc-0-t500x500.jpg"
    )
    assert (
        _normalise_artwork("https://example.com/a.png") == "https://example.com/a.png"
    )


def _fake_ydl(info: Any, errors: list[str] | None = None) -> MagicMock:
    """Stand-in for yt_dlp.YoutubeDL that returns ``info`` from extract_info."""

    def factory(opts: dict[str, Any]) -> MagicMock:
        ydl = MagicMock()
        ydl.__enter__.return_value = ydl

        def extract_info(url: str, download: bool) -> Any:
            for message in errors or []:
                opts["logger"].error(message)
            return info

        ydl.extract_info.side_effect = extract_info
        return ydl

    return MagicMock(side_effect=factory)


class TestSoundCloudClient:
    def test_set(self) -> None:
        info = {
            "_type": "playlist",
            "id": "1208852458",
            "title": "Selected By...",
            "uploader": "Flume",
            "album_type": "playlist",
            "playlist_count": 3,
            "entries": [
                {"id": 1, "title": "The Daisy", "artists": ["Ross from Friends"]},
                None,  # a track yt-dlp could not read
                {
                    "id": 3,
                    "title": "Say Nothing",
                    "artists": ["Flume"],
                    "thumbnail": "https://i1.sndcdn.com/artworks-x-original.jpg",
                },
            ],
        }
        with patch("yt_dlp.YoutubeDL", _fake_ydl(info)):
            content = SoundCloudClient().fetch("https://soundcloud.com/flume/sets/x")

        assert content.source is MusicSource.SOUNDCLOUD
        assert content.content_kind is ContentKind.PLAYLIST
        assert [t.title for t in content.tracks] == ["The Daisy", "Say Nothing"]
        assert content.track_count == 3
        assert content.truncated is True
        # No set artwork, so the first track that has some stands in.
        assert content.thumbnail_url == "https://i1.sndcdn.com/artworks-x-t500x500.jpg"

    def test_album_set(self) -> None:
        info = {
            "_type": "playlist",
            "title": "LP",
            "album_type": "album",
            "entries": [],
        }
        with patch("yt_dlp.YoutubeDL", _fake_ydl(info)):
            content = SoundCloudClient().fetch("https://soundcloud.com/a/sets/lp")
        assert content.content_kind is ContentKind.ALBUM

    def test_summary_reads_one_item(self) -> None:
        info = {"_type": "playlist", "title": "LP", "entries": []}
        fake = _fake_ydl(info)
        with patch("yt_dlp.YoutubeDL", fake):
            SoundCloudClient().fetch("https://soundcloud.com/a/sets/lp", summary=True)
        assert fake.call_args.args[0]["playlist_items"] == "1"

    def test_single_track(self) -> None:
        info = {"id": 9, "title": "Say Nothing", "artists": ["Flume"], "duration": 233}
        with patch("yt_dlp.YoutubeDL", _fake_ydl(info)):
            content = SoundCloudClient().fetch("https://soundcloud.com/flume/say")
        assert content.content_kind is ContentKind.TRACK
        assert content.tracks[0].duration_ms == 233000

    def test_not_found(self) -> None:
        fake = _fake_ydl(
            None, errors=["ERROR: [soundcloud] x: HTTP Error 404: Not Found"]
        )
        with patch("yt_dlp.YoutubeDL", fake), pytest.raises(PlaylistNotFoundError):
            SoundCloudClient().fetch("https://soundcloud.com/flume/missing")

    def test_other_failure(self) -> None:
        fake = _fake_ydl(None, errors=["ERROR: Unable to connect"])
        with patch("yt_dlp.YoutubeDL", fake), pytest.raises(UpstreamAPIError):
            SoundCloudClient().fetch("https://soundcloud.com/flume/missing")


class TestExternalSourceReader:
    def test_routes_each_service(self) -> None:
        spotify, apple, soundcloud = MagicMock(), MagicMock(), MagicMock()
        reader = ExternalSourceReader(
            spotify=spotify, apple_music=apple, soundcloud=soundcloud
        )

        reader.fetch("https://open.spotify.com/album/abc123")
        reader.fetch("https://music.apple.com/fr/album/x/123")
        reader.fetch("https://soundcloud.com/a/sets/b", summary=True)

        spotify.fetch.assert_called_once_with("album", "abc123")
        apple.fetch.assert_called_once_with("album", "123", "fr")
        soundcloud.fetch.assert_called_once_with(
            "https://soundcloud.com/a/sets/b", summary=True
        )

    def test_youtube_links_are_not_external(self) -> None:
        reader = ExternalSourceReader(MagicMock(), MagicMock(), MagicMock())
        assert reader.fetch("https://music.youtube.com/playlist?list=PL1") is None


class TestExtractorWithExternalSource:
    def test_unmatched_track_is_reported_and_cover_is_kept(self) -> None:
        """External playlists carry their cover through to the playlist info,
        which is what gets saved as the sidecar cover next to the M3U."""
        track = ExternalTrack(
            source_id="1", title="Obscure", artists=["Nobody"], duration_ms=0
        )
        sources = MagicMock()
        sources.fetch.return_value = ExternalContent(
            source=MusicSource.APPLE_MUSIC,
            kind="playlist",
            source_id="pl.abc",
            title="Road Trip",
            subtitle="Me",
            tracks=[track],
            thumbnail_url="https://example.com/cover.jpg",
        )
        matcher = MagicMock()
        matcher.match.return_value = SpotifyMatch(
            track=track,
            result=None,
            score=0.0,
            confidence=MatchConfidence.NONE,
            reason="nothing",
        )
        extractor = MetadataExtractorService(
            MockYTMusicClient(), sources=sources, matcher=matcher
        )

        progress = list(
            extractor.extract("https://music.apple.com/us/playlist/road/pl.abc")
        )

        assert len(progress) == 1
        info = progress[0].playlist_info
        assert info is not None
        assert info.title == "Road Trip"
        assert info.kind is ContentKind.PLAYLIST
        assert info.cover_url == "https://example.com/cover.jpg"
        assert progress[0].track is None
        assert progress[0].skipped_by_reason == {SkipReason.NO_MATCH: 1}
        assert info.unavailable_tracks[0].title == "Obscure"
