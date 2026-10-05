/**
 * Fixed atmospheric backdrop that every glass surface floats above.
 *
 * Built from layered radial gradients rather than a photograph: it ships as a
 * few hundred bytes, never pops in on load, adapts to both themes, and can
 * drift slowly without a video. The grain on top breaks up the gradient banding
 * that large, low-contrast washes show on 8-bit displays.
 */
export function AmbientBackground() {
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 -z-10 overflow-hidden"
    >
      {/* Base wash */}
      <div className="absolute inset-0 bg-[#eef2f7] dark:bg-[#05080f]" />

      {/* Horizon glow: the warm/cool split that gives the page a sense of depth.
          Strong enough that the frosted panels have something to sit on -- a
          near-black page makes 6%-white glass read as flat grey. */}
      <div
        className="animate-drift absolute inset-0"
        style={{
          background: `
            radial-gradient(115% 75% at 8% 112%, rgb(56 214 190 / 0.42), transparent 60%),
            radial-gradient(95% 70% at 92% -12%, rgb(126 96 220 / 0.38), transparent 58%),
            radial-gradient(85% 55% at 52% 118%, rgb(255 186 120 / 0.20), transparent 64%),
            radial-gradient(60% 45% at 78% 62%, rgb(70 140 255 / 0.16), transparent 70%)
          `,
        }}
      />

      {/* Vignette keeps the corners quiet so floating panels stay legible */}
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(110% 80% at 50% 38%, transparent 52%, rgb(0 0 0 / 0.42) 100%)",
        }}
      />

      {/* Grain */}
      <div
        className="absolute inset-0 opacity-[0.14] mix-blend-overlay dark:opacity-[0.16]"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3'/%3E%3C/filter%3E%3Crect width='200' height='200' filter='url(%23n)' opacity='0.5'/%3E%3C/svg%3E")`,
        }}
      />
    </div>
  );
}
