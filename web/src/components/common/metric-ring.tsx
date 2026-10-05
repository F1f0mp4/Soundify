import { cn } from "@heroui/react";
import type { ReactNode } from "react";

type Props = {
  /** Big numeral shown inside the ring. */
  value: ReactNode;
  /** Wide-tracked caption under the ring. */
  label: string;
  /** Hairline glyph above the value. */
  icon?: ReactNode;
  /**
   * Fraction of the ring to fill, 0-1. Omit for plain counts, where a filled
   * arc would imply a ceiling that does not exist.
   */
  progress?: number;
  className?: string;
};

const SIZE = 96;
const STROKE = 1.25;
const RADIUS = (SIZE - STROKE) / 2;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

/**
 * A single circular metric: hairline ring, light numeral, tracked caption.
 *
 * The ring is drawn rather than bordered so the progress arc can share exactly
 * the same geometry as the track, and so the whole thing scales cleanly.
 */
export function MetricRing({ value, label, icon, progress, className }: Props) {
  const clamped =
    progress === undefined ? undefined : Math.min(1, Math.max(0, progress));

  return (
    <div className={cn("flex flex-col items-center gap-2.5", className)}>
      <div className="relative grid h-24 w-24 place-items-center">
        <svg
          viewBox={`0 0 ${SIZE} ${SIZE}`}
          className="absolute inset-0 h-full w-full -rotate-90"
          aria-hidden="true"
        >
          <circle
            cx={SIZE / 2}
            cy={SIZE / 2}
            r={RADIUS}
            fill="none"
            stroke="currentColor"
            strokeWidth={STROKE}
            className="text-foreground/15"
          />
          {clamped !== undefined && (
            <circle
              cx={SIZE / 2}
              cy={SIZE / 2}
              r={RADIUS}
              fill="none"
              stroke="currentColor"
              strokeWidth={STROKE * 2}
              strokeLinecap="round"
              strokeDasharray={CIRCUMFERENCE}
              strokeDashoffset={CIRCUMFERENCE * (1 - clamped)}
              className="text-accent transition-[stroke-dashoffset] duration-700 ease-out"
            />
          )}
        </svg>

        <div className="flex flex-col items-center gap-0.5">
          {icon && <span className="text-foreground/70">{icon}</span>}
          <span className="tnum text-foreground text-[1.75rem] leading-none font-extralight">
            {value}
          </span>
        </div>
      </div>

      <span className="eyebrow">{label}</span>
    </div>
  );
}
