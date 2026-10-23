/**
 * Static stand-in for the 3D emblem. Used in three situations: WebGL is
 * unavailable (tests, very old GPUs), the WebGL context is lost, or the
 * three.js chunk is still loading. Pure CSS — no three.js import — so the
 * failure path never pulls the heavy bundle.
 *
 * All animation here is CSS, which the design system already governs:
 * prefers-reduced-motion and <html data-motion="reduced"> collapse these
 * animations to 0.01ms via the global rules in index.css.
 */
export function FallbackEmblem({ reason }: { reason?: 'loading' | 'no-webgl' | 'context-lost' }) {
  return (
    <div
      data-testid="hero-fallback"
      data-reason={reason ?? 'static'}
      aria-hidden
      className="relative w-full h-full flex items-center justify-center select-none"
    >
      {/* Concentric technical rings — the same silhouette as the 3D scene. */}
      <span
        className="absolute w-[72%] h-[72%] rounded-full border border-accent-line/60"
        style={{ borderTopColor: 'var(--color-accent)', animation: 'spin 14s linear infinite' }}
      />
      <span
        className="absolute w-[92%] h-[92%] rounded-full border border-violet-line/50"
        style={{ borderBottomColor: 'var(--color-violet)', animation: 'spin 22s linear infinite reverse' }}
      />
      {/* Core */}
      <span
        className="w-[34%] h-[34%] rotate-45"
        style={{
          background: 'linear-gradient(135deg, var(--color-surface-4), var(--color-surface-2))',
          border: '1px solid var(--color-accent-line)',
          boxShadow: '0 0 24px -6px var(--color-accent-dim)',
        }}
      />
      {reason === 'loading' && (
        <span className="absolute bottom-1 text-[9px] tracking-[0.14em] uppercase text-text-tertiary">
          Loading
        </span>
      )}
    </div>
  )
}
