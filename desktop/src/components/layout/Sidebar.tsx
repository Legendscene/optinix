import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import {
  ChevronsLeft, ChevronsRight, Search, Star, Hexagon, ShieldAlert, Command,
} from 'lucide-react'
import { cn } from '../../lib/utils'
import { ZONE_MAP, TOOL_MAP, type ZoneId } from '../../nav'
import type { Library } from '../../hooks/useLibrary'

/** Sidebar grouping: which destinations sit under which eyebrow. */
const NAV_GROUPS: { label: string; ids: ZoneId[] }[] = [
  { label: 'Start', ids: ['home', 'monitor'] },
  { label: 'Tune', ids: ['performance', 'gaming', 'games', 'network', 'optimizer'] },
  { label: 'Understand', ids: ['diagnostics', 'reports', 'history'] },
  { label: 'App', ids: ['personalization', 'settings'] },
]

interface SidebarProps {
  /** Current route id. May be a zone id or a tool id. */
  active: string
  /** Zone that owns the current route. */
  zone: ZoneId
  onNavigate: (id: string) => void
  onOpenPalette: () => void
  library: Library
  isAdmin: boolean | null
}

export function Sidebar({
  active, zone, onNavigate, onOpenPalette, library, isAdmin,
}: SidebarProps) {
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem('optinix-nav') === 'collapsed')
  const [tip, setTip] = useState<{ text: string; sub?: string; x: number; y: number } | null>(null)
  const closeTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)

  useEffect(() => {
    try { localStorage.setItem('optinix-nav', collapsed ? 'collapsed' : 'expanded') } catch { /* storage unavailable */ }
  }, [collapsed])

  /* The collapse shortcut is handled here because this component owns the state. */
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'b') {
        e.preventDefault()
        setCollapsed((c) => !c)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  useEffect(() => () => clearTimeout(closeTimer.current), [])

  const showTip = (e: React.MouseEvent, text: string, sub?: string) => {
    if (!collapsed) return
    clearTimeout(closeTimer.current)
    const r = (e.currentTarget as HTMLElement).getBoundingClientRect()
    setTip({ text, sub, x: r.right + 10, y: r.top + r.height / 2 })
  }
  const hideTip = () => {
    clearTimeout(closeTimer.current)
    closeTimer.current = setTimeout(() => setTip(null), 80)
  }

  const pinnedTools = library.favorites
    .map((id) => TOOL_MAP[id])
    .filter((t): t is NonNullable<typeof t> => Boolean(t))

  return (
    <>
      <aside
        className={cn(
          'app-sidebar relative flex flex-col h-full shrink-0 border-r border-border',
          'transition-[width] duration-200 ease-out',
          collapsed ? 'w-[64px]' : 'w-[244px]',
        )}
      >
        {/* Ambient top light: one restrained glow behind the brand, so the
            rail reads as an elevated surface instead of a flat strip. */}
        <span
          aria-hidden
          className="pointer-events-none absolute inset-x-0 top-0 h-44"
          style={{
            background:
              'radial-gradient(120% 100% at 50% -40%, rgba(46,230,207,0.11), transparent 72%)',
          }}
        />

        {/* Brand */}
        <div className={cn('relative flex items-center h-[60px] shrink-0 border-b border-border', collapsed ? 'justify-center px-2' : 'px-4 gap-3')}>
          <div
            className="relative w-8 h-8 rounded-[10px] flex items-center justify-center shrink-0"
            style={{
              background: 'linear-gradient(150deg, #3ff0d9 0%, #16b9a5 55%, #0c7f74 100%)',
              boxShadow:
                'inset 0 1px 0 rgba(255,255,255,0.45), inset 0 -2px 6px rgba(0,40,34,0.55), 0 10px 22px -12px rgba(46,230,207,0.7)',
            }}
          >
            <Hexagon size={16} className="text-[#04120f]" strokeWidth={2.6} />
          </div>
          {!collapsed && (
            <div className="min-w-0">
              <div className="font-display text-[15px] font-bold leading-none tracking-[-0.03em]">Optinix</div>
              <div className="mt-1 text-[9px] font-semibold uppercase tracking-[0.16em] text-text-tertiary leading-none">
                Performance
              </div>
            </div>
          )}
        </div>

        <nav className="relative flex-1 overflow-y-auto overflow-x-hidden py-3 flex flex-col gap-4">
          {/* Search trigger */}
          <div className={cn(collapsed ? 'px-2.5' : 'px-3')}>
            <button
              onClick={onOpenPalette}
              onMouseEnter={(e) => showTip(e, 'Search tools', 'Ctrl + K')}
              onMouseLeave={hideTip}
              aria-label="Search tools (Ctrl+K)"
              className={cn(
                'w-full flex items-center gap-2.5 h-8 rounded-[9px] border border-border bg-surface-2',
                'text-text-tertiary hover:text-text-secondary hover:border-border-light',
                'transition-colors duration-150',
                collapsed ? 'justify-center px-0' : 'px-2.5',
              )}
            >
              <Search size={14} className="shrink-0" />
              {!collapsed && (
                <>
                  <span className="text-[12px] flex-1 text-left">Search…</span>
                  <kbd className="text-[10px] font-mono px-1 py-px rounded bg-surface-4 border border-border">
                    ⌃K
                  </kbd>
                </>
              )}
            </button>
          </div>

          {/* Destinations, grouped so 12 items still scan at a glance */}
          <div className={cn(collapsed ? 'px-2.5' : 'px-3')}>
            <ul className="space-y-0.5">
              {NAV_GROUPS.map((group) => (
                <li key={group.label} className="pt-1 first:pt-0">
                  {!collapsed && (
                    <div className="eyebrow px-2 mb-1.5">{group.label}</div>
                  )}
                  <ul className="space-y-0.5">
                    {group.ids.map((id) => {
                      const z = ZONE_MAP[id]
                      if (!z) return null
                      const Icon = z.icon
                      const isActive = zone === z.id
                      return (
                        <li key={z.id}>
                          <button
                            onClick={() => onNavigate(z.id)}
                            onMouseEnter={(e) => showTip(e, z.label, z.tagline)}
                            onMouseLeave={hideTip}
                            title={collapsed ? z.label : undefined}
                            aria-current={isActive ? 'page' : undefined}
                            className={cn(
                              'group relative w-full flex items-center rounded-[9px] transition-colors duration-150',
                              collapsed ? 'h-9 justify-center' : 'h-8 gap-2.5 px-2',
                              isActive
                                ? 'text-text font-medium'
                                : 'text-text-secondary hover:bg-surface-2 hover:text-text',
                            )}
                          >
                            {/* One pill for the whole rail: framer-motion keeps
                                it mounted and slides it between items, so
                                selection reads as a single object moving. */}
                            {isActive && (
                              <motion.span
                                layoutId="nav-active"
                                aria-hidden
                                className="pointer-events-none absolute inset-0 rounded-[10px]"
                                style={{
                                  background:
                                    'linear-gradient(90deg, rgba(46,230,207,0.16), rgba(46,230,207,0.05) 62%, transparent)',
                                  boxShadow:
                                    'inset 0 1px 0 rgba(255,255,255,0.07), inset 0 0 0 1px rgba(46,230,207,0.16)',
                                }}
                                transition={{ type: 'spring', stiffness: 420, damping: 34, mass: 0.7 }}
                              />
                            )}
                            {/* Active rail */}
                            <span
                              className={cn(
                                'absolute left-0 top-1/2 -translate-y-1/2 w-[2px] rounded-r-full bg-accent transition-all duration-200',
                                isActive ? 'h-5 opacity-100' : 'h-0 opacity-0',
                              )}
                              style={isActive ? { boxShadow: '0 0 10px 1px rgba(46,230,207,0.6)' } : undefined}
                            />
                            <Icon
                              size={15}
                              className={cn(
                                'relative shrink-0 transition-colors',
                                isActive && 'text-accent-ink',
                              )}
                            />
                            {!collapsed && (
                              <span className="relative text-[13px] truncate">{z.label}</span>
                            )}
                          </button>
                        </li>
                      )
                    })}
                  </ul>
                </li>
              ))}
            </ul>
          </div>

          {/* Pinned tools */}
          {pinnedTools.length > 0 && (
            <div className={cn('mt-auto', collapsed ? 'px-2.5' : 'px-3')}>
              {!collapsed && (
                <div className="eyebrow px-2 mb-1.5 flex items-center gap-1.5">
                  <Star size={10} />
                  Pinned
                </div>
              )}
              <ul className="space-y-0.5">
                {pinnedTools.map((t) => {
                  const Icon = t.icon
                  const isActive = active === t.id
                  return (
                    <li key={t.id}>
                      <button
                        onClick={() => onNavigate(t.id)}
                        onMouseEnter={(e) => showTip(e, t.label, ZONE_MAP[t.zone].label)}
                        onMouseLeave={hideTip}
                        title={collapsed ? t.label : undefined}
                        className={cn(
                          'relative w-full flex items-center rounded-[9px] transition-colors duration-150',
                          collapsed ? 'h-9 justify-center' : 'h-8 gap-2.5 px-2',
                          isActive
                            ? 'text-text'
                            : 'text-text-secondary hover:bg-surface-2 hover:text-text',
                        )}
                      >
                        {isActive && (
                          <motion.span
                            layoutId="nav-active"
                            aria-hidden
                            className="pointer-events-none absolute inset-0 rounded-[9px] bg-surface-3"
                            transition={{ type: 'spring', stiffness: 420, damping: 34, mass: 0.7 }}
                          />
                        )}
                        <Icon size={14} className="relative shrink-0" />
                        {!collapsed && (
                          <span className="relative text-[12.5px] truncate flex-1 text-left">{t.label}</span>
                        )}
                      </button>
                    </li>
                  )
                })}
              </ul>
            </div>
          )}
        </nav>

        {/* Footer */}
        <div className="relative shrink-0 border-t border-border">
          {isAdmin === false && (
            collapsed ? (
              <div
                onMouseEnter={(e) => showTip(e, 'Limited mode', 'Optinix is not running as Administrator')}
                onMouseLeave={hideTip}
                role="button"
                tabIndex={0}
                aria-label="Limited mode — not running as Administrator"
                title="Limited mode — not running as Administrator"
                className="flex items-center justify-center h-9 text-yellow bg-yellow-dim/60 border-b border-border"
              >
                <ShieldAlert size={13} className="shrink-0" />
              </div>
            ) : (
              <div className="px-3 py-2.5 text-yellow bg-yellow-dim/40 border-b border-border">
                <div className="flex items-center gap-2">
                  <ShieldAlert size={13} className="shrink-0" />
                  <span className="text-[11.5px] font-semibold">Limited mode</span>
                </div>
                <p className="text-[11px] leading-[1.45] text-yellow/80 mt-1">
                  Optinix isn’t running as Administrator, so the steps that change
                  system settings — startup, services, network, registry and most
                  optimizers — are skipped. Monitoring, scanning and reports still work.
                </p>
                <p className="text-[11px] leading-[1.45] text-yellow/80 mt-1.5">
                  To unlock them, close Optinix and reopen it with{' '}
                  <span className="font-medium text-yellow">Run as administrator</span>.
                </p>
              </div>
            )
          )}

          <button
            onClick={() => setCollapsed((c) => !c)}
            onMouseEnter={(e) => showTip(e, collapsed ? 'Expand sidebar' : 'Collapse sidebar', 'Ctrl + B')}
            onMouseLeave={hideTip}
            className={cn(
              'w-full flex items-center gap-2.5 h-10 text-text-tertiary hover:text-text-secondary',
              'transition-colors duration-150',
              collapsed ? 'justify-center' : 'px-4',
            )}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            aria-expanded={!collapsed}
          >
            {collapsed ? <ChevronsRight size={15} /> : <ChevronsLeft size={15} />}
            {!collapsed && (
              <>
                <span className="text-[12px] flex-1 text-left">Collapse</span>
                <Command size={11} className="opacity-60" />
              </>
            )}
          </button>
        </div>
      </aside>

      {/* Tooltip layer */}
      {tip && (
        <div
          className="fixed z-50 pointer-events-none animate-fade-in"
          style={{ left: tip.x, top: tip.y, transform: 'translateY(-50%)' }}
        >
          <div className="surface-card shadow-e3 px-2.5 py-1.5 max-w-[240px]">
            <div className="text-[12px] text-text leading-tight">{tip.text}</div>
            {tip.sub && (
              <div className="text-[10.5px] text-text-tertiary leading-tight mt-0.5">{tip.sub}</div>
            )}
          </div>
        </div>
      )}
    </>
  )
}
