// Must match backend validation in packages/api/src/soundify_api/schemas/jobs.py
// and core validation in packages/soundify/src/soundify/utils/url.py
export const YOUTUBE_URL_PATTERN =
  /^https?:\/\/(music\.youtube\.com\/(playlist\?list=|browse\/|watch\?v=)|(?:www\.|m\.)?youtube\.com\/(playlist\?list=|watch\?v=|shorts\/|live\/|embed\/|e\/|v\/|vi\/)|youtu\.be\/|(?:www\.)?youtube-nocookie\.com\/embed\/)[\w-]+/;

// Track, album and playlist links, optionally behind a locale prefix such as
// /intl-de/. Share links carry a ?si= tracking parameter, which is ignored.
export const SPOTIFY_URL_PATTERN =
  /^(https?:\/\/(open|play)\.spotify\.com\/(intl-[A-Za-z-]+\/)?(track|album|playlist)\/[A-Za-z0-9]+|spotify:(track|album|playlist):[A-Za-z0-9]+$)/;

export function isValidUrl(url: string): boolean {
  return YOUTUBE_URL_PATTERN.test(url) || SPOTIFY_URL_PATTERN.test(url);
}
