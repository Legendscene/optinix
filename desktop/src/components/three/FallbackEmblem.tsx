/**
 * Static stand-in for the 3D tower. Used in three situations: WebGL is
 * unavailable (tests, very old GPUs), the WebGL context is lost, or the
 * three.js chunk is still loading. Pure CSS — no three.js import — so the
 * failure path never pulls the heavy bundle, and it keeps the same silhouette
 * as the scene so the hero never collapses.
 *
 * All animation here is CSS, which the design system already governs:
 * prefers-reduced-motion and <html data-motion="reduced"> collapse these
 * animations via the global rules in index.css.
 */
export function FallbackEmblem({ reason }: { reason?: 'loading' | 'no-webgl' | 'context-lost' }) {
  return (
    <div
      data-testid="hero-fallback"
      data-reason={reason ?? 'static'}
      aria-hidden
      className="relative w-full h-full flex items-center justify-center select-none"
    >
      <span className="tower-base" />

      <div className="tower-fallback">
        <span className="tower-frame" />
        <span className="tower-glass" />
        <span className="tower-strip" />
        <span className="tower-gpu" />
        <span className="tower-fan tower-fan-a" />
        <span className="tower-fan tower-fan-b" />
      </div>

      {reason === 'loading' && (
        <span className="absolute bottom-1 text-[9px] tracking-[0.16em] uppercase text-text-tertiary">
          Loading
        </span>
      )}
    </div>
  )
}
