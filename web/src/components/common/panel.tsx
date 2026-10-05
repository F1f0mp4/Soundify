import { cn, ScrollShadow } from "@heroui/react";
import type { HTMLAttributes, ReactNode, Ref } from "react";

type Props = HTMLAttributes<HTMLElement> & {
  children: ReactNode;
};

/**
 * A floating frosted surface.
 *
 * Deliberately a plain element rather than HeroUI's Card: the card ships an
 * opaque background that would have to be fought off on every instance, and the
 * whole design depends on the ambient backdrop showing through.
 */
export function Panel({ children, className }: Props) {
  return (
    <section
      className={cn("glass overflow-hidden rounded-[1.75rem]", className)}
    >
      {children}
    </section>
  );
}

type HeaderProps = {
  leadingIcon?: ReactNode;
  badge?: ReactNode;
  children: ReactNode;
  className?: string;
};

export function PanelHeader({
  leadingIcon,
  badge,
  children,
  className,
}: HeaderProps) {
  return (
    <div className={cn("px-6 pt-5 pb-4", className)}>
      <div className="text-muted flex w-full items-center gap-2.5">
        {leadingIcon && <span className="opacity-70">{leadingIcon}</span>}
        <span className="eyebrow">{children}</span>
        {badge}
      </div>
    </div>
  );
}

type ContentProps = HTMLAttributes<HTMLDivElement> & {
  children: ReactNode;
  height?: string;
  ref?: Ref<HTMLDivElement>;
};

export function PanelContent({
  children,
  className,
  height = "h-72",
  ref,
  ...props
}: ContentProps) {
  return (
    // Padding lives on the scroller so the scrollbar sits on the panel edge and
    // the scroll shadows fade across the full width.
    <div className="pb-5">
      <ScrollShadow
        ref={ref}
        className={cn(height, "px-6", className)}
        offset={2}
        {...props}
      >
        {children}
      </ScrollShadow>
    </div>
  );
}
