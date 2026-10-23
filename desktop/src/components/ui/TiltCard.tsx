import { useRef, type PointerEvent, type ReactNode } from 'react'
import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion'
import { prefersReducedMotion } from '../../hooks/useMotionPreference'
import { cn } from '../../lib/utils'

interface TiltCardProps {
  children: ReactNode
  className?: string
  /** Inner wrapper classes (the surface that actually tilts). */
  innerClassName?: string
  /** Maximum rotation in degrees at the card edge. Keep it small. */
  intensity?: number
  /** Specular highlight that tracks the pointer. */
  glare?: boolean
  onClick?: () => void
  title?: string
}

/**
 * Card that leans toward the pointer in real 3D.
 *
 * Two details make it read as physical rather than gimmicky: the rotation is
 * spring-damped (it settles, never wobbles) and the highlight is a specular
 * patch that moves with the pointer, so the light source appears to be
 * overhead rather than attached to the mouse.
 *
 * Runs at zero cost when the pointer is away, and does nothing at all when
 * the user has asked for reduced motion.
 */
export function TiltCard({
  children, className, innerClassName, intensity = 5, glare = true, onClick, title,
}: TiltCardProps) {
  const host = useRef<HTMLDivElement>(null)
  const px = useMotionValue(0.5)
  const py = useMotionValue(0.5)

  const spring = { stiffness: 220, damping: 22, mass: 0.4 }
  const rotateY = useSpring(useTransform(px, [0, 1], [-intensity, intensity]), spring)
  const rotateX = useSpring(useTransform(py, [0, 1], [intensity, -intensity]), spring)

  const glareBg = useTransform(
    [px, py],
    ([gx, gy]: number[]) =>
      `radial-gradient(240px circle at ${gx * 100}% ${gy * 100}%, rgba(255,255,255,0.06), transparent 62%)`,
  )

  const onMove = (e: PointerEvent<HTMLDivElement>) => {
    if (prefersReducedMotion()) return
    const el = host.current
    if (!el) return
    const r = el.getBoundingClientRect()
    px.set(Math.min(1, Math.max(0, (e.clientX - r.left) / r.width)))
    py.set(Math.min(1, Math.max(0, (e.clientY - r.top) / r.height)))
  }

  const reset = () => {
    px.set(0.5)
    py.set(0.5)
  }

  return (
    <div
      ref={host}
      className={cn('group perspective-900', className)}
      onPointerMove={onMove}
      onPointerLeave={reset}
      onClick={onClick}
      title={title}
    >
      <motion.div
        className={cn('relative h-full preserve-3d', innerClassName)}
        style={{ rotateX, rotateY, transformStyle: 'preserve-3d' }}
        whileHover={{ z: 6 }}
        transition={{ type: 'spring', ...spring }}
      >
        {children}
        {glare && (
          <motion.span
            aria-hidden
            className="pointer-events-none absolute inset-0 rounded-[inherit] opacity-0 transition-opacity duration-300 group-hover:opacity-100"
            style={{ background: glareBg }}
          />
        )}
      </motion.div>
    </div>
  )
}
