import type { ReactNode } from 'react'
import { cn } from '../../lib/utils'

/**
 * One deliberate state for "no data / not available / failed", replacing the
 * scattered one-off empty boxes with a single visual language. A panel always
 * ends up in exactly one of four states: real data, a skeleton, an error, or
 * this panel — never an unexplained blank.
 */
export type StateTone = 'info' | 'unavailable' | 'error'

interface StatePanelProps {
  icon: ReactNode
  title: string
  detail?: string
  tone?: StateTone
  action?: ReactNode
  size?: 'sm' | 'lg'
  className?: string
}

const toneStyles: Record<StateTone, string> = {
  info: 'text-text-tertiary',
  unavailable: 'text-text-secondary',
  error: 'text-red',
}

const iconStyles: Record<StateTone, string> = {
  info: 'text-text-tertiary',
  unavailable: 'text-text-secondary',
  error: 'text-red bg-red-dim',
}

export function StatePanel({
  icon,
  title,
  detail,
  tone = 'info',
  action,
  size = 'lg',
  className,
}: StatePanelProps) {
  const pad = size === 'lg' ? 'py-10' : 'py-5'
  const iconWrap = size === 'lg' ? 'w-10 h-10 rounded-lg' : 'w-8 h-8 rounded-md'
  return (
    <div className={cn('flex flex-col items-center justify-center text-center gap-2', pad, className)}>
      <span className={cn(
        iconWrap,
        'flex items-center justify-center shrink-0',
        tone === 'error' ? iconStyles.error : 'bg-surface-2 border border-border',
        iconStyles[tone === 'error' ? 'error' : tone],
      )}>
        {icon}
      </span>
      <p className={cn('text-[13px] font-medium', tone === 'error' ? 'text-text' : 'text-text-secondary')}>
        {title}
      </p>
      {detail && (
        <p className={cn('text-[11.5px] leading-[1.5] max-w-[46ch]', toneStyles[tone])}>{detail}</p>
      )}
      {action}
    </div>
  )
}
