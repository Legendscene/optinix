import { cn } from '../../lib/utils'

interface StatusPillProps {
  label: string
  value: string
  color?: string
  alert?: boolean
}

export function StatusPill({ label, value, color, alert }: StatusPillProps) {
  return (
    <div className={cn('flex items-center gap-2 px-2.5 py-1 rounded-lg bg-surface-2 border border-border text-xs')}>
      <span className={cn('w-1.5 h-1.5 rounded-full', alert ? 'bg-red animate-pulse-subtle' : 'bg-green')} style={!alert ? { backgroundColor: color || '#22c55e' } : undefined} />
      <span className="text-text-tertiary">{label}</span>
      <span className="text-text font-medium">{value}</span>
    </div>
  )
}
