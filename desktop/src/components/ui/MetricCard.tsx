import { type ReactNode } from 'react'
import { Card } from './Card'
import { ProgressBar } from './ProgressBar'
import { cn } from '../../lib/utils'

interface MetricCardProps {
  icon: ReactNode
  label: string
  value: string
  progress?: number
  /** Any CSS colour; defaults to the accent ramp. Tokens preferred. */
  progressColor?: string
  trend?: { value: string; up: boolean }
  sub?: string
  className?: string
  onClick?: () => void
}

/**
 * Single-reading tile: gradient icon chip, tabular value, optional progress.
 * The reading is the loudest thing on the card — label and helper text stay
 * quiet so a wall of these scans as data rather than as decoration.
 *
 * These are the app's KPI walls, so they take the shared 3D tilt: the grid
 * leans toward the pointer instead of sitting there as flat rectangles.
 */
export function MetricCard({ icon, label, value, progress, progressColor, trend, sub, className, onClick }: MetricCardProps) {
  return (
    <Card hover tilt onClick={onClick} className={cn('relative overflow-hidden', className)}>
      <div className="flex items-start justify-between mb-2.5">
        <span className="icon-chip text-accent h-9 w-9">{icon}</span>
        {trend && (
          <span className={cn('text-[11px] font-semibold flex items-center gap-0.5 tnum', trend.up ? 'text-green' : 'text-red')}>
            <span aria-hidden>{trend.up ? '↑' : '↓'}</span>{trend.value}
          </span>
        )}
      </div>
      <div className="text-[23px] font-semibold leading-none tracking-[-0.02em] text-text tnum">{value}</div>
      <div className="text-[11.5px] text-text-secondary mt-1.5">{label}</div>
      {progress !== undefined && <ProgressBar value={progress} color={progressColor} className="mt-3" size="sm" />}
      {sub && <div className="text-[10.5px] text-text-tertiary mt-1.5">{sub}</div>}
    </Card>
  )
}
