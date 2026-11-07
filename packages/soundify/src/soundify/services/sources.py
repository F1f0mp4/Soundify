"""Route a link to the reader for the service it belongs to."""

from soundify.services.apple_music import AppleMusicClient
from soundify.services.external import ExternalContent
from soundify.services.soundcloud import SoundCloudClient
from soundify.services.spotify import SpotifyEmbedClient
from soundify.utils.url import (
    parse_apple_music_url,
    parse_soundcloud_url,
    parse_spotify_url,
)


def is_external_url(url: str) -> bool:
    """Whether the link belongs to a service whose tracks must be matched.

    True for Spotify, Apple Music and SoundCloud. YouTube and YouTube Music
    links are downloaded directly and return False.
    """
    return (
        parse_spotify_url(url) is not None
        or parse_apple_music_url(url) is not None
        or parse_soundcloud_url(url) is not None
    )


class ExternalSourceReader:
    """Reads track lists from Spotify, Apple Music and SoundCloud links."""

    def __init__(
        self,
        spotify: SpotifyEmbedClient | None = None,
        apple_music: AppleMusicClient | None = None,
        soundcloud: SoundCloudClient | None = None,
    ) -> None:
        """Initialize the reader.

        Args:
            spotify: Spotify reader. Defaults to the public embed reader.
            apple_music: Apple Music reader. Defaults to AppleMusicClient.
            soundcloud: SoundCloud reader. Defaults to SoundCloudClient.
        """
        self._spotify = spotify or SpotifyEmbedClient()
        self._apple_music = apple_music or AppleMusicClient()
        self._soundcloud = soundcloud or SoundCloudClient()

    def fetch(self, url: str, *, summary: bool = False) -> ExternalContent | None:
        """Fetch the content behind an external link.

        Args:
            url: Any URL.
            summary: Only the title, cover and track count are needed. Lets
                readers that pay per track (SoundCloud) skip the track list.

        Returns:
            The content, or None when the link is not a Spotify, Apple Music or
            SoundCloud link.

        Raises:
            PlaylistParseError: If the link names an unsupported entity kind.
            PlaylistNotFoundError: If the service has no such entity.
            UpstreamAPIError: If the service cannot be reached or read.
        """
        if spotify := parse_spotify_url(url):
            return self._spotify.fetch(*spotify)
        if apple := parse_apple_music_url(url):
            return self._apple_music.fetch(*apple)
        if parse_soundcloud_url(url) is not None:
            return self._soundcloud.fetch(url.strip(), summary=summary)
        return None
