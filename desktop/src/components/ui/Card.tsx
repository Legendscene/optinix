import { useRef, type PointerEvent, type ReactNode } from 'react'
import { motion } from 'framer-motion'
import { prefersReducedMotion } from '../../hooks/useMotionPreference'
import { TiltCard } from './TiltCard'
import { cn } from '../../lib/utils'

interface CardProps {
  children: ReactNode
  className?: string
  hover?: boolean
  glass?: boolean
  onClick?: () => void
  padding?: 'sm' | 'md' | 'lg'
  /** Lean toward the pointer in 3D. Delegates to `TiltCard`, so the pointer
      maths stays owned by one component. Off by default: dense tables and
      full-width panels read better flat. */
  tilt?: boolean
}

const paddings = { sm: 'p-3', md: 'p-4', lg: 'p-6' }

/**
 * The app's default panel.
 *
 * Every legacy page builds on this component, so the design language lives
 * here rather than in fifty page files: token radius, token elevation, the
 * shared corner sheen (`.card-depth`) and an optional pointer sheen. Pages can
 * still override the surface colour through `className`.
 */
export function Card({ children, className, hover, glass, onClick, padding = 'md', tilt }: CardProps) {
  const host = useRef<HTMLDivElement>(null)
  const interactive = Boolean(hover || onClick)

  /* Interactive cards carry their own light: the spotlight gradient in
     `.card-depth` is centred on the pointer. Written straight to the element
     (no state, no re-render) and skipped entirely under reduced motion, where
     the patch stays centred instead of chasing the cursor. */
  const onMove = (e: PointerEvent<HTMLDivElement>) => {
    const el = host.current
    if (!el || !interactive || prefersReducedMotion()) return
    const r = el.getBoundingClientRect()
    if (!r.width || !r.height) return
    el.style.setProperty('--gx', `${((e.clientX - r.left) / r.width) * 100}%`)
    el.style.setProperty('--gy', `${((e.clientY - r.top) / r.height) * 100}%`)
  }

  /* Drop the pointer position on leave so the light returns to the card's
     resting centre instead of staying parked where the cursor last was. */
  const onLeave = () => {
    const el = host.current
    if (!el || !interactive) return
    el.style.removeProperty('--gx')
    el.style.removeProperty('--gy')
  }

  const body = (
    <motion.div
      ref={host}
      onPointerMove={onMove}
      onPointerLeave={onLeave}
      whileHover={hover ? { y: -2, boxShadow: 'var(--shadow-e3)' } : undefined}
      transition={{ type: 'spring', stiffness: 300, damping: 24 }}
      onClick={onClick}
      className={cn(
        'card-depth relative rounded-[var(--radius-card)] border border-border bg-surface-1 shadow-e1',
        paddings[padding],
        hover && 'sheen cursor-pointer transition-colors hover:border-border-light',
        glass && 'surface-glass',
        tilt && 'h-full',
        className
      )}
    >
      {children}
    </motion.div>
  )

  if (!tilt) return body

  return (
    <TiltCard className="h-full min-w-0" innerClassName="h-full">
      {body}
    </TiltCard>
  )
}
