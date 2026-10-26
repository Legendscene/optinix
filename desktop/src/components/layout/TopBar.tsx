import { Bell, Search, Activity, Loader2, ChevronRight, SlidersHorizontal } from 'lucide-react'
import { cn } from '../../lib/utils'
import { ZONE_MAP, TOOL_MAP, type ZoneId } from '../../nav'

export interface TopBarVitals {
  cpu?: number
  ram?: number
  disk?: number
  netDown?: number
  fps?: number | null
  temp?: number | null
  optimizing?: boolean
}

interface TopBarProps {
  route: string
  zone: ZoneId
  vitals: TopBarVitals
  onOpenPalette: () => void
  onNavigate: (id: string) => void
  unreadNotifications?: number
  optimizing?: boolean
}

export function TopBar({
  route, zone, vitals, onOpenPalette, onNavigate, unreadNotifications, optimizing,
}: TopBarProps) {
  const tool = TOOL_MAP[route]
  const zoneMeta = ZONE_MAP[zone]
  const ZoneIcon = zoneMeta.icon

  return (
    <header className="app-topbar relative flex items-center gap-4 h-[60px] px-5 border-b border-border shrink-0">
      {/* Hairline catch-light along the top edge — separates the header
          from the content below like a machined panel lip. */}
      <span
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-px"
        style={{
          background:
            'linear-gradient(90deg, transparent, rgba(255,255,255,0.06) 35%, rgba(255,255,255,0.06) 65%, transparent)',
        }}
      />
      {/* Breadcrumb */}
      <nav className="flex items-center gap-1.5 min-w-0 shrink-0" aria-label="Breadcrumb">
        <button
          onClick={() => onNavigate(zone)}
          className="flex items-center gap-1.5 h-6 px-1 -ml-1 rounded-md text-[12.5px] text-text-tertiary hover:text-text-secondary hover:bg-surface-2 transition-colors duration-150"
        >
          <ZoneIcon size={13} />
          <span className="hidden lg:inline">{zoneMeta.label}</span>
        </button>
        {tool && (
          <>
            <ChevronRight size={12} className="text-text-tertiary/50" />
            <span className="text-[12.5px] text-text truncate max-w-[220px]">{tool.label}</span>
          </>
        )}
      </nav>

      {/* Search */}
      <div className="flex-1 flex justify-center">
        <button
          onClick={onOpenPalette}
          aria-label="Search tools (Ctrl+K)"
          className={cn(
            'group flex items-center gap-2.5 h-9 w-full max-w-[360px] px-3 rounded-[10px]',
            'bg-surface-2 border border-border text-text-tertiary',
            'hover:border-border-light hover:text-text-secondary hover:bg-surface-3',
            'transition-colors duration-150',
            'shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]',
          )}
        >
          <Search size={13} className="shrink-0" />
          <span className="text-[12.5px] flex-1 text-left truncate">
            Search tools, games, actions…
          </span>
          <kbd className="text-[10px] font-mono px-1 py-px rounded bg-surface-4 border border-border shrink-0">
            ⌃K
          </kbd>
        </button>
      </div>

      {/* Live vitals. Each one carries the same hue as its card on Home, so
          the shell and the dashboard read as one instrument set. */}
      <div className="flex items-center gap-1 shrink-0">
        <Vital label="CPU" value={vitals.cpu} hue="var(--color-accent)" />
        <Vital label="RAM" value={vitals.ram} hue="var(--color-violet)" />
        <Vital label="DISK" value={vitals.disk} hue="#d9a13a" />
        {vitals.fps != null && <Vital label="FPS" value={vitals.fps} raw hue="var(--color-cyan)" />}
        {vitals.temp != null && <Vital label="TEMP" value={vitals.temp} unit="°" hue="#e07a4f" />}
      </div>

      <span className="w-px h-5 bg-border shrink-0" />

      {optimizing && (
        <span className="flex items-center gap-1.5 text-[11px] text-accent-ink bg-accent-dim px-2 py-1 rounded-md shrink-0">
          <Loader2 size={11} className="animate-spin" />
          Optimizing
        </span>
      )}

      <button
        onClick={() => onNavigate('notifications')}
        aria-label="Notifications"
        className="relative p-1.5 rounded-lg text-text-tertiary hover:text-text hover:bg-surface-2 transition-colors duration-150"
      >
        <Bell size={15} />
        {!!unreadNotifications && unreadNotifications > 0 && (
          <span className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-accent" />
        )}
      </button>

      <button
        onClick={() => onNavigate('settings')}
        aria-label="Settings"
        className="p-1.5 rounded-lg text-text-tertiary hover:text-text hover:bg-surface-2 transition-colors duration-150"
      >
        <SlidersHorizontal size={15} />
      </button>
    </header>
  )
}

function Vital({ label, value, unit, raw, hue }: {
  label: string
  value?: number
  unit?: string
  raw?: boolean
  /** Data hue for this metric, shared with its card on Home. */
  hue?: string
}) {
  const tone =
    value == null ? 'text-text-tertiary'
      : !raw && value >= 90 ? 'text-red'
        : !raw && value >= 75 ? 'text-yellow'
          : 'text-text-secondary'

  return (
    <div
      className="flex items-baseline gap-1.5 px-2.5 py-1.5 rounded-lg hover:bg-surface-3 transition-colors duration-150 cursor-default"
      title={value == null ? `${label}: unavailable` : `${label}: ${value}${unit ?? '%'}`}
    >
      <span
        aria-hidden
        className="h-1.5 w-1.5 rounded-full shrink-0"
        style={{
          background: hue ?? 'var(--color-accent)',
          opacity: value == null ? 0.3 : 0.9,
          boxShadow: value == null ? 'none' : `0 0 6px -1px ${hue ?? 'var(--color-accent)'}`,
        }}
      />
      <span className="text-[9.5px] font-semibold tracking-[0.12em] text-text-tertiary uppercase">
        {label}
      </span>
      <span className={cn('font-display text-[12.5px] font-bold tnum tracking-[-0.02em]', tone)}>
        {value == null ? '—' : Math.round(value)}
        {value != null && unit}
      </span>
    </div>
  )
}

export function LiveDot({ className }: { className?: string }) {
  return <Activity size={12} className={cn('text-accent-ink', className)} />
}
