import type { CSSProperties } from 'react'
import { cn } from '../../lib/utils'

interface Orb3DProps {
  /** Box size in pixels; the sphere is proportional so any size works. */
  size?: number
  className?: string
  /** Hide from assistive tech (it is decoration, never data). */
  decorative?: boolean
}

/**
 * CSS focal ornament for page hero bands: a machined instrument dial inside
 * a dark metal case — tick scale, one accent arc, a hub with a needle.
 *
 * Deliberately not WebGL. The app already ships one three.js scene for the
 * Home hero; a second canvas per page would cost a GPU context and a bundle
 * for something that is pure ornament. This is built from conic gradients
 * and masks, so it costs nothing, scales with the layout and inherits the
 * accent ramp — change the accent preset and the dial follows.
 *
 * Everything animated is a CSS transform, so the global reduced-motion
 * rules in index.css park it automatically.
 */
export function Orb3D({ size = 168, className, decorative = true }: Orb3DProps) {
  return (
    <div
      className={cn('orb', className)}
      style={{ width: size, height: size, '--orb-size': `${size}px` } as CSSProperties}
      {...(decorative ? { 'aria-hidden': true } : {})}
      data-testid="orb-3d"
    >
      <span className="orb-halo" />
      <span className="orb-case">
        <span className="orb-ticks" />
        <span className="orb-arc" />
        <span className="orb-hub">
          <span className="orb-needle" />
        </span>
        <span className="orb-dot" />
      </span>
      <span className="orb-shadow" />
    </div>
  )
}
