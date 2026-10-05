"""Match Spotify tracks to YouTube Music songs.

A Spotify link carries metadata but no audio we may take, so every Spotify track
has to be identified on YouTube Music before it can be downloaded. Getting that
wrong is worse than failing outright: a silent mismatch fills the library with
covers, live takes and sped-up edits that look correct in the file listing.

So the matcher scores every candidate and returns a confidence alongside each
match. Callers can then route weak matches to review rather than writing them
into the library as though they were certain, which is what makes "why did it
grab the wrong song" debuggable instead of mysterious.

Scoring uses the same rapidfuzz helpers as the album matcher in
:mod:`soundify.lib.matching`, plus duration and video type, which the album path
does not need.
"""

import logging
import re
from dataclasses import dataclass
from enum import StrEnum

from soundify.lib.matching import match_artists, match_title
from soundify.models.enums import VideoType
from soundify.models.ytmusic import SearchResult
from soundify.services.spotify import SpotifyTrack

logger = logging.getLogger(__name__)

# How many candidates to pull per track. The album lookup elsewhere asks for a
# single result, which leaves nothing to compare; matching needs alternatives.
SEARCH_LIMIT = 10

# Score at or above which a match is taken without question.
HIGH_CONFIDENCE_SCORE = 75.0

# Below this a match is not used at all; the track goes to review instead.
MIN_ACCEPTABLE_SCORE = 55.0

# Weights for the three independent signals. They sum to 1.0.
_TITLE_WEIGHT = 0.45
_ARTIST_WEIGHT = 0.35
_DURATION_WEIGHT = 0.20

# Durations within this many seconds are treated as identical.
_DURATION_GRACE_SECONDS = 2

# Each second beyond the grace window costs this much of the duration score.
_DURATION_PENALTY_PER_SECOND = 6.0

# Below this artist similarity the candidate is a different act, however well the
# title matches. Covers and tribute versions share titles but not performers.
_ARTIST_MATCH_FLOOR = 45.0

# Beyond this difference the candidate is a different recording: an extended mix,
# a loop, or a full album upload rather than the single track.
_MAX_DURATION_DIFFERENCE_SECONDS = 25

# Words that mark a different recording of the same song. A candidate carrying
# one the Spotify track does not (or the reverse) is very likely the wrong take.
_VERSION_WORDS = frozenset(
    {
        "live",
        "remix",
        "cover",
        "instrumental",
        "karaoke",
        "acoustic",
        "demo",
        "reprise",
        "slowed",
        "reverb",
        "mashup",
        "8d",
    }
)

_VERSION_MISMATCH_PENALTY = 14.0

# Bonuses and penalties by video type. Art Tracks are the auto-generated
# "- Topic" uploads that correspond to the album audio, so they are what a
# Spotify track should normally resolve to.
_VIDEO_TYPE_ADJUSTMENT = {
    VideoType.ATV: 6.0,
    VideoType.OFFICIAL_SOURCE_MUSIC: 2.0,
    VideoType.OMV: 0.0,
    VideoType.UGC: -12.0,
}

_WORD_PATTERN = re.compile(r"[a-z0-9]+")


class MatchConfidence(StrEnum):
    """How much to trust a match."""

    HIGH = "high"
    LOW = "low"
    NONE = "none"


@dataclass(frozen=True)
class SpotifyMatch:
    """The outcome of matching one Spotify track against YouTube Music.

    Attributes:
        track: The Spotify track that was searched for.
        result: The best candidate found, or None when nothing was acceptable.
        score: Combined score of the best candidate (0-100).
        confidence: Whether the match should be trusted, reviewed, or ignored.
        reason: Short human-readable explanation, shown in logs and the UI.
    """

    track: SpotifyTrack
    result: SearchResult | None
    score: float
    confidence: MatchConfidence
    reason: str

    @property
    def video_id(self) -> str | None:
        """Video ID to download, or None when there is nothing to download."""
        return self.result.video_id if self.result else None


def _words(text: str) -> set[str]:
    """Lowercase word set, used for version-word comparison."""
    return set(_WORD_PATTERN.findall(text.lower()))


def _version_mismatch_penalty(target: str, candidate: str) -> float:
    """Penalise candidates that disagree with the target about the version.

    "Song (Live)" and "Song" are different recordings, and fuzzy title
    similarity alone rates them as nearly identical, so this has to be explicit.

    Args:
        target: Spotify track title.
        candidate: YouTube Music result title.

    Returns:
        Penalty to subtract from the title score.
    """
    target_versions = _words(target) & _VERSION_WORDS
    candidate_versions = _words(candidate) & _VERSION_WORDS
    mismatches = target_versions.symmetric_difference(candidate_versions)
    return len(mismatches) * _VERSION_MISMATCH_PENALTY


def _duration_score(difference: int | None) -> float | None:
    """Score how closely two durations agree.

    Args:
        difference: Absolute difference in seconds, or None when unknown.

    Returns:
        Score from 0-100, or None when the difference is unknown, in which case
        duration is dropped from the weighting rather than guessed at.
    """
    if difference is None:
        return None

    if difference <= _DURATION_GRACE_SECONDS:
        return 100.0

    penalty = (difference - _DURATION_GRACE_SECONDS) * _DURATION_PENALTY_PER_SECOND
    return max(0.0, 100.0 - penalty)


def _video_type_adjustment(video_type: str | None) -> float:
    """Nudge the score by video type, preferring official album audio."""
    if not video_type:
        return 0.0
    try:
        return _VIDEO_TYPE_ADJUSTMENT.get(VideoType(video_type), 0.0)
    except ValueError:
        # A type YouTube Music added since this enum was written.
        return 0.0


def score_candidate(track: SpotifyTrack, result: SearchResult) -> float:
    """Score one YouTube Music candidate against a Spotify track.

    Args:
        track: The Spotify track being matched.
        result: A YouTube Music search result.

    Returns:
        Score from 0-100.
    """
    title_match = match_title(track.title, result.title)
    title_score = max(title_match.similarity, title_match.base_similarity)
    title_score -= _version_mismatch_penalty(track.title, result.title)
    title_score = max(0.0, title_score)

    artist_score = (
        match_artists(set(track.artists), result.artists).best_score
        if track.artists
        else 0.0
    )

    duration_difference = (
        abs(track.duration_seconds - result.duration_seconds)
        if track.duration_seconds and result.duration_seconds
        else None
    )
    duration_score = _duration_score(duration_difference)

    if duration_score is None:
        # Re-spread the duration weight across the signals we actually have.
        total_weight = _TITLE_WEIGHT + _ARTIST_WEIGHT
        score = (
            title_score * _TITLE_WEIGHT + artist_score * _ARTIST_WEIGHT
        ) / total_weight
    else:
        score = (
            title_score * _TITLE_WEIGHT
            + artist_score * _ARTIST_WEIGHT
            + duration_score * _DURATION_WEIGHT
        )

    score += _video_type_adjustment(result.video_type)
    score = max(0.0, min(100.0, score))

    # Hard gates. A different performer or a wildly different length means this
    # is a different recording however well the title matches, and weighted
    # scoring alone cannot express that: a perfect title and artist still leaves
    # enough points to auto-accept an hour-long loop. Cap such candidates below
    # the acceptance threshold so they surface for review instead of being
    # written into the library as though they were correct.
    if track.artists and artist_score < _ARTIST_MATCH_FLOOR:
        return min(score, MIN_ACCEPTABLE_SCORE - 1)

    if (
        duration_difference is not None
        and duration_difference > _MAX_DURATION_DIFFERENCE_SECONDS
    ):
        return min(score, MIN_ACCEPTABLE_SCORE - 1)

    return score


def match_track(track: SpotifyTrack, results: list[SearchResult]) -> SpotifyMatch:
    """Pick the best YouTube Music candidate for a Spotify track.

    Args:
        track: The Spotify track being matched.
        results: Candidates from a YouTube Music song search.

    Returns:
        SpotifyMatch describing the best candidate and how much to trust it.
        Never raises and never silently drops a track: when nothing is good
        enough the match carries MatchConfidence.NONE and an explanation.
    """
    if not results:
        return SpotifyMatch(
            track=track,
            result=None,
            score=0.0,
            confidence=MatchConfidence.NONE,
            reason="no YouTube Music results for this track",
        )

    scored = sorted(
        ((score_candidate(track, r), r) for r in results),
        key=lambda pair: pair[0],
        reverse=True,
    )
    best_score, best_result = scored[0]

    if best_score < MIN_ACCEPTABLE_SCORE:
        return SpotifyMatch(
            track=track,
            result=None,
            score=best_score,
            confidence=MatchConfidence.NONE,
            reason=(
                f"best candidate {best_result.title!r} scored "
                f"{best_score:.0f}, below the {MIN_ACCEPTABLE_SCORE:.0f} minimum"
            ),
        )

    if best_score >= HIGH_CONFIDENCE_SCORE:
        confidence = MatchConfidence.HIGH
        reason = f"matched {best_result.title!r} with score {best_score:.0f}"
    else:
        confidence = MatchConfidence.LOW
        reason = (
            f"matched {best_result.title!r} with score {best_score:.0f}; "
            "verify this is the right version"
        )

    return SpotifyMatch(
        track=track,
        result=best_result,
        score=best_score,
        confidence=confidence,
        reason=reason,
    )


class SpotifyMatcher:
    """Resolves Spotify tracks to YouTube Music video IDs."""

    def __init__(self, client: object, search_limit: int = SEARCH_LIMIT) -> None:
        """Initialize the matcher.

        Args:
            client: YouTube Music client exposing ``search_songs(query, limit)``.
            search_limit: How many candidates to score per track.
        """
        self._client = client
        self._search_limit = search_limit

    def match(self, track: SpotifyTrack) -> SpotifyMatch:
        """Search YouTube Music for a Spotify track and score the candidates.

        Args:
            track: The Spotify track to resolve.

        Returns:
            SpotifyMatch for the track. Search failures become a NONE match
            rather than an exception, so one bad track cannot abort a playlist.
        """
        try:
            results = self._client.search_songs(  # type: ignore[attr-defined]
                track.search_query, limit=self._search_limit
            )
        except Exception as e:  # noqa: BLE001 - one track must not kill the job
            logger.warning("Search failed for %r: %s", track.search_query, e)
            return SpotifyMatch(
                track=track,
                result=None,
                score=0.0,
                confidence=MatchConfidence.NONE,
                reason=f"YouTube Music search failed: {e}",
            )

        match = match_track(track, results)
        logger.debug("Spotify match for %r: %s", track.search_query, match.reason)
        return match
