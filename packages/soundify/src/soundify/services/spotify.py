"""Spotify metadata extraction via public embed pages.

Why not the official Web API: since February 2026 a Development Mode app only
keeps working while the account that owns it holds a Spotify Premium
subscription, and Spotify-owned editorial playlists (``37i9dQZF1D...``) have
returned 404 for newly created apps since November 2024. The public embed pages
need no credentials, still serve editorial playlists, and carry everything the
matcher needs.

What the embed pages do not carry: ISRC, per-track album names, and track
numbers. That is not a problem here, because album, track number, year and cover
art are taken from YouTube Music once a track has been matched. Spotify only has
to supply title, artists and duration.

Known limit: playlist embeds return at most ``EMBED_TRACK_LIMIT`` tracks, so
longer playlists come back truncated and are flagged as such.
"""

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

import httpx

from soundify.exceptions import (
    PlaylistNotFoundError,
    PlaylistParseError,
    UpstreamAPIError,
)
from soundify.utils.url import SPOTIFY_KINDS

logger = logging.getLogger(__name__)

EMBED_URL = "https://open.spotify.com/embed/{kind}/{spotify_id}"

# Playlist embeds stop after this many entries, regardless of playlist length.
EMBED_TRACK_LIMIT = 100

_NEXT_DATA_PATTERN = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.DOTALL
)


@dataclass(frozen=True)
class SpotifyTrack:
    """A single track as described by Spotify.

    Attributes:
        spotify_id: The Spotify track ID.
        title: Track title.
        artists: Artist names, primary artist first.
        duration_ms: Track duration in milliseconds.
        explicit: Whether Spotify marks the track as explicit.
    """

    spotify_id: str
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
class SpotifyContent:
    """A Spotify track, album or playlist and the tracks it contains.

    Attributes:
        kind: One of "track", "album" or "playlist".
        spotify_id: The Spotify ID of the entity itself.
        title: Display title of the entity.
        subtitle: Album artist for albums, owner for playlists, artists for tracks.
        tracks: The tracks contained in the entity. A single track yields one.
        truncated: True when the embed page hit EMBED_TRACK_LIMIT, meaning tracks
            beyond that limit are missing.
    """

    kind: str
    spotify_id: str
    title: str
    subtitle: str | None
    tracks: list[SpotifyTrack]
    truncated: bool = False


def _split_artists(subtitle: str | None) -> list[str]:
    """Split a Spotify subtitle string into artist names.

    Track rows in an embed carry their artists as one display string. Spotify
    joins them with a comma followed by a non-breaking space, which has to be
    normalised or the trailing name keeps an invisible prefix.

    Args:
        subtitle: Raw subtitle string, e.g. "KAROL G,\xa0Judeline".

    Returns:
        List of artist names, empty when there is nothing to split.
    """
    if not subtitle:
        return []
    normalised = subtitle.replace("\xa0", " ")
    return [name.strip() for name in normalised.split(",") if name.strip()]


def _id_from_uri(uri: str | None) -> str:
    """Extract the bare ID from a Spotify URI such as ``spotify:track:ID``."""
    if not uri:
        return ""
    return uri.rsplit(":", 1)[-1]


def _track_from_entity(entity: dict[str, Any]) -> SpotifyTrack:
    """Build a track from a single-track embed, which has structured artists."""
    artists = [
        name
        for artist in entity.get("artists") or []
        if (name := (artist.get("name") or "").strip())
    ]
    return SpotifyTrack(
        spotify_id=entity.get("id") or _id_from_uri(entity.get("uri")),
        title=entity.get("name") or entity.get("title") or "",
        artists=artists,
        duration_ms=int(entity.get("duration") or 0),
        explicit=bool(entity.get("isExplicit")),
    )


def _track_from_list_item(item: dict[str, Any]) -> SpotifyTrack | None:
    """Build a track from a trackList row, whose artists are a display string.

    Returns:
        The track, or None when the row has no title or ID to work with.
    """
    title = (item.get("title") or "").strip()
    spotify_id = _id_from_uri(item.get("uri"))
    if not title or not spotify_id:
        return None

    return SpotifyTrack(
        spotify_id=spotify_id,
        title=title,
        artists=_split_artists(item.get("subtitle")),
        duration_ms=int(item.get("duration") or 0),
        explicit=bool(item.get("isExplicit")),
    )


class SpotifyEmbedClient:
    """Reads Spotify metadata from public embed pages.

    No credentials, no API keys, and no user account are involved: the embed
    pages are the same ones Spotify serves to anyone embedding a player.
    """

    TIMEOUT = 15.0

    # Spotify serves the embed HTML only to browser-shaped clients.
    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
    )

    def fetch(self, kind: str, spotify_id: str) -> SpotifyContent:
        """Fetch and parse a Spotify entity.

        Args:
            kind: One of "track", "album" or "playlist".
            spotify_id: The Spotify entity ID.

        Returns:
            SpotifyContent with the entity's tracks.

        Raises:
            PlaylistParseError: If the kind is not supported.
            PlaylistNotFoundError: If Spotify has no such entity.
            UpstreamAPIError: If the request fails or the page cannot be parsed.
        """
        if kind not in SPOTIFY_KINDS:
            raise PlaylistParseError(f"Unsupported Spotify content type: {kind}")

        url = EMBED_URL.format(kind=kind, spotify_id=spotify_id)
        logger.debug("Fetching Spotify %s %s", kind, spotify_id)

        try:
            response = httpx.get(
                url,
                headers={"User-Agent": self.USER_AGENT},
                timeout=self.TIMEOUT,
                follow_redirects=True,
            )
            if response.status_code == httpx.codes.NOT_FOUND:
                raise PlaylistNotFoundError(f"Spotify {kind} not found: {spotify_id}")
            response.raise_for_status()
        except httpx.TimeoutException as e:
            raise UpstreamAPIError(f"Spotify request timed out: {url}") from e
        except httpx.HTTPStatusError as e:
            raise UpstreamAPIError(
                f"Spotify returned {e.response.status_code} for {url}"
            ) from e
        except httpx.RequestError as e:
            raise UpstreamAPIError(f"Spotify request failed: {e}") from e

        entity = self._parse_entity(response.text, kind, spotify_id)
        return self._build_content(entity, kind, spotify_id)

    def _parse_entity(self, html: str, kind: str, spotify_id: str) -> dict[str, Any]:
        """Pull the embedded JSON entity out of the page HTML.

        Raises:
            UpstreamAPIError: If the page has no parsable entity, which is how a
                change to Spotify's embed markup will surface.
        """
        match = _NEXT_DATA_PATTERN.search(html)
        if not match:
            raise UpstreamAPIError(
                f"Spotify embed page for {kind} {spotify_id} has no embedded data; "
                "the page format may have changed"
            )

        try:
            payload = json.loads(match.group(1))
            entity = payload["props"]["pageProps"]["state"]["data"]["entity"]
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            raise UpstreamAPIError(
                f"Could not read Spotify {kind} {spotify_id}: {e}"
            ) from e

        if not isinstance(entity, dict):
            raise UpstreamAPIError(f"Unexpected Spotify payload for {spotify_id}")

        return entity

    def _build_content(
        self, entity: dict[str, Any], kind: str, spotify_id: str
    ) -> SpotifyContent:
        """Turn a parsed entity into SpotifyContent."""
        title = entity.get("name") or entity.get("title") or spotify_id

        if kind == "track":
            track = _track_from_entity(entity)
            return SpotifyContent(
                kind=kind,
                spotify_id=spotify_id,
                title=title,
                subtitle=", ".join(track.artists) or None,
                tracks=[track] if track.title else [],
            )

        raw_tracks = entity.get("trackList") or []
        tracks = [
            track
            for item in raw_tracks
            if isinstance(item, dict) and (track := _track_from_list_item(item))
        ]

        truncated = len(raw_tracks) >= EMBED_TRACK_LIMIT
        if truncated:
            logger.warning(
                "Spotify %s %s returned %d tracks; embed pages stop at %d, so any "
                "further tracks are missing",
                kind,
                spotify_id,
                len(raw_tracks),
                EMBED_TRACK_LIMIT,
            )

        return SpotifyContent(
            kind=kind,
            spotify_id=spotify_id,
            title=title,
            subtitle=entity.get("subtitle"),
            tracks=tracks,
            truncated=truncated,
        )
