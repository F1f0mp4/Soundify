import { SoundifyMark } from "@/components/brand/wordmark";

export function Footer() {
  return (
    <footer className="mx-auto w-full max-w-5xl px-4 py-10 sm:px-6">
      <div className="flex flex-col items-center gap-4">
        <SoundifyMark className="text-foreground/25 h-5 w-5" />

        <p className="text-muted/80 text-center text-[0.6875rem] tracking-[0.14em] uppercase">
          <a
            href="https://github.com/yt-dlp/yt-dlp"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-foreground transition-colors"
          >
            yt-dlp
          </a>
          <span className="px-2 opacity-40">·</span>
          <a
            href="https://github.com/sigma67/ytmusicapi"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-foreground transition-colors"
          >
            ytmusicapi
          </a>
          <span className="px-2 opacity-40">·</span>
          <a
            href="https://github.com/guillevc/yubal"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-foreground transition-colors"
          >
            yubal
          </a>
          <span className="px-2 opacity-40">·</span>
          {/* Plain text, not a link: these are Soundify's versions, and upstream
              has no release matching them. */}
          <span className="tnum">{__VERSION__}</span>
        </p>
      </div>
    </footer>
  );
}
