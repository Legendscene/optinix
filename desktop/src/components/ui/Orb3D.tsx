import type { CSSProperties } from 'react'
import { cn } from '../../lib/utils'

interface Orb3DProps {
  /** Box size in pixels; the rings are proportional so any size works. */
  size?: number
  className?: string
  /** Hide from assistive tech (it is decoration, never data). */
  decorative?: boolean
}

/**
 * CSS 3D focal point for page hero bands: a lit core inside three tilted
 * rings, with satellite beads running the same orbits.
 *
 * Deliberately not WebGL. The app already ships one three.js scene for the
 * Home hero; a second canvas per page would cost a GPU context and a bundle
 * for something that is pure ornament. This is the same silhouette built from
 * transforms, so it costs nothing, scales with the layout and inherits the
 * accent ramp — change the accent preset and the orb follows.
 *
 * Depth is real: the rig sits in a `perspective` box, the rings are rotated on
 * X and Y, the beads orbit inside their tilted planes and the core is pushed
 * forward on Z. Everything animated here is a CSS transform, so the global
 * reduced-motion rules in index.css park it automatically.
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

      {/* Ring rig: three orbits on different axes. */}
      <div className="orb-rig">
        <span className="orb-ring" />
        <span className="orb-ring" />
        <span className="orb-ring" />
      </div>

      {/* Bead rig: the same orbits, travelled by satellites. */}
      <div className="orb-rig orb-rig-reverse">
        <span className="orb-sat"><i /></span>
        <span className="orb-sat"><i /></span>
        <span className="orb-sat"><i /></span>
      </div>

      {/* Inspection line across the core — the "instrument" tell. */}
      <span className="orb-axis" />
      <span className="orb-core" />
      <span className="orb-flare" />
    </div>
  )
}
