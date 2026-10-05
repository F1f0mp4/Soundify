"""Tests for matching Spotify tracks to YouTube Music songs."""

from typing import Any

from soundify.models.ytmusic import SearchResult
from soundify.services.spotify import SpotifyTrack
from soundify.services.spotify_match import (
    MIN_ACCEPTABLE_SCORE,
    MatchConfidence,
    SpotifyMatcher,
    match_track,
    score_candidate,
)


def _track(
    title: str = "Paper Skyline",
    artists: list[str] | None = None,
    duration_ms: int = 200_000,
) -> SpotifyTrack:
    return SpotifyTrack(
        spotify_id="sp1",
        title=title,
        artists=["Violet Harbour"] if artists is None else artists,
        duration_ms=duration_ms,
    )


def _result(
    title: str = "Paper Skyline",
    artists: list[str] | None = None,
    duration_seconds: int | None = 200,
    video_type: str = "MUSIC_VIDEO_TYPE_ATV",
    video_id: str = "vid1",
) -> SearchResult:
    payload: dict[str, Any] = {
        "videoId": video_id,
        "videoType": video_type,
        "title": title,
        "artists": [{"name": a} for a in (artists or ["Violet Harbour"])],
        "duration_seconds": duration_seconds,
    }
    return SearchResult.model_validate(payload)


class TestScoreCandidate:
    """Tests for scoring a single candidate."""

    def test_exact_match_scores_very_high(self) -> None:
        assert score_candidate(_track(), _result()) > 95

    def test_wrong_artist_can_never_be_auto_accepted(self) -> None:
        """A perfect title by the wrong act is a cover, not the track."""
        score = score_candidate(_track(), _result(artists=["Someone Else Entirely"]))

        assert score < MIN_ACCEPTABLE_SCORE

    def test_long_upload_can_never_be_auto_accepted(self) -> None:
        """An hour-long upload of a three minute song is a different recording."""
        score = score_candidate(_track(), _result(duration_seconds=3600))

        assert score < MIN_ACCEPTABLE_SCORE

    def test_live_version_is_penalised(self) -> None:
        """A live take of the right song must not outrank the studio cut."""
        studio = score_candidate(_track(), _result())
        live = score_candidate(_track(), _result(title="Paper Skyline (Live)"))

        assert live < studio

    def test_remix_is_penalised(self) -> None:
        original = score_candidate(_track(), _result())
        remix = score_candidate(_track(), _result(title="Paper Skyline (Remix)"))

        assert remix < original

    def test_requested_remix_is_not_penalised(self) -> None:
        """When Spotify asks for the remix, the remix is the correct answer."""
        track = _track(title="Paper Skyline (Remix)")

        remix = score_candidate(track, _result(title="Paper Skyline (Remix)"))
        original = score_candidate(track, _result(title="Paper Skyline"))

        assert remix > original

    def test_duration_mismatch_lowers_score(self) -> None:
        """An hour-long loop of a three minute song is the wrong recording."""
        close = score_candidate(_track(), _result(duration_seconds=201))
        far = score_candidate(_track(), _result(duration_seconds=320))

        assert close > far

    def test_art_track_preferred_over_user_upload(self) -> None:
        atv = score_candidate(_track(), _result(video_type="MUSIC_VIDEO_TYPE_ATV"))
        ugc = score_candidate(_track(), _result(video_type="MUSIC_VIDEO_TYPE_UGC"))

        assert atv > ugc

    def test_missing_duration_does_not_crash(self) -> None:
        """Some results carry no duration; it is dropped, not guessed at."""
        score = score_candidate(_track(), _result(duration_seconds=None))

        assert score > 90

    def test_unknown_video_type_is_neutral(self) -> None:
        score = score_candidate(_track(), _result(video_type="MUSIC_VIDEO_TYPE_NEW"))

        assert score > 90


class TestMatchTrack:
    """Tests for picking the best candidate."""

    def test_no_results_yields_no_match(self) -> None:
        match = match_track(_track(), [])

        assert match.confidence is MatchConfidence.NONE
        assert match.video_id is None
        assert "no YouTube Music results" in match.reason

    def test_picks_highest_scoring_candidate(self) -> None:
        match = match_track(
            _track(),
            [
                _result(title="Paper Skyline (Live)", video_id="live"),
                _result(title="Paper Skyline", video_id="studio"),
            ],
        )

        assert match.video_id == "studio"
        assert match.confidence is MatchConfidence.HIGH

    def test_poor_candidates_are_rejected_with_a_reason(self) -> None:
        """A weak best candidate is reported, not quietly downloaded."""
        match = match_track(
            _track(), [_result(title="Completely Different", artists=["Nobody"])]
        )

        assert match.confidence is MatchConfidence.NONE
        assert match.video_id is None
        assert "below the" in match.reason

    def test_middling_match_is_flagged_for_review(self) -> None:
        """A plausible but imperfect candidate is used, and marked to verify."""
        match = match_track(
            _track(duration_ms=200_000),
            [
                _result(
                    title="Paper Skyline (Live)",
                    artists=["Violet Harbour Trio"],
                    duration_seconds=224,
                    video_type="MUSIC_VIDEO_TYPE_OMV",
                )
            ],
        )

        assert match.confidence is MatchConfidence.LOW
        assert match.video_id == "vid1"
        assert "verify" in match.reason


class _FailingClient:
    def search_songs(self, query: str, limit: int | None = None) -> list[SearchResult]:
        raise RuntimeError("upstream exploded")


class _StubClient:
    def __init__(self, results: list[SearchResult]) -> None:
        self.results = results
        self.limit: int | None = None

    def search_songs(self, query: str, limit: int | None = None) -> list[SearchResult]:
        self.limit = limit
        return self.results


class TestSpotifyMatcher:
    """Tests for the searching wrapper."""

    def test_search_failure_does_not_raise(self) -> None:
        """One failing track must not abort a whole playlist."""
        match = SpotifyMatcher(_FailingClient()).match(_track())

        assert match.confidence is MatchConfidence.NONE
        assert "search failed" in match.reason

    def test_requests_multiple_candidates(self) -> None:
        """Scoring needs alternatives, so more than one result is requested."""
        client = _StubClient([_result()])

        SpotifyMatcher(client, search_limit=7).match(_track())

        assert client.limit == 7
