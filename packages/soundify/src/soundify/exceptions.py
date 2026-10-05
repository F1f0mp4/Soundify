"""Custom exceptions for soundify."""


class SoundifyError(Exception):
    """Base exception for soundify."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class PlaylistParseError(SoundifyError):
    """Failed to parse playlist URL.

    Raised when the provided URL doesn't contain a valid playlist ID.
    """


class TrackParseError(SoundifyError):
    """Failed to parse track URL.

    Raised when the provided URL doesn't contain a valid video ID,
    or when a playlist URL is provided instead of a single track URL.
    """


class PlaylistNotFoundError(SoundifyError):
    """Playlist not found or inaccessible.

    Raised when the playlist doesn't exist or is private.
    """


class TrackNotFoundError(SoundifyError):
    """Track not found or inaccessible.

    Raised when the track doesn't exist, has been removed, or is
    region-restricted and not available.
    """


class AuthenticationRequiredError(SoundifyError):
    """Authentication required to access this playlist.

    Raised when trying to access a private playlist without valid cookies.
    """


class UnsupportedPlaylistError(SoundifyError):
    """Playlist type is not supported.

    Raised for auto-generated playlists like Recap, Discover Mix, etc.
    that use a different API structure not supported by ytmusicapi.
    """


class UpstreamAPIError(SoundifyError):
    """YouTube Music API error.

    Raised when the underlying API request fails.
    """


class DownloadError(SoundifyError):
    """Failed to download a track.

    Raised when yt-dlp fails to download audio.
    """


class CancellationError(SoundifyError):
    """Operation was cancelled.

    Raised when a download or extraction operation is cancelled
    via a CancelToken.
    """
