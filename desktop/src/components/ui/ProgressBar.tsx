import { motion } from 'framer-motion'
import { cn } from '../../lib/utils'

interface ProgressBarProps {
  value: number
  max?: number
  /** Any CSS colour. Tokens preferred; defaults to a semantic ramp. */
  color?: string
  className?: string
  size?: 'sm' | 'md' | 'lg'
  label?: string
}

const heights = { sm: 'h-1', md: 'h-1.5', lg: 'h-2' }

/**
 * Thin determinate bar.
 *
 * Colour now comes from tokens instead of hardcoded hexes, so the bar follows
 * the accent preset and the light theme. The fill is a two-stop gradient: the
 * leading edge is the pure colour, the tail fades into it, which reads as
 * direction of travel rather than a flat block.
 */
export function ProgressBar({ value, max = 100, color, className, size = 'md', label }: ProgressBarProps) {
  const pct = Math.min(Math.max((value / max) * 100, 0), 100)
  const barColor = color || (pct > 80 ? 'var(--color-red)' : pct > 60 ? 'var(--color-yellow)' : 'var(--color-green)')

  return (
    <div className={cn('w-full', className)}>
      {label && <div className="flex justify-between text-xs text-text-tertiary mb-1"><span>{label}</span><span className="tnum">{Math.round(pct)}%</span></div>}
      <div className={cn('w-full rounded-full bg-surface-3 overflow-hidden', heights[size])}>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
          className={cn('rounded-full', heights[size])}
          style={{
            backgroundImage: `linear-gradient(90deg, color-mix(in srgb, ${barColor} 45%, transparent), ${barColor})`,
          }}
        />
      </div>
    </div>
  )
}
