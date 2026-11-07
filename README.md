<div align="center">

# Soundify

**Self-hosted music library.** Paste a link — YouTube Music, Spotify, Apple Music or SoundCloud — and get tagged, organised audio.

Scheduled sync · synced lyrics · media-server ready

</div>

<br/>

## What it is

Soundify is a fork of [yubal](https://github.com/guillevc/yubal) by [@guillevc](https://github.com/guillevc) (MIT), rebuilt around three changes:

|                                  |                                                                                                                                                                                                                                                           |
| -------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Downloads that actually work** | yt-dlp is pinned to the YouTube clients that serve audio without a PO token. Upstream leaves client choice to yt-dlp, which switches to `web_creator`/`web_music` as soon as cookies are present — both need a token, so every track fails with HTTP 403. |
| **Links from any service**       | Paste a Spotify, Apple Music or SoundCloud track, album or playlist. Soundify reads the track list (no API keys, no accounts), matches each track on YouTube Music, and tags from there. Playlists from all four services can be subscribed to.           |
| **A new interface**              | Dark glass over an ambient backdrop, ring metrics, an original identity.                                                                                                                                                                                  |

Everything else — tagging, deduplication, scheduling, the M3U layout, the browser extension — is upstream's work.

## How it works

Downloading music is easy. _Organising_ it is the hard part. Soundify produces a clean, tagged library:

```
data/
├── Pink Floyd/
│   └── 1973 - The Dark Side of the Moon/
│       ├── 01 - Speak to Me.opus
│       ├── 01 - Speak to Me.lrc
│       └── cover.jpg
└── _Playlists/
    ├── My Favorites [n2g-XhDv].m3u
    └── My Favorites [n2g-XhDv].jpg
```

Each track lives in its album folder; playlists reference it, so a track appearing in ten playlists is stored once:

```m3u
#EXTM3U
#EXTINF:239,Pink Floyd - Breathe
../Pink Floyd/1973 - The Dark Side of the Moon/02 - Breathe.opus
```

## Features

- **Web UI** — real-time progress, job queue, works on mobile
- **YouTube Music, Spotify, Apple Music & SoundCloud** — albums, playlists and single tracks
- **Scheduled sync** — subscribe to a playlist or album from any of them; new tracks arrive automatically
- **Whole playlists by default** — no track cap unless you set one
- **Playlist covers** — saved next to each playlist's M3U, taken from the service the playlist came from
- **Smart deduplication** — one file, referenced everywhere
- **Synced lyrics** — `.lrc` files from lrclib.net, with a YouTube Music fallback
- **ReplayGain** — track gain, plus album gain on complete albums
- **Format options** — `opus` (best quality/size), `mp3`, `m4a` — copied directly when possible, transcoded otherwise
- **Media server ready** — Navidrome, Jellyfin, Gonic
- **CLI** — [download and inspect metadata from the terminal](packages/soundify/src/soundify/cli/README.md)

## Quick start

```bash
docker compose up -d
# http://localhost:8000
```

The bundled `compose.yaml` builds from source. Set `PUID`/`PGID` to match your host user (run `id`) so downloaded files are owned by you.

## Configuration

| Variable                           | Description                                  | Default                       |
| ---------------------------------- | -------------------------------------------- | ----------------------------- |
| `PUID` / `PGID`                    | User/group ID for file ownership             | `1000`                        |
| `SOUNDIFY_AUDIO_FORMAT`            | `opus`, `mp3`, or `m4a`                      | `opus`                        |
| `SOUNDIFY_AUDIO_QUALITY`           | Transcode quality (0=best, 10=worst)         | `0`                           |
| `SOUNDIFY_PLAYER_CLIENTS`          | yt-dlp YouTube clients, in order             | `["visionos","web_embedded"]` |
| `SOUNDIFY_POT_PROVIDER_URL`        | PO token provider, e.g. `http://bgutil:4416` | —                             |
| `SOUNDIFY_DOWNLOAD_SLEEP_INTERVAL` | Seconds between downloads                    | `0`                           |
| `SOUNDIFY_SCHEDULER_ENABLED`       | Automatic scheduled sync                     | `true`                        |
| `SOUNDIFY_SCHEDULER_CRON`          | Cron schedule for auto-sync                  | `0 0 * * *`                   |
| `SOUNDIFY_FETCH_LYRICS`            | Fetch lyrics from lrclib.net                 | `true`                        |
| `SOUNDIFY_DOWNLOAD_UGC`            | Download user uploads to `_Unofficial/`      | `false`                       |
| `SOUNDIFY_REPLAYGAIN`              | Apply ReplayGain tags                        | `true`                        |
| `SOUNDIFY_TZ`                      | Timezone (IANA)                              | `UTC`                         |

<details>
<summary>All options</summary>

| Variable                       | Description                                | Default       |
| ------------------------------ | ------------------------------------------ | ------------- |
| `SOUNDIFY_HOST`                | Server bind address                        | `127.0.0.1`   |
| `SOUNDIFY_PORT`                | Server port                                | `8000`        |
| `SOUNDIFY_DATA`                | Music library output                       | `/app/data`   |
| `SOUNDIFY_CONFIG`              | Config directory                           | `/app/config` |
| `SOUNDIFY_LOG_LEVEL`           | `DEBUG`, `INFO`, `WARNING`, `ERROR`        | `INFO`        |
| `SOUNDIFY_ASCII_FILENAMES`     | Transliterate unicode to ASCII             | `false`       |
| `SOUNDIFY_BASE_PATH`           | URL base path for reverse-proxy subfolders | —             |
| `SOUNDIFY_CORS_ORIGINS`        | Allowed CORS origins                       | `["*"]`       |
| `SOUNDIFY_JOB_TIMEOUT_SECONDS` | Job execution timeout                      | `1800`        |
| `SOUNDIFY_TEMP`                | Temp directory                             | System temp   |

</details>

## Cookies (optional)

Needed for age-restricted tracks, private playlists and your **Liked Music** (`list=LM`). A **free** signed-in account is enough — Premium is never required.

Place a `cookies.txt` at `config/ytdlp/cookies.txt`, or upload it through the web UI.

<details>
<summary>Exporting from Safari on macOS</summary>

Safari stores cookies in a binary format, so yt-dlp has to convert them.

1. System Settings → Privacy & Security → **Full Disk Access** → enable Terminal, then restart Terminal.
2. Sign into YouTube in Safari.
3. Run:

```bash
pipx run yt-dlp --cookies-from-browser safari --cookies ~/Downloads/cookies.txt --skip-download "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

Firefox is easier if Safari gives you trouble: `--cookies-from-browser firefox`, no Full Disk Access needed.

</details>

> [!CAUTION]
> `cookies.txt` is credential-equivalent — anyone holding it is signed in as you. Cookie use can also trigger stricter rate limiting and put the account at risk, so consider a secondary account.

## Age-restricted tracks

Measured on 2026-09-12, so you know what to expect:

- Tracks that are **embeddable** download with **no account at all** (the `web_embedded` client handles them).
- Tracks behind _"Sign in to confirm your age"_ need cookies from a free signed-in account. A PO token does **not** help here — the `mweb` client returns the identical error with and without one, so the optional bgutil sidecar in `compose.yaml` stays off by default.

## Subscriptions

Subscribe to a playlist or album on the **Playlists** page and Soundify re-syncs it on the schedule, downloading only what is new. Each subscription shows a badge for its service (YouTube Music, Spotify, Apple Music or SoundCloud). Single-track links are refused, since a lone track never gains new songs — download those from the home page instead.

The **track limit** field (`#`) is empty by default, which means the whole playlist. A number applies only when you type one, and only to that download or subscription. Subscriptions created with a limit show it in the _Limit_ column; click the **×** next to it to remove it, and the next sync picks up the rest of the playlist.

## Spotify, Apple Music and SoundCloud

None of these hand out audio Soundify can use, so they only supply the track list. Each track's title, artists and duration are matched against YouTube Music; album, track number, year and cover art then come from YouTube Music, so tagging is the same as for any other download. A track with no confident match is skipped and listed in the job, never swapped for a cover or a live version.

| Service         | Supported links                                                                            | How it is read                                           | Limits                                                                                  |
| --------------- | ------------------------------------------------------------------------------------------ | -------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| **Spotify**     | `open.spotify.com` track, album, playlist; `spotify:` URIs                                 | Public embed pages                                       | **Playlists stop at 100 tracks**; longer ones are truncated and flagged                 |
| **Apple Music** | `music.apple.com` song, album (including `?i=` song links), playlist (`pl.…`)              | Public page data; single songs via the iTunes Lookup API | Very long playlists may list only their first page of tracks; flagged when that happens |
| **SoundCloud**  | Tracks, sets (playlists and albums), private `/s-…` links, `on.soundcloud.com` short links | yt-dlp                                                   | Reading a set takes about half a second per track; profiles and likes are not supported |

Why no official APIs: Spotify's Web API stopped working for Development Mode apps without Premium in February 2026 and has returned 404 for editorial `37i9dQZF1D…` playlists since November 2024; the Apple Music API needs a paid developer membership. The public pages need no credentials and still serve editorial playlists.

Why SoundCloud is matched rather than downloaded directly: a large share of its catalogue is DRM protected or served as a 30-second preview. Matching gives full-length audio and proper album tags. Independent uploads that are not on YouTube Music (DJ mixes, unreleased tracks) are skipped and reported.

## Media server integration

| Server        | Artist linking                                             | Playlists |
| ------------- | ---------------------------------------------------------- | :-------: |
| **Navidrome** | Works out of the box                                       |    ✅     |
| **Jellyfin**  | Enable "Use non-standard artists tags" in library settings |    ✅     |
| **Gonic**     | Set `GONIC_MULTI_VALUE_ARTIST=multi`                       |    ❌     |

> [!NOTE]
> ReplayGain uses `rsgain`, which the Dockerfile installs for amd64 only. On arm64 (Apple Silicon) it is unavailable and the step is skipped.

## Credits

Built on [yubal](https://github.com/guillevc/yubal) by [@guillevc](https://github.com/guillevc) — the tagging, organisation, scheduling and extension are all their work. If this is useful to you, [support the upstream project](https://ko-fi.com/guillevc).

Powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp) and [ytmusicapi](https://github.com/sigma67/ytmusicapi). Lyrics from [LRCLIB](https://lrclib.net).

## License

[MIT](LICENSE) — as inherited from yubal, whose copyright notice is retained.

---

<sub>For personal archiving only. Comply with the terms of service of the platforms you use and with applicable copyright law.</sub>
