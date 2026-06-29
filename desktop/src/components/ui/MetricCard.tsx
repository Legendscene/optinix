import { type ReactNode } from 'react'
import { Card } from './Card'
import { ProgressBar } from './ProgressBar'
import { cn } from '../../lib/utils'

interface MetricCardProps {
  icon: ReactNode
  label: string
  value: string
  progress?: number
  progressColor?: string
  trend?: { value: string; up: boolean }
  sub?: string
  className?: string
  onClick?: () => void
}

export function MetricCard({ icon, label, value, progress, trend, sub, className, onClick }: MetricCardProps) {
  return (
    <Card hover onClick={onClick} className={cn('relative overflow-hidden', className)}>
      <div className="flex items-start justify-between mb-2">
        <div className="p-2 rounded-lg bg-surface-2 text-accent">{icon}</div>
        {trend && (
          <span className={cn('text-xs font-medium flex items-center gap-0.5', trend.up ? 'text-green' : 'text-red')}>
            <span>{trend.up ? '↑' : '↓'}</span>{trend.value}
          </span>
        )}
      </div>
      <div className="text-2xl font-semibold tracking-tight text-text">{value}</div>
      <div className="text-xs text-text-secondary mt-0.5">{label}</div>
      {progress !== undefined && <ProgressBar value={progress} className="mt-2" size="sm" />}
      {sub && <div className="text-[11px] text-text-tertiary mt-1">{sub}</div>}
    </Card>
  )
}
