import { Chip, tv, type VariantProps } from "@heroui/react";
import { ReactNode } from "react";

// Hairline outline rather than a filled pill: several chips sit together on a
// translucent row, and filled backgrounds stack into visual noise against the
// frosted surface behind them.
const jobChip = tv({
  base: "border bg-transparent text-[0.625rem] tracking-[0.1em] uppercase",
  variants: {
    variant: {
      flat: "text-muted border-[var(--surface-border)]",
      album: "text-accent border-accent/35",
      playlist: "text-secondary border-secondary/35",
      track: "border-amber-500/35 text-amber-600 dark:text-amber-300",
    },
  },
  defaultVariants: {
    variant: "flat",
  },
});

type Props = {
  children: ReactNode;
  className?: string;
} & VariantProps<typeof jobChip>;

export function JobChip({ children, variant, className }: Props) {
  return (
    <Chip size="md" variant="soft" className={jobChip({ variant, className })}>
      {children}
    </Chip>
  );
}
