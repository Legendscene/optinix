import { type ReactNode } from 'react'
import { cn } from '../../lib/utils'

interface BadgeProps {
  children: ReactNode
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info' | 'accent'
  className?: string
}

const variants = {
  default: 'bg-surface-3 text-text-secondary',
  success: 'bg-green-dim text-green',
  warning: 'bg-yellow-dim text-yellow',
  danger: 'bg-red-dim text-red',
  info: 'bg-cyan-dim text-cyan',
  accent: 'bg-accent-dim text-accent',
}

export function Badge({ children, variant = 'default', className }: BadgeProps) {
  return (
    <span className={cn('inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium', variants[variant], className)}>
      {children}
    </span>
  )
}
