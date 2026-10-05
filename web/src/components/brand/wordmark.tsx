import { cn } from "@heroui/react";

type MarkProps = {
  className?: string;
  /** Slowly rotates the outer ring, used while downloads are running. */
  isActive?: boolean;
};

/**
 * The Soundify mark: a disc with sound radiating from it.
 *
 * Concentric geometry on a single axis, drawn with hairline strokes so it sits
 * at the same visual weight as the interface icons rather than shouting over
 * them.
 */
export function SoundifyMark({ className, isActive }: MarkProps) {
  return (
    <svg
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
      className={cn("h-7 w-7", className)}
    >
      {/* Disc */}
      <circle
        cx="13"
        cy="16"
        r="9"
        stroke="currentColor"
        strokeWidth="1.1"
        opacity="0.55"
        className={cn(
          isActive &&
            "origin-[13px_16px] animate-[spin_9s_linear_infinite] motion-reduce:animate-none",
        )}
      />
      {/* Spindle */}
      <circle cx="13" cy="16" r="2.15" fill="currentColor" />
      {/* Radiating arcs */}
      <path
        d="M23.2 10.6a9.9 9.9 0 0 1 0 10.8"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <path
        d="M27.4 7.6a15.2 15.2 0 0 1 0 16.8"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        opacity="0.5"
      />
    </svg>
  );
}

type WordmarkProps = {
  className?: string;
  markClassName?: string;
  isActive?: boolean;
  /** Hide the lettering and show the mark alone. */
  markOnly?: boolean;
};

/**
 * Full lockup: mark plus letterspaced logotype.
 *
 * The lettering is deliberately light and widely tracked; that spacing is the
 * brand, so it is set here rather than left to each call site.
 */
export function Wordmark({
  className,
  markClassName,
  isActive,
  markOnly,
}: WordmarkProps) {
  return (
    <span className={cn("flex items-center gap-2.5", className)}>
      <SoundifyMark className={markClassName} isActive={isActive} />
      {!markOnly && (
        <span className="text-foreground text-[1.0625rem] leading-none font-light tracking-[0.34em] uppercase">
          Soundify
        </span>
      )}
    </span>
  );
}
