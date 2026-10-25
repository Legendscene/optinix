/**
 * Ambient depth layer behind every route.
 *
 * Optinix is a dark hardware product, so the shell is lit like a room rather
 * than decorated like a HUD: one electric-cyan key light from above the fold,
 * a violet counter-light low left, a cool blue fill high right, two soft light
 * shafts, film grain and a vignette. No grid, no wireframe halls — depth here
 * comes from light falling across a surface, which is what makes the framed
 * content read as physical plates.
 *
 * Purely decorative: no canvas, no WebGL context. Every moving part is a
 * transform on one element, so the layer costs the compositor almost nothing
 * and never blocks a click.
 *
 * Depth is pointer-reactive: three layers chase the pointer at different
 * rates and directions (key light with, counter light against), so the
 * backdrop reads as a space instead of a poster. The listener is
 * rAF-throttled, lerps for organic lag, stops itself when the pointer rests,
 * and never runs under reduced motion (the layers then hold their default
 * pose).
 */

import { useEffect, useRef } from 'react'
import { prefersReducedMotion } from '../../hooks/useMotionPreference'

export function PageAtmosphere() {
  /* The CSS vars --px/--py land on this host; every parallax layer reads
     them through inheritance, so one writer drives all layers. */
  const host = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = host.current
    if (!el) return

    let raf = 0
    let running = false
    let px = 0.5, py = 0.5   // eased value (what the layers show)
    let tx = 0.5, ty = 0.5   // pointer target

    const tick = () => {
      px += (tx - px) * 0.06
      py += (ty - py) * 0.06
      el.style.setProperty('--px', px.toFixed(3))
      el.style.setProperty('--py', py.toFixed(3))
      /* Settled close enough to the target: stop the loop entirely and
         restart on the next pointer move instead of idling forever. */
      if (Math.abs(tx - px) < 0.001 && Math.abs(ty - py) < 0.001) {
        running = false
        return
      }
      raf = requestAnimationFrame(tick)
    }

    const wake = () => {
      if (!running) {
        running = true
        raf = requestAnimationFrame(tick)
      }
    }

    const onMove = (e: PointerEvent) => {
      if (prefersReducedMotion() || document.hidden) return
      tx = e.clientX / window.innerWidth
      ty = e.clientY / window.innerHeight
      wake()
    }

    window.addEventListener('pointermove', onMove, { passive: true })
    return () => {
      cancelAnimationFrame(raf)
      running = false
      window.removeEventListener('pointermove', onMove)
    }
  }, [])

  return (
    <div
      aria-hidden
      ref={host}
      style={{ '--px': 0.5, '--py': 0.5 } as React.CSSProperties}
      className="pointer-events-none absolute inset-0 z-0 overflow-hidden"
    >
      {/* The light the whole app sits in. */}
      <div className="atmo-key" />
      <div className="atmo-cool" />
      <div className="atmo-counter" />

      {/* Two soft shafts from above the fold. */}
      <div className="atmo-shaft atmo-shaft-a" />
      <div className="atmo-shaft atmo-shaft-b" />

      {/* Edge falloff so the content column always has the brightest
          surface in the frame. */}
      <div className="atmo-vignette absolute inset-0" />

      {/* Static film grain: the texture that keeps large dark fields from
          reading as flat CSS fills. */}
      <div className="atmo-grain absolute inset-0" />
    </div>
  )
}
