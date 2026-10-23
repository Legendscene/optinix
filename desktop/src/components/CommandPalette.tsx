import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import {
  Search, CornerDownLeft, Star, LayoutGrid, Command,
  ArrowUp, ArrowDown, X, Loader2, Zap,
} from 'lucide-react'
import { cn } from '../lib/utils'
import {
  TOOLS, TOOL_MAP, ZONES, ZONE_MAP, searchTools, type ZoneId, type Tool,
} from '../nav'
import type { Library } from '../hooks/useLibrary'

export type PaletteAction = {
  id: string
  label: string
  description: string
  keywords: string[]
  run: () => void
  pending?: boolean
}

type Row =
  | { kind: 'tool'; tool: Tool }
  | { kind: 'action'; action: PaletteAction }
  | { kind: 'zone'; zoneId: ZoneId }
  | { kind: 'header'; label: string; hint?: string }
  | { kind: 'empty' }

interface CommandPaletteProps {
  open: boolean
  onClose: () => void
  onNavigate: (id: string) => void
  library: Library
  actions: PaletteAction[]
}

const MAX_ROWS = 60

export function CommandPalette({
  open, onClose, onNavigate, library, actions,
}: CommandPaletteProps) {
  const [query, setQuery] = useState('')
  const [cursor, setCursor] = useState(0)
  const [showAllTools, setShowAllTools] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLDivElement>(null)
  const scrollLock = useRef(false)

  /* Reset transient state every time the palette opens. */
  useEffect(() => {
    if (!open) return
    setQuery('')
    setCursor(0)
    setShowAllTools(false)
    /* Focus after paint so the caret lands reliably in WebView2. */
    const id = requestAnimationFrame(() => inputRef.current?.focus())
    return () => cancelAnimationFrame(id)
  }, [open])

  /* Lock body scroll while open. */
  useEffect(() => {
    if (!open) return
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = prev }
  }, [open])

  const rows = useMemo<Row[]>(() => {
    const q = query.trim().toLowerCase()

    if (q) {
      const toolHits = searchTools(q, 24)
      const actionHits = actions
        .filter((a) => a.pending || hay(a).includes(q))
        .slice(0, 4)
      const zoneHits = ZONES.filter(
        (z) => z.label.toLowerCase().includes(q) || z.purpose.toLowerCase().includes(q),
      ).slice(0, 3)

      const out: Row[] = []
      if (actionHits.length) {
        out.push({ kind: 'header', label: 'Actions' })
        out.push(...actionHits.map((a): Row => ({ kind: 'action', action: a })))
      }
      if (toolHits.length) {
        out.push({ kind: 'header', label: `Tools · ${toolHits.length}` })
        out.push(...toolHits.map((t): Row => ({ kind: 'tool', tool: t })))
      }
      if (zoneHits.length) {
        out.push({ kind: 'header', label: 'Zones' })
        out.push(...zoneHits.map((z): Row => ({ kind: 'zone', zoneId: z.id })))
      }
      if (!toolHits.length && !actionHits.length && !zoneHits.length) {
        out.push({ kind: 'empty' })
      }
      return out.slice(0, MAX_ROWS)
    }

    /* No query: favourites, recents, then quick zones. */
    const out: Row[] = []

    if (library.favorites.length) {
      out.push({ kind: 'header', label: 'Favourites' })
      for (const id of library.favorites) {
        const tool = TOOL_MAP[id]
        if (tool) out.push({ kind: 'tool', tool })
      }
    }

    if (library.recents.length) {
      out.push({ kind: 'header', label: 'Recent', hint: 'Clear' })
      for (const r of library.recents) {
        const tool = TOOL_MAP[r.id]
        if (tool) out.push({ kind: 'tool', tool })
      }
    }

    if (actions.length) {
      out.push({ kind: 'header', label: 'Quick actions' })
      out.push(...actions.map((a): Row => ({ kind: 'action', action: a })))
    }

    out.push({ kind: 'header', label: 'Browse' })
    for (const z of ZONES) out.push({ kind: 'zone', zoneId: z.id })

    if (showAllTools) {
      out.push({ kind: 'header', label: 'All tools', hint: `${TOOLS.length}` })
      for (const t of TOOLS) out.push({ kind: 'tool', tool: t })
    }
    return out.slice(0, MAX_ROWS)
  }, [query, actions, library.favorites, library.recents, showAllTools])

  const selectable = useMemo(
    () => rows.filter((r) => r.kind === 'tool' || r.kind === 'action' || r.kind === 'zone'),
    [rows],
  )

  /* Keep the cursor on a real row as the result set changes. */
  useEffect(() => {
    setCursor((c) => Math.min(c, Math.max(0, selectable.length - 1)))
  }, [selectable.length])

  const activate = useCallback(
    (row: Row | undefined) => {
      if (!row) return
      if (row.kind === 'tool') {
        library.touch(row.tool.id)
        onNavigate(row.tool.id)
      } else if (row.kind === 'zone') {
        onNavigate(row.zoneId)
      } else if (row.kind === 'action') {
        library.touch(row.action.id)
        row.action.run()
      }
      onClose()
    },
    [library, onNavigate, onClose],
  )

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
        return
      }
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setCursor((c) => (c + 1) % Math.max(1, selectable.length))
        return
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault()
        setCursor((c) => (c - 1 + selectable.length) % Math.max(1, selectable.length))
        return
      }
      if (e.key === 'Home') { e.preventDefault(); setCursor(0); return }
      if (e.key === 'End') {
        e.preventDefault()
        setCursor(Math.max(0, selectable.length - 1))
        return
      }
      if (e.key === 'Enter') {
        e.preventDefault()
        activate(selectable[cursor])
      }
    },
    [selectable, cursor, activate, onClose],
  )

  /* Keep the active row in view. */
  useEffect(() => {
    if (scrollLock.current) return
    const el = listRef.current?.querySelector<HTMLElement>('[data-active="true"]')
    el?.scrollIntoView({ block: 'nearest' })
  }, [cursor])

  if (!open) return null

  let selIndex = -1

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-[14vh] px-6"
      role="dialog"
      aria-modal="true"
      aria-label="Command palette"
    >
      <button
        aria-label="Close"
        tabIndex={-1}
        onClick={onClose}
        className="absolute inset-0 bg-black/55 cursor-default"
      />

      <div
        className="relative w-full max-w-[620px] surface-card overflow-hidden shadow-e4 animate-rise flex flex-col max-h-[62vh]"
        onKeyDown={onKeyDown}
      >
        {/* Search field */}
        <div className="flex items-center gap-3 px-4 h-14 border-b border-border shrink-0">
          <Search size={16} className="text-text-tertiary shrink-0" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => { setQuery(e.target.value); setCursor(0) }}
            placeholder="Search 53 tools, zones and actions…"
            spellCheck={false}
            autoComplete="off"
            aria-label="Search tools and actions"
            className="flex-1 bg-transparent text-[15px] placeholder:text-text-tertiary outline-none"
          />
          <kbd className="px-1.5 py-0.5 rounded bg-surface-3 border border-border text-[10px] font-mono text-text-tertiary">
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div ref={listRef} className="overflow-y-auto py-1.5 flex-1" role="listbox">
          {rows.map((row) => {
            if (row.kind === 'header') {
              return (
                <div
                  key={`h-${row.label}`}
                  className="flex items-center justify-between px-4 pt-3 pb-1.5 first:pt-1.5"
                >
                  <span className="eyebrow">{row.label}</span>
                  {row.hint && (
                    <button
                      onClick={() => {
                        if (row.hint === 'Clear') library.clearRecents()
                        if (row.hint === 'All') setShowAllTools(true)
                      }}
                      className="text-[11px] text-text-tertiary hover:text-text transition-colors"
                    >
                      {row.hint}
                    </button>
                  )}
                </div>
              )
            }

            if (row.kind === 'empty') {
              return (
                <div key="empty" className="px-4 py-10 text-center">
                  <p className="text-sm text-text-secondary">No tool matches “{query}”</p>
                  <p className="text-xs text-text-tertiary mt-1">
                    Try “ram”, “dns”, “startup” or “junk”.
                  </p>
                </div>
              )
            }

            selIndex += 1
            const active = selIndex === cursor
            const common =
              'w-full flex items-center gap-3 px-4 py-2 text-left transition-colors duration-100'

            if (row.kind === 'tool') {
              const { tool } = row
              const fav = library.isFavorite(tool.id)
              const Icon = tool.icon
              return (
                <div
                  key={tool.id}
                  role="option"
                  aria-selected={active}
                  data-active={active}
                  className={cn(common, active ? 'bg-accent-dim' : 'hover:bg-surface-2')}
                  onMouseEnter={() => { scrollLock.current = true; setCursor(selIndex) }}
                  onMouseLeave={() => { scrollLock.current = false }}
                  onClick={() => activate(row)}
                >
                  <span className="relative flex items-center justify-center w-8 h-8 rounded-lg bg-surface-3 border border-border shrink-0">
                    <Icon size={15} className={active ? 'text-accent-ink' : 'text-text-secondary'} />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center gap-2">
                      <span className={cn('text-[13px] truncate', active ? 'text-text' : 'text-text-secondary')}>
                        {tool.label}
                      </span>
                      {tool.badge === 'danger' && (
                        <span className="text-[10px] font-medium text-red bg-red-dim px-1.5 py-px rounded">
                          risky
                        </span>
                      )}
                      {tool.badge === 'admin' && (
                        <span className="text-[10px] font-medium text-yellow bg-yellow-dim px-1.5 py-px rounded">
                          admin
                        </span>
                      )}
                    </span>
                    <span className="block text-[11px] text-text-tertiary truncate">
                      {ZONE_MAP[tool.zone].label} · {tool.group}
                    </span>
                  </span>
                  <span className="flex items-center gap-1.5 shrink-0">
                    {fav && <Star size={12} className="text-accent-ink" fill="currentColor" />}
                    {active && <CornerDownLeft size={12} className="text-text-tertiary" />}
                  </span>
                </div>
              )
            }

            if (row.kind === 'action') {
              const { action } = row
              return (
                <div
                  key={action.id}
                  role="option"
                  aria-selected={active}
                  data-active={active}
                  className={cn(common, active ? 'bg-accent-dim' : 'hover:bg-surface-2')}
                  onMouseEnter={() => { scrollLock.current = true; setCursor(selIndex) }}
                  onMouseLeave={() => { scrollLock.current = false }}
                  onClick={() => activate(row)}
                >
                  <span className="flex items-center justify-center w-8 h-8 rounded-lg bg-accent-dim text-accent-ink shrink-0">
                    {action.pending ? <Loader2 size={15} className="animate-spin" /> : <Zap size={15} />}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-[13px] truncate">{action.label}</span>
                    <span className="block text-[11px] text-text-tertiary truncate">
                      {action.description}
                    </span>
                  </span>
                  {active && <CornerDownLeft size={12} className="text-text-tertiary" />}
                </div>
              )
            }

            const zone = ZONE_MAP[row.zoneId]
            const ZoneIcon = zone.icon
            return (
              <div
                key={zone.id}
                role="option"
                aria-selected={active}
                data-active={active}
                className={cn(common, active ? 'bg-accent-dim' : 'hover:bg-surface-2')}
                onMouseEnter={() => { scrollLock.current = true; setCursor(selIndex) }}
                onMouseLeave={() => { scrollLock.current = false }}
                onClick={() => activate(row)}
              >
                <span className="flex items-center justify-center w-8 h-8 rounded-lg bg-surface-3 border border-border shrink-0">
                  <ZoneIcon size={15} className={active ? 'text-accent-ink' : 'text-text-secondary'} />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block text-[13px]">{zone.label}</span>
                  <span className="block text-[11px] text-text-tertiary truncate">{zone.tagline}</span>
                </span>
                {active && <CornerDownLeft size={12} className="text-text-tertiary" />}
              </div>
            )
          })}

          {!query && !showAllTools && (
            <div className="px-4 py-3 border-t border-border mt-1.5">
              <button
                onClick={() => setShowAllTools(true)}
                className="flex items-center gap-2 text-[12px] text-text-secondary hover:text-text transition-colors"
              >
                <LayoutGrid size={13} />
                Show all {TOOLS.length} tools
                <ArrowDown size={11} className="ml-0.5" />
              </button>
            </div>
          )}
        </div>

        {/* Footer legend */}
        <div className="flex items-center gap-4 px-4 h-9 border-t border-border bg-surface-1 text-[11px] text-text-tertiary shrink-0">
          <span className="flex items-center gap-1.5">
            <ArrowUp size={11} /><ArrowDown size={11} /> navigate
          </span>
          <span className="flex items-center gap-1.5">
            <CornerDownLeft size={11} /> open
          </span>
          <span className="flex items-center gap-1.5 ml-auto">
            <Command size={11} />K to toggle
          </span>
          <button
            onClick={onClose}
            aria-label="Close"
            className="hover:text-text transition-colors"
          >
            <X size={13} />
          </button>
        </div>
      </div>
    </div>,
    document.body,
  )
}

function hay(v: { label: string; description: string }): string {
  return `${v.label} ${v.description}`.toLowerCase()
}
