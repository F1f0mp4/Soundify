import { Wordmark } from "@/components/brand/wordmark";
import { ThemeToggler } from "@/components/layout/theme-toggler";
import { CookieDropdown } from "@/features/cookies/cookie-dropdown";
import { useCookies } from "@/features/cookies/use-cookies";
import { useJobs } from "@/features/jobs/jobs-context";
import { useVersionCheck } from "@/hooks/use-version-check";
import { Button, buttonVariants, cn, Link as HeroUILink } from "@heroui/react";
import { Link, useRouterState } from "@tanstack/react-router";
import {
  DownloadIcon,
  ListMusicIcon,
  MenuIcon,
  RocketIcon,
  XIcon,
} from "lucide-react";
import { useEffect, useState } from "react";

const navItems = [
  { label: "Downloads", startIcon: DownloadIcon, href: "/" },
  { label: "Playlists", startIcon: ListMusicIcon, href: "/playlists" },
];

export function Header() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const routerState = useRouterState();
  const currentPath = routerState.location.pathname;
  const {
    cookiesConfigured,
    isUploading,
    isDeleting,
    fileInputRef,
    handleFileSelect,
    handleDropdownAction,
    triggerFileUpload,
  } = useCookies();
  const { data: versionInfo } = useVersionCheck();
  const { hasActiveJobs } = useJobs();

  // While the overlay menu is open, block page scroll and allow Escape to close
  // it (v2's Navbar did both for us).
  useEffect(() => {
    if (!isMenuOpen) return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setIsMenuOpen(false);
    };
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isMenuOpen]);

  return (
    <>
      {/* Transparent over the ambient backdrop: the header is part of the
          atmosphere rather than a bar sitting on top of it. */}
      <nav className="sticky top-0 z-40 w-full">
        <header className="mx-auto grid h-20 max-w-5xl grid-cols-[1fr_auto_1fr] items-center px-4 sm:px-6">
          {/* Left: navigation on desktop, menu toggle on mobile */}
          <div className="flex items-center gap-1">
            <Button
              isIconOnly
              size="sm"
              variant="ghost"
              className="icon-action sm:hidden"
              aria-label={isMenuOpen ? "Close menu" : "Open menu"}
              aria-expanded={isMenuOpen}
              onPress={() => setIsMenuOpen(!isMenuOpen)}
            >
              {isMenuOpen ? (
                <XIcon className="h-5 w-5" strokeWidth={1.25} />
              ) : (
                <MenuIcon className="h-5 w-5" strokeWidth={1.25} />
              )}
            </Button>

            <ul className="hidden items-center gap-1 sm:flex">
              {navItems.map((item) => {
                const isItemActive = currentPath === item.href;
                return (
                  <li key={item.href}>
                    <Link
                      to={item.href}
                      data-active={isItemActive || undefined}
                      className="text-muted data-[active]:text-foreground data-[active]:glass-subtle hover:text-foreground inline-flex items-center gap-2 rounded-full px-3.5 py-1.5 text-xs tracking-[0.12em] uppercase transition-colors"
                    >
                      <item.startIcon
                        className="h-3.5 w-3.5"
                        strokeWidth={1.25}
                      />
                      {item.label}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>

          {/* Center: brand */}
          <Link
            to="/"
            aria-label="Soundify home"
            className="justify-self-center"
          >
            <Wordmark
              isActive={hasActiveJobs}
              markClassName="text-accent h-6 w-6"
              className="max-[380px]:[&>span:last-child]:hidden"
            />
          </Link>

          {/* Right: actions */}
          <div className="flex items-center justify-end gap-1">
            {versionInfo?.updateAvailable && (
              <a
                href={versionInfo.releaseUrl}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={`Update available: ${versionInfo.latestVersion}`}
                className={cn(
                  buttonVariants({
                    size: "sm",
                    variant: "ghost",
                    isIconOnly: true,
                  }),
                  "icon-action text-accent hidden sm:inline-flex",
                )}
              >
                <RocketIcon className="h-4 w-4" strokeWidth={1.25} />
              </a>
            )}
            <div className="hidden sm:block">
              <CookieDropdown
                variant="desktop"
                cookiesConfigured={cookiesConfigured}
                isUploading={isUploading}
                isDeleting={isDeleting}
                onDropdownAction={handleDropdownAction}
                onUploadClick={triggerFileUpload}
              />
            </div>
            <ThemeToggler />
          </div>
        </header>

        {/* Hidden file input for cookie upload */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".txt"
          onChange={handleFileSelect}
          className="hidden"
        />
      </nav>

      {/* Mobile menu: overlays the page instead of pushing it down, so the
          sticky bar keeps its height and content below never shifts. Must live
          outside <nav>, whose backdrop-filter would otherwise make it the
          containing block for this fixed element. */}
      {isMenuOpen && (
        <div className="bg-background/80 fixed inset-x-0 top-20 bottom-0 z-30 overflow-y-auto backdrop-blur-2xl sm:hidden">
          <ul className="flex flex-col gap-6 p-8">
            {navItems.map((item) => (
              <li key={item.href}>
                <Link
                  to={item.href}
                  onClick={() => setIsMenuOpen(false)}
                  className={cn(
                    "flex w-full items-center gap-3 text-lg font-light tracking-[0.1em] uppercase",
                    currentPath === item.href
                      ? "text-accent"
                      : "text-foreground",
                  )}
                >
                  <item.startIcon className="h-4 w-4" strokeWidth={1.25} />
                  {item.label}
                </Link>
              </li>
            ))}
            <li className="pt-2">
              <CookieDropdown
                variant="mobile"
                cookiesConfigured={cookiesConfigured}
                isUploading={isUploading}
                isDeleting={isDeleting}
                onDropdownAction={handleDropdownAction}
                onUploadClick={triggerFileUpload}
              />
            </li>
            <li>
              <HeroUILink
                href="https://github.com/guillevc/yubal"
                target="_blank"
                rel="noopener noreferrer"
                className="text-muted w-full text-sm"
              >
                Built on yubal
                <HeroUILink.Icon />
              </HeroUILink>
            </li>
          </ul>
        </div>
      )}
    </>
  );
}
