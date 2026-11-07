// Must match backend validation in packages/api/src/soundify_api/schemas/jobs.py
// and core validation in packages/soundify/src/soundify/utils/url.py
export const YOUTUBE_URL_PATTERN =
  /^https?:\/\/(music\.youtube\.com\/(playlist\?list=|browse\/|watch\?v=)|(?:www\.|m\.)?youtube\.com\/(playlist\?list=|watch\?v=|shorts\/|live\/|embed\/|e\/|v\/|vi\/)|youtu\.be\/|(?:www\.)?youtube-nocookie\.com\/embed\/)[\w-]+/;

// Track, album and playlist links, optionally behind a locale prefix such as
// /intl-de/. Share links carry a ?si= tracking parameter, which is ignored.
export const SPOTIFY_URL_PATTERN =
  /^(https?:\/\/(open|play)\.spotify\.com\/(intl-[A-Za-z-]+\/)?(track|album|playlist)\/[A-Za-z0-9]+|spotify:(track|album|playlist):[A-Za-z0-9]+$)/;

// Album and song links (an album link with ?i=SONG is a song), and playlists,
// whose IDs start with "pl." (or "pl.u-" for user playlists).
export const APPLE_MUSIC_URL_PATTERN =
  /^https?:\/\/(music|geo\.music|embed\.music|itunes)\.apple\.com\/([a-z]{2}\/)?((album|song)(\/[^/?#]+)?\/\d+|playlist(\/[^/?#]+)?\/pl\.[A-Za-z0-9-]+)\/?([?#].*)?$/;

// Track links (/artist/track) and sets (/artist/sets/name), optionally with a
// /s-SECRET private-link suffix, plus on.soundcloud.com short links. Profiles
// and their tabs (likes, tracks, ...) are feeds, not a fixed track list.
const SOUNDCLOUD_RESERVED =
  "discover|stream|search|upload|you|charts|pages|settings|messages|notifications|people|tags|terms-of-use|imprint|jobs|pro|mobile|popular|signin|logout";
const SOUNDCLOUD_TABS =
  "likes|tracks|albums|sets|reposts|followers|following|comments|popular-tracks|spotlight|playlists";
export const SOUNDCLOUD_URL_PATTERN = new RegExp(
  "^https?:\\/\\/(" +
    `(www\\.|m\\.)?soundcloud\\.com\\/(?!(${SOUNDCLOUD_RESERVED})(?:[/?#]|$))[\\w-]+\\/` +
    `(sets\\/[\\w-]+|(?!(${SOUNDCLOUD_TABS})(?:[/?#]|$))[\\w-]+)(\\/s-[A-Za-z0-9]+)?` +
    "|on\\.soundcloud\\.com\\/[\\w-]+" +
    ")\\/?([?#].*)?$",
  "i",
);

export function isValidUrl(url: string): boolean {
  return (
    YOUTUBE_URL_PATTERN.test(url) ||
    SPOTIFY_URL_PATTERN.test(url) ||
    APPLE_MUSIC_URL_PATTERN.test(url) ||
    SOUNDCLOUD_URL_PATTERN.test(url)
  );
}
