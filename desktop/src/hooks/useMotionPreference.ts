import { useEffect, useState } from 'react'

/**
 * True when motion should be suppressed.
 *
 * Two sources, in precedence order (matching the CSS in index.css):
 *  - <html data-motion="full">   -> never suppress (user overrode the OS)
 *  - <html data-motion="reduced"> -> always suppress (user asked for it)
 *  - otherwise the OS prefers-reduced-motion media query decides.
 *
 * CSS animations/transitions are already handled by the stylesheet rules.
 * This hook exists for JS-driven animation (framer-motion, the 3D hero,
 * canvas) which never touches CSS and would ignore those rules.
 */
export function useMotionPreference(): boolean {
  const [reduced, setReduced] = useState(() => compute())

  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    const update = () => setReduced(compute())
    update()
    mq.addEventListener('change', update)

    /* The in-app setting lives on <html data-motion>; watch it directly so
       toggling Settings applies without a reload. */
    const obs = new MutationObserver(update)
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ['data-motion'] })

    return () => {
      mq.removeEventListener('change', update)
      obs.disconnect()
    }
  }, [])

  return reduced
}

function compute(): boolean {
  return prefersReducedMotion()
}

/** Imperative read of the same rules, for pointer-driven effects (game
 *  card tilt) that must not subscribe every instance to an observer. */
export function prefersReducedMotion(): boolean {
  const mode = document.documentElement.dataset.motion
  if (mode === 'full') return false
  if (mode === 'reduced') return true
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}
