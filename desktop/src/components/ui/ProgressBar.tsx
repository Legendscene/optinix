import { motion } from 'framer-motion'
import { cn } from '../../lib/utils'

interface ProgressBarProps {
  value: number
  max?: number
  color?: string
  className?: string
  size?: 'sm' | 'md' | 'lg'
  label?: string
}

const heights = { sm: 'h-1', md: 'h-1.5', lg: 'h-2' }

export function ProgressBar({ value, max = 100, color, className, size = 'md', label }: ProgressBarProps) {
  const pct = Math.min(Math.max((value / max) * 100, 0), 100)
  const barColor = color || (pct > 80 ? '#ef4444' : pct > 60 ? '#eab308' : '#22c55e')

  return (
    <div className={cn('w-full', className)}>
      {label && <div className="flex justify-between text-xs text-text-tertiary mb-1"><span>{label}</span><span>{Math.round(pct)}%</span></div>}
      <div className={cn('w-full rounded-full bg-surface-3 overflow-hidden', heights[size])}>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
          className={cn('rounded-full', heights[size])}
          style={{ backgroundColor: barColor }}
        />
      </div>
    </div>
  )
}
