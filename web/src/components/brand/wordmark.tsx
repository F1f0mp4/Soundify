import { cn } from "@heroui/react";
import { useId } from "react";

type MarkProps = {
  className?: string;
  /** Pulses the detached dot while downloads are running. */
  isActive?: boolean;
};

/**
 * The Soundify mark.
 *
 * Two capsules read as a level meter, one punched with a circular counter. A
 * blob fuses into the base of the first through a concave neck, and a detached
 * dot sits clear of the form. The neck is a true tangent fillet: the two wedge
 * paths carry the concave edges, while their straight edges run to the circle
 * centres where the circles themselves cover them, so no seam can appear.
 */
export function SoundifyMark({ className, isActive }: MarkProps) {
  // Mask ids must be unique per instance or multiple marks on one page collide.
  const maskId = useId();

  return (
    <svg
      viewBox="0 0 64 64"
      fill="none"
      aria-hidden="true"
      className={cn("h-7 w-7", className)}
    >
      <defs>
        <mask id={maskId}>
          <rect width="64" height="64" fill="#fff" />
          <circle cx="45" cy="26" r="4.6" fill="#000" />
        </mask>
      </defs>
      <g fill="currentColor">
        <path d="M 17.396 35.678 A 10 10 0 0 1 9.984 42.155 L 11.5 49.5 L 24 38 Z" />
        <path d="M 25.764 44.774 A 10 10 0 0 0 18.694 51.622 L 11.5 49.5 L 24 38 Z" />
        <circle cx="11.5" cy="49.5" r="7.5" />
        <rect x="17" y="14" width="14" height="31" rx="7" />
        <rect
          x="38"
          y="19"
          width="14"
          height="33"
          rx="7"
          mask={`url(#${maskId})`}
        />
        <circle
          cx="56"
          cy="12"
          r="5"
          className={cn(isActive && "animate-dot-pulse")}
        />
      </g>
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
