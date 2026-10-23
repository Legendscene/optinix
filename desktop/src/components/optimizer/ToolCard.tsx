import { ArrowRight, CircleAlert, ShieldAlert, Star } from 'lucide-react'
import { cn } from '../../lib/utils'
import type { Tool } from '../../nav'

interface ToolCardProps {
  tool: Tool
  onOpen: () => void
  onTogglePin: () => void
  pinned?: boolean
}

/** Pressable card for one tool in the zone grid; the pin star is a nested
    control, so the outer handler must not fire on it. */
export function ToolCard({ tool, onOpen, onTogglePin, pinned }: ToolCardProps) {
  const Icon = tool.icon
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onOpen}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onOpen()
        }
      }}
      className="surface-card surface-card-interactive group relative p-3.5 cursor-pointer hover:border-eg-line focus-visible:outline-2 focus-visible:outline-eg-green"
    >
      <div className="flex items-start gap-3">
        <span className="w-8 h-8 rounded-lg bg-surface-3 border border-border flex items-center justify-center shrink-0 text-text-secondary group-hover:text-eg-green group-hover:bg-eg-green-dim group-hover:border-eg-line transition-colors duration-150">
          <Icon size={15} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <h4 className="font-display uppercase text-[12px] font-semibold tracking-[0.03em] text-text truncate">
              {tool.label}
            </h4>
            {tool.badge === 'danger' && <RiskBadge />}
            {tool.badge === 'admin' && <AdminBadge />}
          </div>
          <p className="mt-0.5 text-[11.5px] leading-[1.45] text-text-tertiary line-clamp-2">
            {tool.description}
          </p>
        </div>
        <div className="flex flex-col items-center gap-1 shrink-0 -mr-1 -mt-0.5">
          <button
            onClick={(e) => { e.stopPropagation(); onTogglePin() }}
            aria-label={pinned ? `Unpin ${tool.label}` : `Pin ${tool.label}`}
            title={pinned ? 'Unpin' : 'Pin to sidebar'}
            className={cn(
              'p-1 rounded transition-colors duration-150',
              pinned ? 'text-eg-green' : 'text-text-tertiary/50 hover:text-text-secondary opacity-0 group-hover:opacity-100 focus-visible:opacity-100',
            )}
          >
            <Star size={13} fill={pinned ? 'currentColor' : 'none'} />
          </button>
          <ArrowRight size={13} className="text-eg-green opacity-0 -translate-x-1 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-150" />
        </div>
      </div>
    </div>
  )
}

function RiskBadge() {
  return (
    <span
      title="Aggressive tuning. A restore point is taken first."
      className="inline-flex items-center gap-1 text-[10px] font-medium text-red bg-red-dim px-1.5 py-px rounded shrink-0"
    >
      <CircleAlert size={9} />
      risky
    </span>
  )
}

function AdminBadge() {
  return (
    <span
      title="Needs Administrator privileges"
      className="inline-flex items-center gap-1 text-[10px] font-medium text-yellow bg-yellow-dim px-1.5 py-px rounded shrink-0"
    >
      <ShieldAlert size={9} />
      admin
    </span>
  )
}
