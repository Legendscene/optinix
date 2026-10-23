import type { ReactNode } from 'react'
import { cn } from '../../lib/utils'

/**
 * Shared page header used by every route. One visual rhythm: eyebrow-free
 * 20px title (page-title), 13px secondary subtitle, and 10px tertiary hint.
 * Actions slot on the right and wrap below the title on narrow windows.
 */
interface PageHeaderProps {
  title: string
  subtitle?: ReactNode
  hint?: string
  actions?: ReactNode
  className?: string
}

export function PageHeader({ title, subtitle, hint, actions, className }: PageHeaderProps) {
  return (
    <div className={cn('flex flex-wrap items-start justify-between gap-3', className)}>
      <div className="min-w-0">
        <h1 className="page-title text-text">{title}</h1>
        {subtitle != null && <p className="page-subtitle mt-1">{subtitle}</p>}
        {hint && (
          <p className="text-[10px] text-text-tertiary mt-0.5">{hint}</p>
        )}
      </div>
      {actions && <div className="shrink-0">{actions}</div>}
    </div>
  )
}
