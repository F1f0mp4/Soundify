import type { components } from "@/api/schema";
import { cn } from "@heroui/react";
import type { ReactNode } from "react";

export type MusicSource = components["schemas"]["MusicSource"];

type SourceStyle = {
  label: string;
  /** Badge background; each service is recognisable by its colour first. */
  className: string;
  glyph: ReactNode;
};

// Simplified marks drawn on a 24x24 grid, white or black on the brand colour,
// so the badge reads at 16-20px without shipping a brand icon set.
const SOURCES: Record<MusicSource, SourceStyle> = {
  youtube: {
    label: "YouTube Music",
    className: "bg-[#ff0033] rounded-[30%]",
    glyph: <path d="M9.5 7.6v8.8l7.2-4.4z" fill="#fff" />,
  },
  spotify: {
    label: "Spotify",
    className: "bg-[#1ed760] rounded-full",
    glyph: (
      <g fill="none" stroke="#000" strokeLinecap="round">
        <path d="M6.6 9.4c3.7-1.2 7.6-.9 10.9.9" strokeWidth={1.9} />
        <path d="M7.2 12.6c3-.9 6.1-.6 8.8.8" strokeWidth={1.6} />
        <path d="M7.8 15.6c2.4-.6 4.7-.4 6.8.6" strokeWidth={1.35} />
      </g>
    ),
  },
  apple_music: {
    label: "Apple Music",
    className: "bg-gradient-to-b from-[#fb5c74] to-[#fa233b] rounded-[30%]",
    glyph: (
      <g fill="#fff">
        <path
          d="M10 16.4V7.6l7.4-1.6v8.6"
          fill="none"
          stroke="#fff"
          strokeWidth={1.7}
        />
        <ellipse cx="8.4" cy="16.6" rx="2.1" ry="1.8" />
        <ellipse cx="15.8" cy="15" rx="2.1" ry="1.8" />
      </g>
    ),
  },
  soundcloud: {
    label: "SoundCloud",
    className: "bg-gradient-to-b from-[#ff7700] to-[#ff3300] rounded-[30%]",
    glyph: (
      <g fill="#fff">
        <rect x="4.4" y="12.4" width="1.1" height="3.6" rx=".55" />
        <rect x="6.3" y="11.2" width="1.1" height="4.8" rx=".55" />
        <rect x="8.2" y="10.2" width="1.1" height="5.8" rx=".55" />
        <path d="M10.2 16V9.6a4.3 4.3 0 0 1 7.2 2.4 2 2 0 1 1 .6 4z" />
      </g>
    ),
  },
};

type SourceIconProps = {
  source: MusicSource;
  className?: string;
};

/** Badge showing which service a playlist comes from. */
export function SourceIcon({ source, className }: SourceIconProps) {
  const style = SOURCES[source] ?? SOURCES.youtube;
  return (
    <span
      role="img"
      aria-label={`From ${style.label}`}
      title={style.label}
      className={cn(
        "inline-flex size-5 shrink-0 items-center justify-center overflow-hidden",
        style.className,
        className,
      )}
    >
      <svg viewBox="0 0 24 24" className="size-full" aria-hidden="true">
        {style.glyph}
      </svg>
    </span>
  );
}
