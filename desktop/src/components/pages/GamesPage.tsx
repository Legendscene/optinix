import { useEffect, useMemo, useRef, useState } from 'react'
import {
  Activity, CircleAlert, Clock, Cpu, FolderOpen, FolderSearch, Gamepad2,
  MemoryStick, MonitorPlay, Plus, Server, Sparkles, Star, HardDrive,
  Loader2, Play, RefreshCw, Search, ScanLine, Undo2, X, Wifi, TerminalSquare,
} from 'lucide-react'
import { cn } from '../../lib/utils'
import { PageHero } from '../ui/PageHero'
import { useGameLibrary } from '../../hooks/useGameLibrary'
import { useMountedRef } from '../../hooks/useMountedRef'
import { prefersReducedMotion } from '../../hooks/useMotionPreference'
import { api } from '../../lib/api'
import type { DiscoveredGame, GameExeCandidate, GameSessionData } from '../../types'

/** Format an epoch-seconds timestamp for the "last scan" line. */
function fmtTime(ts: number | null): string {
  if (!ts) return ''
  const d = new Date(ts * 1000)
  return d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

/** Human seconds -> "1h 04m" style session duration. */
function fmtDuration(s: number | null): string {
  if (s == null) return '—'
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  if (h > 0) return `${h}h ${String(m).padStart(2, '0')}m`
  if (m > 0) return `${m}m`
  return `${s}s`
}

const num = (v: unknown, unit = ''): string =>
  typeof v === 'number' && Number.isFinite(v) ? `${v}${unit}` : '—'

/** Backend-resolved cover art for a game (Steam store APIs behind
    core.game_artwork, disk-cached). A 404 means the backend could not
    verify any artwork for this title — the designed lettered tile takes
    over and the miss is remembered so the browser never retries a dead
    source inside one session. Never a broken-image icon. */
const failedCovers = new Map<string, number>() // game id -> failed-at (ms)
const COVER_RETRY_MS = 5 * 60_000 // a later scan/backend cache can fix it

const coverUrl = (game: DiscoveredGame) =>
  `/api/game-library/artwork?id=${encodeURIComponent(game.id)}`

const coverFailed = (id: string) => {
  const at = failedCovers.get(id)
  if (at == null) return false
  if (Date.now() - at > COVER_RETRY_MS) { failedCovers.delete(id); return false }
  return true
}

function GameArt({ game, size = 'lg' }: { game: DiscoveredGame; size?: 'sm' | 'lg' }) {
  const dims = size === 'lg' ? 'w-16 h-16 rounded-[12px]' : 'w-14 h-14 rounded-[10px]'
  const [failed, setFailed] = useState(() => coverFailed(game.id))
  const markFailed = () => { failedCovers.set(game.id, Date.now()); setFailed(true) }
  if (failed) {
    // Fallback: identity gradient tile with the game's initial — consistent,
    // theme-aware, and clearly not a real cover (no fake artwork).
    return (
      <span className={cn(dims,
        'bg-gradient-to-br from-surface-4 to-surface-3 border border-border',
        'flex items-center justify-center text-[22px] font-bold text-accent-ink shrink-0 select-none')}>
        {game.name.slice(0, 1)}
      </span>
    )
  }
  return (
    <img
      src={coverUrl(game)}
      alt=""
      onError={markFailed}
      className={cn(dims, 'object-cover shrink-0 bg-surface-3')}
      loading="lazy"
    />
  )
}

const STATUS_META: Record<string, { label: string; cls: string }> = {
  installed: { label: 'Installed', cls: 'text-green bg-green-dim' },
  running: { label: 'Running', cls: 'text-accent-ink bg-accent-dim' },
  missing: { label: 'Missing files', cls: 'text-yellow bg-yellow-dim' },
  restricted: { label: 'Access restricted', cls: 'text-text-secondary bg-surface-3' },
}

const SOURCE_LABEL: Record<string, string> = {
  steam: 'Steam', epic: 'Epic', riot: 'Riot', battlenet: 'Battle.net',
  gog: 'GOG', ea: 'EA app', ubisoft: 'Ubisoft', xbox: 'Xbox / Store',
  registry: 'Standalone', custom: 'Custom folder', gryphline: 'Gryphline',
  emulator: 'Emulator', manual: 'Manually added', startmenu: 'Start Menu',
}

/** Library category filter. 'native' = launcher-verified native installs,
    'manual' = user-imported plain executables,
    'emulator' = registered emulators: manual entries associated with one,
    plus discovery's own emulator shells (kind='emulator'). */
type Category = 'all' | 'native' | 'manual' | 'emulator'

const isManual = (g: DiscoveredGame) => g.source === 'manual'
const isEmulatorGame = (g: DiscoveredGame) =>
  (isManual(g) && !!g.emulator_id) || g.kind === 'emulator'

interface Filters {
  query: string
  source: string // 'all' | source id
  drive: string // 'all' | drive letter
  status: 'all' | 'installed' | 'running'
  category: Category
  favoritesOnly: boolean
}

const EMPTY_FILTERS: Filters = {
  query: '', source: 'all', drive: 'all', status: 'all',
  category: 'all', favoritesOnly: false,
}

/**
 * Gaming Center: the library is what the Windows PC actually has. Data comes
 * only from the backend discovery scan (launchers + validated folders);
 * predefined/profile titles never populate it. Selecting a game opens a
 * detail panel with real session metrics from the backend.
 */
export function GamesPage() {
  const lib = useGameLibrary()
  const mounted = useMountedRef()
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS)
  /** Add-game flow visibility. */
  const [showAdd, setShowAdd] = useState(false)
  /** Page-level feedback for detail-panel manual edits (rename/detach/remove). */
  const [localMsg, setLocalMsg] = useState<string | null>(null)
  const [roots, setRoots] = useState<string[]>([])
  const [newRoot, setNewRoot] = useState('')
  const [rootMsg, setRootMsg] = useState<string | null>(null)
  /** Profile preview for the detail popover: what the backend would change. */
  const [preview, setPreview] = useState<{ name: string; desc: string; tweaks: string[] } | null>(null)
  /** The game whose details panel is open. */
  const [selectedId, setSelectedId] = useState<string | null>(null)

  useEffect(() => {
    api.gameLibraryRoots()
      .then((r) => { if (mounted.current) setRoots(r.roots) })
      .catch(() => { /* roots are optional; page renders without them */ })
  }, [mounted])

  const addRoot = async () => {
    if (!newRoot.trim()) return
    setRootMsg(null)
    try {
      const r = await api.gameLibraryAddRoot(newRoot.trim())
      if (mounted.current) { setRoots(r.roots); setNewRoot('') }
      setRootMsg('Root added — run Refresh scan to pick it up.')
    } catch (e) {
      setRootMsg(e instanceof Error ? e.message : String(e))
    }
  }

  const removeRoot = async (root: string) => {
    try {
      const r = await api.gameLibraryRemoveRoot(root)
      if (mounted.current) setRoots(r.roots)
      setRootMsg(`Removed "${root}" — run Refresh scan to update the library.`)
    } catch (e) {
      setRootMsg(e instanceof Error ? e.message : String(e))
    }
  }

  const games = lib.library?.games ?? []
  const selected = games.find((g) => g.id === selectedId) ?? null

  const allSources = useMemo(
    () => Array.from(new Set(games.map((g) => g.source))).sort(),
    [games],
  )
  const allDrives = useMemo(
    () => Array.from(
      new Set(
        games
          .map((g) => g.install_path?.slice(0, 2).toUpperCase())
          .filter((d): d is string => !!d && /^[A-Z]:$/.test(d)),
      ),
    ).sort(),
    [games],
  )

  /* Default view = EVERY DETECTED GAME. A card must not vanish because its
     files are temporarily unreachable (drive unplugged) — 'missing' and
     'restricted' keep their own honest pill and stay visible; the status
     filter can still narrow to installed-only. Favorites and running sort
     first — the Gaming Center's own priority. */
  const filtered = useMemo(() => {
    const q = filters.query.trim().toLowerCase()
    return games.filter((g) => {
      if (filters.favoritesOnly && !lib.favorites.has(g.id)) return false
      if (filters.status === 'installed' && !(g.status === 'installed' || g.status === 'running')) return false
      if (filters.status === 'running' && g.status !== 'running') return false
      if (filters.source !== 'all' && g.source !== filters.source) return false
      if (filters.category === 'native' && (isManual(g) || g.kind === 'emulator')) return false
      if (filters.category === 'manual' && (isEmulatorGame(g) || !isManual(g))) return false
      if (filters.category === 'emulator' && !isEmulatorGame(g)) return false
      if (filters.drive !== 'all' && !(g.install_path && g.install_path.slice(0, 2).toUpperCase() === filters.drive)) return false
      if (q && !g.name.toLowerCase().includes(q)) return false
      return true
    }).sort((a, b) => {
      if (a.status === 'running' && b.status !== 'running') return -1
      if (b.status === 'running' && a.status !== 'running') return 1
      if (lib.favorites.has(a.id) && !lib.favorites.has(b.id)) return -1
      if (lib.favorites.has(b.id) && !lib.favorites.has(a.id)) return 1
      return a.name.localeCompare(b.name)
    })
  }, [games, filters, lib.favorites])

  const scan = (
    <button
      onClick={lib.scan}
      disabled={lib.progress?.running}
      className="flex items-center gap-1.5 h-8 px-3 rounded-lg border border-border bg-surface-2
        text-[12.5px] text-text-secondary hover:text-text hover:border-border-light transition-colors
        disabled:opacity-50 disabled:cursor-not-allowed"
    >
      {lib.progress?.running
        ? <Loader2 size={13} className="animate-spin" />
        : <RefreshCw size={13} />}
      Refresh scan
    </button>
  )

  return (
    <div className="page space-y-4 animate-rise pb-4">
      <PageHero
        eyebrow="Gaming"
        title="Gaming Center"
        subtitle="Verified games installed on this PC. Only installations whose files Optinix could validate appear here."
        icon={<Gamepad2 size={19} />}
        badges={
          lib.library?.scanned_at
            ? <span className="text-[11px] text-text-tertiary tnum">Last scan: {fmtTime(lib.library.scanned_at)}</span>
            : undefined
        }
        actions={
          <>
            {lib.appliedProfileId && (
              <button
                onClick={lib.revertProfile}
                className="flex items-center gap-1.5 h-8 px-3 rounded-lg border border-border bg-surface-2
                  text-[12.5px] text-text-secondary hover:text-text hover:border-border-light transition-colors"
              >
                <Undo2 size={13} /> Revert “{lib.appliedProfileId}”
              </button>
            )}
            <button
              onClick={() => setShowAdd((v) => !v)}
              aria-pressed={showAdd}
              className="flex items-center gap-1.5 h-8 px-3 rounded-lg bg-accent bg-[image:var(--grad-control)] text-on-accent
                text-[12.5px] font-medium hover:brightness-110 transition-colors"
            >
              <Plus size={13} /> Add Game
            </button>
            {scan}
          </>
        }
      />

      {(localMsg || lib.actionMsg) && (
        <div role="status" className="flex items-center gap-2 rounded-[10px] px-3.5 py-2.5
          text-[12.5px] bg-surface-2 border border-border text-text-secondary animate-rise">
          <Activity size={13} /> {localMsg ?? lib.actionMsg}
        </div>
      )}

      {/* Profile preview: fetched from the backend's own profile record, so
          it lists exactly what Apply would touch — never a guess. */}
      {preview && (
        <div role="dialog" aria-label="Profile preview"
          className="surface-card p-4 animate-rise">
          <div className="flex items-center justify-between">
            <h3 className="text-[13px] font-medium">Profile preview — {preview.name}</h3>
            <button onClick={() => setPreview(null)} aria-label="Close preview"
              className="text-text-tertiary hover:text-text">
              <X size={14} />
            </button>
          </div>
          {preview.desc && <p className="text-[12px] text-text-secondary mt-1">{preview.desc}</p>}
          <ul className="mt-2 flex flex-wrap gap-1.5">
            {preview.tweaks.map((t) => (
              <li key={t} className="text-[11px] bg-surface-3 rounded-md px-2 py-0.5 font-mono">{t}</li>
            ))}
          </ul>
          <p className="text-[11px] text-text-tertiary mt-2">
            Review only — use “Apply profile” on the card to make the backend perform the changes.
          </p>
        </div>
      )}

      {rootMsg && (
        <div role="status" className="flex items-center gap-2 rounded-[10px] px-3.5 py-2.5
          text-[12.5px] bg-yellow-dim text-yellow border border-yellow/30 animate-rise">
          <ScanLine size={13} /> {rootMsg}
        </div>
      )}

      {/* Scan progress (polled, real fraction from the backend) */}
      {lib.progress?.running && (
        <div className="surface-card p-4 space-y-2" role="status" aria-live="polite">
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-2 text-[12.5px] text-text-secondary">
              <Loader2 size={13} className="animate-spin" />
              Scanning launchers and folders… {lib.progress.games_found} found
            </span>
            <button
              onClick={lib.cancelScan}
              className="flex items-center gap-1 h-7 px-2.5 rounded-lg bg-surface-3
                hover:bg-red hover:text-on-accent text-text-secondary text-[11.5px] transition-colors"
            >
              <X size={11} /> Cancel
            </button>
          </div>
          <div className="h-1.5 rounded-full bg-surface-3 overflow-hidden">
            <div
              className="h-full bg-accent transition-all duration-300"
              style={{ width: `${Math.round(lib.progress.fraction * 100)}%` }}
            />
          </div>
        </div>
      )}

      {lib.state === 'loading' && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="surface-card h-[300px] animate-pulse-subtle" />
          ))}
        </div>
      )}

      {lib.state === 'error' && (
        <div className="surface-card p-5 flex items-start gap-3">
          <CircleAlert size={17} className="text-red shrink-0 mt-0.5" />
          <div>
            <p className="text-[13px] font-medium">Could not load the game library</p>
            <p className="text-[12px] text-text-secondary mt-1">{lib.error}</p>
            <p className="text-[11.5px] text-text-tertiary mt-1.5">
              The Optinix service must be running on 127.0.0.1:5420.
            </p>
          </div>
        </div>
      )}

      {lib.state === 'ready' && (
        <>
          {/* Scan diagnostics: compact by default, expandable on demand.
              Never fabricated — renders only after a real scan. */}
          {lib.library?.diagnostics && (
            <details className="surface-card p-4" data-testid="scan-diagnostics">
              <summary className="cursor-pointer select-none text-[12.5px] text-text-secondary
                flex items-center gap-2">
                <ScanLine size={13} />
                Scan diagnostics — {lib.library.diagnostics.verified_installed} verified ·
                {' '}{lib.library.diagnostics.candidates_found} candidates ·
                {' '}{lib.library.diagnostics.duplicates_removed} merged
              </summary>
              <ul className="mt-3 space-y-1.5">
                {lib.library.diagnostics.sources.map((s) => (
                  <li key={s.source} className="flex items-start gap-2 text-[12px]">
                    <span className={cn(
                      'text-[10px] font-medium px-1.5 py-px rounded shrink-0 w-[104px] text-center',
                      s.status === 'inspected' && s.games > 0 && 'text-green bg-green-dim',
                      s.status === 'inspected' && s.games === 0 && 'text-text-secondary bg-surface-3',
                      s.status === 'not_installed' && 'text-text-tertiary bg-surface-3',
                      s.status === 'access_restricted' && 'text-yellow bg-yellow-dim',
                      s.status === 'error' && 'text-red bg-red-dim',
                    )}>
                      {s.status === 'inspected' && s.games > 0 ? `OK · ${s.games}` :
                        s.status === 'not_installed' ? 'Not installed' :
                        s.status === 'access_restricted' ? 'Restricted' :
                        s.status === 'error' ? 'Error' : 'Inspected'}
                    </span>
                    <span className="text-text-secondary">{SOURCE_LABEL[s.source] ?? s.label}</span>
                    {s.notes.length > 0 && (
                      <span className="text-text-tertiary truncate" title={s.notes.join(' · ')}>
                        — {s.notes[0]}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
              {lib.library.diagnostics.duplicates_removed > 0 && (
                <p className="text-[11px] text-text-tertiary mt-2">
                  {lib.library.diagnostics.duplicates_removed} duplicate record
                  {lib.library.diagnostics.duplicates_removed === 1 ? '' : 's'} merged
                  during the scan.
                </p>
              )}
            </details>
          )}

          {/* Filters: search, category, launcher, drive, status, favorites */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary" />
              <input
                value={filters.query}
                onChange={(e) => setFilters((f) => ({ ...f, query: e.target.value }))}
                placeholder="Search installed games…"
                aria-label="Search installed games"
                className="w-full h-9 pl-9 pr-3 rounded-lg bg-surface-2 border border-border
                  text-[13px] text-text placeholder:text-text-tertiary outline-none
                  focus:border-accent/50 transition-colors"
              />
            </div>
            <select
              value={filters.category}
              onChange={(e) => setFilters((f) => ({ ...f, category: e.target.value as Category }))}
              aria-label="Filter by library category"
              className="h-9 px-2.5 rounded-lg bg-surface-2 border border-border text-[12.5px]
                text-text outline-none focus:border-accent/50"
            >
              <option value="all">All games</option>
              <option value="native">Native PC Games</option>
              <option value="manual">Manually Added</option>
              <option value="emulator">Emulator Games</option>
            </select>
            <select
              value={filters.source}
              onChange={(e) => setFilters((f) => ({ ...f, source: e.target.value }))}
              aria-label="Filter by launcher"
              className="h-9 px-2.5 rounded-lg bg-surface-2 border border-border text-[12.5px]
                text-text outline-none focus:border-accent/50"
            >
              <option value="all">All launchers</option>
              {allSources.map((s) => <option key={s} value={s}>{SOURCE_LABEL[s] ?? s}</option>)}
            </select>
            <select
              value={filters.drive}
              onChange={(e) => setFilters((f) => ({ ...f, drive: e.target.value }))}
              aria-label="Filter by installation drive"
              className="h-9 px-2.5 rounded-lg bg-surface-2 border border-border text-[12.5px]
                text-text outline-none focus:border-accent/50"
            >
              <option value="all">All drives</option>
              {allDrives.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
            <div className="grid grid-cols-2 gap-2">
              <select
                value={filters.status}
                onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value as Filters['status'] }))}
                aria-label="Filter by status"
                className="h-9 px-2.5 rounded-lg bg-surface-2 border border-border text-[12.5px]
                  text-text outline-none focus:border-accent/50 min-w-0"
              >
                <option value="installed">Installed only</option>
                <option value="running">Running now</option>
                <option value="all">All statuses</option>
              </select>
              <button
                onClick={() => setFilters((f) => ({ ...f, favoritesOnly: !f.favoritesOnly }))}
                aria-pressed={filters.favoritesOnly}
                aria-label="Show favorites only"
                className={cn(
                  'flex items-center justify-center gap-1.5 h-9 px-2 rounded-lg border text-[12.5px] transition-colors',
                  filters.favoritesOnly
                    ? 'bg-yellow-dim text-yellow border-yellow/40'
                    : 'bg-surface-2 border-border text-text-secondary hover:text-text',
                )}
              >
                <Star size={12} fill={filters.favoritesOnly ? 'currentColor' : 'none'} />
                Favorites
              </button>
            </div>
          </div>

          {/* Add Game flow: exe / folder / shortcut / emulator. All writes go
              through the backend validation; the UI never launches on add. */}
          {showAdd && lib.state === 'ready' && (
            <AddGamePanel
              lib={lib}
              onClose={() => setShowAdd(false)}
            />
          )}

          {filtered.length === 0 ? (
            <div className="surface-card py-10 flex flex-col items-center text-center gap-2.5">
              <Gamepad2 size={26} className="text-text-tertiary" />
              <p className="text-[13.5px] font-medium">
                {games.length === 0
                  ? 'No installed games detected yet'
                  : filters.favoritesOnly && games.length > 0
                    ? 'No favorites yet — star a game to pin it here'
                    : filters.query || filters.source !== 'all' || filters.drive !== 'all' || filters.status !== 'installed'
                      ? 'No installed game matches the filters'
                      : 'Nothing currently installed & not running'}
              </p>
              <p className="text-[12px] text-text-tertiary max-w-[40ch]">
                {games.length === 0
                  ? 'Run a refresh scan — Optinix reads Steam, Epic, Riot, Battle.net, GOG, EA app, Xbox/Store, Gryphline, installed emulators, the Windows uninstall registry and your custom folders.'
                  : 'Try clearing the search or choosing a different launcher or drive.'}
              </p>
              {games.length === 0 && (
                <button
                  onClick={lib.scan}
                  className="mt-1 flex items-center gap-1.5 h-8 px-3 rounded-lg bg-accent text-on-accent
                    text-[12px] font-medium hover:bg-accent-hover transition-colors"
                >
                  <RefreshCw size={12} /> Run scan
                </button>
              )}
            </div>
            ) : (
            <ul className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4 gap-3">
              {filtered.map((g) => (
                <GameCard
                  key={g.id}
                  game={g}
                  busy={lib.busyGame === g.id}
                  applied={lib.appliedProfileId === g.profile_id && !!g.profile_id}
                  favorite={lib.favorites.has(g.id)}
                  selected={selectedId === g.id}
                  manual={isManual(g)}
                  emulatorName={g.emulator?.name ?? null}
                  onToggleFavorite={() => lib.toggleFavorite(g)}
                  onSelect={() => setSelectedId(selectedId === g.id ? null : g.id)}
                  onOpen={() => lib.openFolder(g)}
                  onLaunch={() => isManual(g) ? lib.launchManual(g) : lib.launch(g)}
                  onPreview={async () => {
                    if (!g.profile_id) return
                    const p = await lib.previewProfile(g.profile_id)
                    if (p && mounted.current) {
                      setPreview({
                        name: p.name,
                        desc: p.description ?? '',
                        tweaks: Object.entries(p)
                          .filter(([k, v]) => k !== 'name' && k !== 'description' && v != null)
                          .map(([k]) => k),
                      })
                    }
                  }}
                  onApply={() => lib.applyProfile(g)}
                />
              ))}
            </ul>
          )}

          {/* Detail panel: identity, install data, live session metrics. */}
          {selected && (
            <GameDetails
              game={selected}
              fetchSession={lib.fetchSession}
              onClose={() => setSelectedId(null)}
              onRename={async (name) => { await lib.updateManual(selected.id, { name }); setLocalMsg(`Renamed to “${name}”`) }}
              onDetachEmulator={async () => { await lib.updateManual(selected.id, { emulator_id: null }); setLocalMsg('Emulator association removed') }}
              onRemove={async () => {
                if (!window.confirm(`Remove “${selected.name}” from the library? This will not delete any files.`)) return
                await lib.removeManual(selected.id)
                setSelectedId(null)
                setLocalMsg(`Removed “${selected.name}” from the library`)
              }}
            />
          )}

          {/* Optional section: user-approved custom scan roots. Separate from
              the library — never presented as pre-installed games. */}
          <details className="surface-card p-4">
            <summary className="cursor-pointer select-none text-[12.5px] text-text-secondary
              flex items-center gap-2">
              <HardDrive size={13} /> Custom game folders (optional)
            </summary>
            <p className="text-[11.5px] text-text-tertiary mt-2">
              Add drives or folders Optinix should scan for games the launchers did not report.
              Scans only these roots — never your whole PC.
            </p>
            {roots.length > 0 && (
              <ul className="mt-2 space-y-1">
                {roots.map((r) => (
                  <li key={r} className="flex items-center justify-between gap-2 text-[12px]
                    bg-surface-3 rounded-lg px-2.5 py-1.5">
                    <span className="truncate font-mono">{r}</span>
                    <button
                      onClick={() => removeRoot(r)}
                      className="text-text-tertiary hover:text-red shrink-0"
                      aria-label={`Remove root ${r}`}
                    >
                      <X size={12} />
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <div className="flex gap-2 mt-3">
              <input
                value={newRoot}
                onChange={(e) => setNewRoot(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') void addRoot() }}
                placeholder="e.g. D:\\Games"
                aria-label="Add scan root"
                className="flex-1 h-8 px-2.5 rounded-lg bg-surface-2 border border-border text-[12px]
                  font-mono text-text placeholder:text-text-tertiary outline-none focus:border-accent/50"
              />
              <button
                onClick={addRoot}
                className="h-8 px-3 rounded-lg bg-surface-3 hover:bg-accent hover:text-on-accent
                  text-text-secondary text-[12px] transition-colors"
              >
                Add
              </button>
            </div>
          </details>
        </>
      )}
    </div>
  )
}

function GameCard({ game, busy, applied, favorite, selected, manual, emulatorName, onToggleFavorite, onSelect, onOpen, onLaunch, onPreview, onApply }: {
  game: DiscoveredGame
  busy: boolean
  applied: boolean
  favorite: boolean
  selected: boolean
  manual: boolean
  emulatorName: string | null
  onToggleFavorite: () => void
  onSelect: () => void
  onOpen: () => void
  onLaunch: () => void
  onPreview: () => void
  onApply: () => void
}) {
  const meta = STATUS_META[game.status] ?? { label: game.status, cls: 'text-text-secondary bg-surface-3' }
  const drive = game.install_path?.slice(0, 2).toUpperCase() ?? null

  /* Perspective tilt: pointer position over the artwork drives a small
     rotateX/rotateY. Bounded at 4deg, applied straight to the DOM node
     (no re-render per mousemove) and skipped entirely under reduced
     motion. This is one of the two places tilt is allowed — the card
     body itself stays flat and readable. */
  const artRef = useRef<HTMLDivElement>(null)
  const onMove = (e: React.PointerEvent) => {
    const el = artRef.current
    if (!el || prefersReducedMotion()) return
    const r = el.getBoundingClientRect()
    const px = (e.clientX - r.left) / r.width - 0.5
    const py = (e.clientY - r.top) / r.height - 0.5
    el.style.transform = `perspective(900px) rotateX(${(-py * 4).toFixed(2)}deg) rotateY(${(px * 5).toFixed(2)}deg)`
  }
  const resetTilt = () => {
    const el = artRef.current
    if (el) el.style.transform = ''
  }

  return (
    <li
      className={cn(
        'group surface-card surface-card-interactive overflow-hidden flex flex-col',
        'transition-[border-color,box-shadow,transform] duration-200',
        'hover:-translate-y-0.5 hover:border-border-light',
        game.status === 'running' && 'border-accent-line shadow-glow-accent',
        selected && 'ring-1 ring-accent/60 border-accent/60',
      )}
    >
      {/* Artwork: the visual anchor. Tilt + zoom live here only. */}
      <div
        ref={artRef}
        onPointerMove={onMove}
        onPointerLeave={resetTilt}
        className="relative aspect-[16/9] overflow-hidden bg-surface-3 transition-transform duration-200 ease-out will-change-transform"
      >
        <GameCover game={game} />
        {/* Bottom scrim keeps the title legible over any artwork. */}
        <span
          aria-hidden
          className="absolute inset-x-0 bottom-0 h-2/3 pointer-events-none"
          style={{ background: 'linear-gradient(to top, rgba(8,9,12,0.92), rgba(8,9,12,0.35) 55%, transparent)' }}
        />
        {/* Soft edge lighting on hover. */}
        <span
          aria-hidden
          className="absolute inset-0 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-200"
          style={{ boxShadow: 'inset 0 0 0 1px var(--color-accent-line), inset 0 -32px 48px -32px var(--color-accent-dim)' }}
        />

        {/* Badges over the artwork. */}
        <div className="absolute top-2 left-2 flex items-center gap-1.5">
          <span className={cn(
            'text-[10px] font-medium px-1.5 py-0.5 rounded backdrop-blur-sm',
            'bg-black/45 text-white/90 border border-white/10',
          )}>
            {manual ? 'Manually added' : SOURCE_LABEL[game.source] ?? game.source}
          </span>
          {game.kind === 'emulator' && (
            <span
              className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-black/45 backdrop-blur-sm
                text-white/90 border border-white/10"
              title="Discovered emulator shell — kept separate from native PC games"
            >
              Emulator
            </span>
          )}
          {emulatorName && (
            <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-black/45 backdrop-blur-sm
              text-white/90 border border-white/10" title={`Launched through ${emulatorName}`}>
              via {emulatorName}
            </span>
          )}
        </div>

        {/* Status + drive, top-right. */}
        <div className="absolute top-2 right-2 flex items-center gap-1.5">
          <span className={cn('text-[10px] font-medium px-1.5 py-0.5 rounded backdrop-blur-sm', meta.cls)}>
            {meta.label}
          </span>
          {drive && (
            <span className="tnum text-[10px] font-medium px-1.5 py-0.5 rounded bg-black/45 backdrop-blur-sm
              text-white/90 border border-white/10">
              {drive}
            </span>
          )}
        </div>

        {/* Title over the scrim — the whole strip opens details. */}
        <button
          onClick={onSelect}
          aria-label={`Open details for ${game.name}`}
          className="absolute inset-x-0 bottom-0 p-3 text-left"
        >
          <span className="block text-[14px] font-semibold text-white truncate leading-tight drop-shadow">
            {game.name}
          </span>
          {game.exe_path && (
            <span className="block text-[10px] text-white/65 truncate font-mono mt-0.5" title={game.exe_path}>
              {game.exe_path}
            </span>
          )}
        </button>

        {/* Favorite, floating over the artwork corner. */}
        <button
          onClick={onToggleFavorite}
          aria-pressed={favorite}
          aria-label={favorite ? `Unfavorite ${game.name}` : `Favorite ${game.name}`}
          className={cn(
            'absolute bottom-3 right-3 p-1.5 rounded-lg backdrop-blur-sm transition-colors',
            'bg-black/45 border border-white/10',
            favorite ? 'text-yellow' : 'text-white/75 hover:text-yellow',
          )}
        >
          <Star size={14} fill={favorite ? 'currentColor' : 'none'} />
        </button>
      </div>

      {/* Actions. */}
      <div className="p-2.5 flex items-center gap-1.5">
        <button
          onClick={onOpen}
          disabled={busy || !game.install_path}
          title={game.install_path ? undefined : 'No accessible installation folder'}
          className="flex items-center gap-1.5 h-7 px-2.5 rounded-lg bg-surface-3 flex-1
            hover:bg-surface-4 text-text-secondary text-[11.5px] transition-colors disabled:opacity-50"
        >
          <FolderOpen size={11} /> Folder
        </button>
        <button
          onClick={onLaunch}
          disabled={busy || !(game.exe_path && (game.status === 'installed' || game.status === 'running'))}
          title={game.exe_path ? undefined : 'No verified executable — launch unavailable'}
          className="flex items-center justify-center gap-1.5 h-7 px-3 rounded-lg flex-1
            bg-accent-dim text-accent-ink text-[11.5px] font-medium
            hover:bg-accent hover:text-on-accent transition-colors disabled:opacity-50"
        >
          {busy ? <Loader2 size={11} className="animate-spin" /> : <Play size={11} fill="currentColor" />}
          Launch
        </button>
      </div>

      {game.profile_id && (
        <div className="flex items-center justify-between gap-2 border-t border-border px-2.5 py-2">
          <button
            onClick={onPreview}
            title="See what this profile changes before applying"
            className="flex items-center gap-1.5 h-7 px-2 rounded-lg text-text-tertiary
              hover:text-text text-[11px] transition-colors truncate"
          >
            <Sparkles size={11} /> {game.profile_id}
          </button>
          {applied ? (
            <span className="text-[10.5px] text-green font-medium shrink-0">applied</span>
          ) : (
            <button
              onClick={onApply}
              disabled={busy}
              className="flex items-center gap-1 h-7 px-2.5 rounded-lg bg-surface-3 shrink-0
                text-text-secondary text-[11px] hover:bg-accent hover:text-on-accent
                transition-colors disabled:opacity-50"
            >
              <Sparkles size={10} /> Apply
            </button>
          )}
        </div>
      )}
    </li>
  )
}

/** Card artwork: the backend resolves and caches verified Steam cover art
    (core.game_artwork) and serves it from /api/game-library/artwork. The
    designed tile is always the base layer — it shows while the image loads
    and stays when the endpoint answers 404 (no verified artwork), so
    neither a broken-image icon nor an endless spinner can appear. */
function GameCover({ game }: { game: DiscoveredGame }) {
  const [failed, setFailed] = useState(() => coverFailed(game.id))
  const [loaded, setLoaded] = useState(false)
  const markFailed = () => { failedCovers.set(game.id, Date.now()); setFailed(true) }

  return (
    <>
      {/* Designed fallback — always beneath the artwork. */}
      <span className="absolute inset-0 bg-gradient-to-br from-surface-4 via-surface-3 to-surface-2 flex items-center justify-center">
        <span className="grid-overlay absolute inset-0" />
        <span className="relative text-[44px] font-bold text-accent-ink/70 select-none leading-none">
          {game.name.slice(0, 1)}
        </span>
      </span>
      {!loaded && !failed && (
        <span aria-hidden className="absolute inset-0 bg-surface-3/60 animate-pulse-subtle" />
      )}
      {!failed && (
        <img
          src={coverUrl(game)}
          alt=""
          loading="lazy"
          decoding="async"
          onLoad={() => setLoaded(true)}
          onError={markFailed}
          className={cn(
            'absolute inset-0 w-full h-full object-cover object-top',
            'transition-[opacity,transform] duration-300 ease-out group-hover:scale-[1.05]',
            loaded ? 'opacity-100' : 'opacity-0',
          )}
        />
      )}
    </>
  )
}

/** One metric pill in the session view. value === null -> '—' (unavailable). */
function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="bg-surface-2 rounded-lg px-3 py-2 border border-border">
      <div className="flex items-center gap-1.5 text-[10.5px] text-text-tertiary">
        {icon} {label}
      </div>
      <p className="text-[14px] font-semibold tnum mt-0.5">{value}</p>
    </div>
  )
}

/** Details panel for one game: real identity/install data + a live session
    view. Metrics come from the backend (`/api/game-library/session/<id>`);
    unavailable values render as '—', never fabricated numbers. */
function GameDetails({ game, fetchSession, onClose, onRename, onDetachEmulator, onRemove }: {
  game: DiscoveredGame
  fetchSession: (g: DiscoveredGame) => Promise<GameSessionData | null>
  onClose: () => void
  onRename: (name: string) => Promise<void>
  onDetachEmulator: () => Promise<void>
  onRemove: () => Promise<void>
}) {
  const [data, setData] = useState<GameSessionData | null>(null)
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    let alive = true
    const load = async () => {
      const d = await fetchSession(game)
      if (alive) { setData(d); setLoaded(true) }
    }
    void load()
    // Light polling while running gives a live session clock; an installed
    // (not running) game is static, so it is fetched once.
    const t = window.setInterval(() => { if (data?.session.running) void load() }, 4000)
    return () => { alive = false; window.clearInterval(t) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [game.id])

  const sys = (data?.system_metrics ?? {}) as Record<string, unknown>
  const sess = data?.session

  return (
    <section className="surface-card p-5 animate-rise" aria-label={`Details for ${game.name}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-4 min-w-0">
          <GameArt game={game} />
          <div className="min-w-0">
            <h2 className="text-[16px] font-semibold truncate">{game.name}</h2>
            <div className="flex items-center gap-2 mt-1 text-[11.5px] text-text-secondary flex-wrap">
              <span className="bg-surface-3 rounded px-1.5 py-px">{SOURCE_LABEL[game.source] ?? game.source}</span>
              {game.kind === 'emulator' && (
                <span
                  className="bg-surface-3 rounded px-1.5 py-px"
                  title="Discovered emulator shell — kept separate from native PC games"
                >
                  Emulator
                </span>
              )}
              <span className={cn(
                'text-[10.5px] px-1.5 py-px rounded',
                sess?.running ? 'text-accent-ink bg-accent-dim' : 'text-text-secondary bg-surface-3')}>
                {sess?.running ? 'Running' : STATUS_META[game.status]?.label ?? game.status}
              </span>
              {game.appid != null && <span className="text-text-tertiary">Steam appid {game.appid}</span>}
            </div>
          </div>
        </div>
        <button onClick={onClose} aria-label="Close details"

          className="text-text-tertiary hover:text-text p-1">
          <X size={15} />
        </button>
      </div>

      {/* Installation facts (backend-verified only). */}
      <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1.5 mt-4 text-[12px]">
        <div className="flex gap-2 min-w-0">
          <dt className="text-text-tertiary w-[92px] shrink-0">Install path</dt>
          <dd className="font-mono truncate flex-1" title={game.install_path ?? ''}>
            {game.install_path ?? '—'}
          </dd>
        </div>
        <div className="flex gap-2 min-w-0">
          <dt className="text-text-tertiary w-[92px] shrink-0">Executable</dt>
          <dd className="font-mono truncate flex-1" title={game.exe_path ?? ''}>
            {game.exe_path ?? '— (launch unavailable)'}
          </dd>
        </div>
        <div className="flex gap-2">
          <dt className="text-text-tertiary w-[92px] shrink-0">Drive</dt>
          <dd>{game.install_path?.slice(0, 2).toUpperCase() ?? '—'}</dd>
        </div>
        <div className="flex gap-2">
          <dt className="text-text-tertiary w-[92px] shrink-0">Profile</dt>
          <dd>{game.profile_id ?? 'No compatible profile'}</dd>
        </div>
        {game.source === 'manual' && (
          <div className="flex gap-2">
            <dt className="text-text-tertiary w-[92px] shrink-0">Launch args</dt>
            <dd className="font-mono truncate flex-1">{game.args || '—'}</dd>
          </div>
        )}
        {game.emulator && (
          <div className="flex gap-2">
            <dt className="text-text-tertiary w-[92px] shrink-0">Emulator</dt>
            <dd className="truncate flex-1" title={game.emulator.exe_path}>
              {game.emulator.name}
            </dd>
          </div>
        )}
      </dl>

      {game.source === 'manual' && (
        <div className="flex items-center gap-2 mt-3 pt-3 border-t border-border">
          <button
            onClick={async () => {
              const name = window.prompt('New display name', game.name)
              if (name && name.trim() && name.trim() !== game.name) {
                try {
                  await onRename(name.trim())
                } catch { /* actionMsg already shows the backend error */ }
              }
            }}
            className="h-7 px-2.5 rounded-lg bg-surface-3 text-text-secondary text-[11.5px] hover:bg-surface-4 transition-colors"
          >
            Rename
          </button>
          {game.emulator_id != null && (
            <button
              onClick={onDetachEmulator}
              className="h-7 px-2.5 rounded-lg bg-surface-3 text-text-secondary text-[11.5px] hover:bg-surface-4 transition-colors"
            >
              Detach emulator
            </button>
          )}
          <button
            onClick={onRemove}
            className="h-7 px-2.5 rounded-lg bg-red-dim text-red text-[11.5px] hover:bg-red hover:text-on-accent transition-colors ml-auto"
          >
            Remove from library
          </button>
        </div>
      )}

      {/* Session view — only real backend values; unavailable = —. */}
      {!loaded ? (
        <div className="flex items-center gap-2 mt-4 text-[12px] text-text-tertiary">
          <Loader2 size={12} className="animate-spin" /> Loading session data…
        </div>
      ) : !data ? (
        <p className="mt-4 text-[12px] text-text-tertiary">
          Session data unavailable — the Optinix service did not respond.
        </p>
      ) : (
        <>
          <h3 className="text-[12.5px] font-medium mt-5 flex items-center gap-1.5">
            <MonitorPlay size={13} /> Current session
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-2">
            <Metric icon={<Clock size={11} />} label="Session time"
              value={sess?.running ? fmtDuration(sess.duration_s) : '—'} />
            <Metric icon={<Cpu size={11} />} label="Game CPU"
              value={sess?.running ? num(sess.game_cpu_pct, '%') : '—'} />
            <Metric icon={<MemoryStick size={11} />} label="Game RAM"
              value={sess?.running && sess.game_ram_mb != null ? `${sess.game_ram_mb} MB` : '—'} />
            <Metric icon={<Server size={11} />} label="System CPU"
              value={num(sys.cpu, '%')} />
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-2">
            <Metric icon={<MemoryStick size={11} />} label="System RAM"
              value={num(sys.ram, '%')} />
            <Metric icon={<Cpu size={11} />} label="GPU load"
              value={num(sys.gpu, '%')} />
            <Metric icon={<Activity size={11} />} label="GPU temp"
              value={num(sys.gpu_temp, '°C')} />
            <Metric icon={<Wifi size={11} />} label="Net ↓/↑"
              value={sys.network_download != null && sys.network_upload != null
                ? `${sys.network_download}/${sys.network_upload} MB/s` : '—'} />
          </div>
          {!sess?.running && (
            <p className="text-[11px] text-text-tertiary mt-3">
              Per-game CPU/RAM/session time need the game to be running. System-wide values
              come from the shared monitor and are not attributed to this game.
            </p>
          )}
        </>
      )}
    </section>
  )
}

/** Add Game panel: exe / folder / shortcut / emulator. Every path is
    validated by the backend before an entry is created, and nothing is
    launched by this flow. The manual path field is the secure selection
    mechanism here (the desktop shell runs pywebview without a JS file-picker
    bridge, so a native dialog is not available in this architecture). */
function AddGamePanel({ lib, onClose }: {
  lib: ReturnType<typeof useGameLibrary>
  onClose: () => void
}) {
  const [tab, setTab] = useState<'exe' | 'folder' | 'shortcut' | 'emulator'>('exe')
  const [msg, setMsg] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  // exe tab
  const [exePath, setExePath] = useState('')
  const [exeName, setExeName] = useState('')
  const [exeEmu, setExeEmu] = useState('') // '' = native, else emulator id

  // folder tab
  const [folderPath, setFolderPath] = useState('')
  const [folderName, setFolderName] = useState('')
  const [candidates, setCandidates] = useState<GameExeCandidate[] | null>(null)
  const [chosenExe, setChosenExe] = useState('')

  // shortcut tab
  const [lnkPath, setLnkPath] = useState('')
  const [resolved, setResolved] = useState<{ target: string; args: string; exists: boolean } | null>(null)
  const [lnkName, setLnkName] = useState('')

  // emulator tab
  const [emuName, setEmuName] = useState('')
  const [emuPath, setEmuPath] = useState('')
  const [emuArgs, setEmuArgs] = useState('')

  const run = async (fn: () => Promise<string>) => {
    setBusy(true); setMsg(null); setErr(null)
    try {
      const m = await fn()
      setMsg(m)
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  const TABS: { id: typeof tab; label: string }[] = [
    { id: 'exe', label: 'Executable' },
    { id: 'folder', label: 'From a folder' },
    { id: 'shortcut', label: 'Shortcut' },
    { id: 'emulator', label: 'Emulator' },
  ]

  const inputCls = [
    'w-full h-9 px-3 rounded-lg bg-surface-2 border border-border text-[12.5px] font-mono',
    'text-text placeholder:text-text-tertiary outline-none focus:border-accent/50 transition-colors',
  ].join(' ')
  const labelCls = 'block text-[11.5px] text-text-tertiary mb-1'
  const btnCls = [
    'h-9 px-4 rounded-lg bg-accent text-on-accent text-[12.5px] font-medium',
    'hover:bg-accent-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2',
  ].join(' ')

  return (
    <section className="surface-card p-4 space-y-3 animate-rise" aria-label="Add a game">
      <div className="flex items-center justify-between">
        <h3 className="text-[13px] font-medium flex items-center gap-2"><FolderSearch size={14} /> Add a game</h3>
        <button onClick={onClose} aria-label="Close add game panel" className="text-text-tertiary hover:text-text p-1">
          <X size={14} />
        </button>
      </div>
      <div className="flex gap-1 flex-wrap">
        {TABS.map((t) => (
          <button key={t.id}
            onClick={() => { setTab(t.id); setMsg(null); setErr(null); setResolved(null); setCandidates(null) }}
            aria-pressed={tab === t.id}
            className={cn('h-7 px-2.5 rounded-lg text-[11.5px] transition-colors',
              tab === t.id ? 'bg-accent-dim text-accent-ink font-medium' : 'bg-surface-3 text-text-secondary hover:text-text')}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'exe' && (
        <div className="space-y-2">
          <div>
            <label className={labelCls} htmlFor="add-exe-path">Full path to the game's .exe</label>
            <input id="add-exe-path" value={exePath} onChange={(e) => setExePath(e.target.value)}
              placeholder="C:\\Games\\MyGame\\MyGame.exe" className={inputCls} />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <div>
              <label className={labelCls} htmlFor="add-exe-name">Display name (optional)</label>
              <input id="add-exe-name" value={exeName} onChange={(e) => setExeName(e.target.value)}
                placeholder="My Game" className={cn(inputCls, 'font-sans')} />
            </div>
            <div>
              <label className={labelCls} htmlFor="add-exe-emu">Launch through emulator (optional)</label>
              <select id="add-exe-emu" value={exeEmu} onChange={(e) => setExeEmu(e.target.value)}
                className="w-full h-9 px-2.5 rounded-lg bg-surface-2 border border-border text-[12.5px] text-text outline-none focus:border-accent/50">
                <option value="">Native PC game (no emulator)</option>
                {lib.emulators.map((e) => <option key={e.id} value={e.id}>{e.name}</option>)}
              </select>
            </div>
          </div>
          <p className="text-[11px] text-text-tertiary">The path must exist on disk — the backend checks it before saving. The entry is labeled “Manually added”.</p>
          <button className={btnCls} disabled={busy || !exePath.trim()}
            onClick={() => run(async () => {
              await lib.addManualExe(exePath.trim(), exeName.trim(), exeEmu || null)
              setExePath(''); setExeName('')
              return 'Game added to the library as “Manually added”.'
            })}>
            {busy ? <Loader2 size={12} className="animate-spin" /> : <Plus size={12} />} Add to library
          </button>
        </div>
      )}

      {tab === 'folder' && (
        <div className="space-y-2">
          <div>
            <label className={labelCls} htmlFor="add-folder-path">Game installation folder</label>
            <input id="add-folder-path" value={folderPath} onChange={(e) => { setFolderPath(e.target.value); setCandidates(null); setChosenExe('') }}
              placeholder="C:\\Games\\MyGame" className={inputCls} />
          </div>
          <button className="h-8 px-3 rounded-lg bg-surface-3 text-text-secondary text-[12px] hover:bg-surface-4 transition-colors flex items-center gap-2"
            disabled={busy || !folderPath.trim()}
            onClick={() => run(async () => {
              const c = await lib.scanFolder(folderPath.trim())
              setCandidates(c)
              return c.length ? `${c.length} possible game executables found — pick the right one below.` : 'No plausible game executable found in that folder (installers/helpers are ignored).'
            })}>
            <ScanLine size={12} /> Find game executables
          </button>
          {candidates && candidates.length > 0 && (
            <div className="space-y-1 max-h-[180px] overflow-y-auto pr-1">
              {candidates.map((c) => (
                <label key={c.path} className={cn('flex items-center gap-2 text-[11.5px] rounded-lg px-2.5 py-1.5 cursor-pointer transition-colors',
                  chosenExe === c.path ? 'bg-accent-dim text-accent-ink' : 'bg-surface-2 hover:bg-surface-3 text-text-secondary')}>
                  <input type="radio" name="folder-exe" checked={chosenExe === c.path} onChange={() => setChosenExe(c.path)} className="accent-current" />
                  <span className="truncate font-mono" title={c.path}>{c.name}</span>
                  <span className="text-text-tertiary ml-auto shrink-0 tnum">{c.size_mb} MB</span>
                </label>
              ))}
            </div>
          )}
          {candidates && candidates.length === 0 && (
            <p className="text-[11.5px] text-yellow">No game executable candidates. Installers, updaters and helpers are never auto-selected — you can still add the exe directly from the Executable tab.</p>
          )}
          <div>
            <label className={labelCls} htmlFor="add-folder-name">Display name (optional)</label>
            <input id="add-folder-name" value={folderName} onChange={(e) => setFolderName(e.target.value)}
              placeholder="My Game" className={cn(inputCls, 'font-sans')} />
          </div>
          <button className={btnCls} disabled={busy || !folderPath.trim()}
            onClick={() => run(async () => {
              await lib.addManualFolder(folderPath.trim(), chosenExe, folderName.trim())
              setFolderPath(''); setFolderName(''); setCandidates(null); setChosenExe('')
              return chosenExe ? 'Folder game added with your chosen executable.' : 'Folder added — pick its executable later by editing the entry.'
            })}>
            {busy ? <Loader2 size={12} className="animate-spin" /> : <Plus size={12} />} Add folder game
          </button>
        </div>
      )}

      {tab === 'shortcut' && (
        <div className="space-y-2">
          <div>
            <label className={labelCls} htmlFor="add-lnk-path">Path to the .lnk shortcut</label>
            <input id="add-lnk-path" value={lnkPath} onChange={(e) => { setLnkPath(e.target.value); setResolved(null) }}
              placeholder="C:\\Users\\me\\Desktop\\Game.lnk" className={inputCls} />
          </div>
          <button className="h-8 px-3 rounded-lg bg-surface-3 text-text-secondary text-[12px] hover:bg-surface-4 transition-colors flex items-center gap-2"
            disabled={busy || !lnkPath.trim()}
            onClick={() => run(async () => {
              const r = await lib.resolveShortcut(lnkPath.trim())
              setResolved({ target: r.target || '', args: r.args, exists: r.exists })
              return r.target ? `Shortcut resolves to ${r.target}${r.exists ? '' : ' — TARGET IS MISSING ON DISK'}. Nothing was executed.` : 'Shortcut could not be resolved (see error below).'
            })}>
            <ScanLine size={12} /> Resolve target
          </button>
          {resolved && (
            <div className="bg-surface-2 rounded-lg px-3 py-2 text-[11.5px] space-y-1" role="status">
              <p className="font-mono truncate" title={resolved.target}>{resolved.target || '—'}</p>
              {resolved.args && <p className="text-text-tertiary font-mono">args: {resolved.args}</p>}
              <p className={resolved.exists ? 'text-green' : 'text-red'}>
                {resolved.exists ? 'Target exists — safe to import.' : 'Target file is missing; importing will save it as Missing until the path is valid again.'}
              </p>
            </div>
          )}
          <div>
            <label className={labelCls} htmlFor="add-lnk-name">Display name (optional)</label>
            <input id="add-lnk-name" value={lnkName} onChange={(e) => setLnkName(e.target.value)}
              placeholder="My Game" className={cn(inputCls, 'font-sans')} />
          </div>
          <p className="text-[11px] text-text-tertiary">Only the shortcut structure is read — the target is never executed here.</p>
          <button className={btnCls} disabled={busy || !resolved?.target}
            onClick={() => run(async () => {
              if (!resolved) return ''
              await lib.addManualExe(resolved.target, lnkName.trim(), null)
              setLnkPath(''); setResolved(null); setLnkName('')
              return 'Shortcut target imported as a manually added game.'
            })}>
            {busy ? <Loader2 size={12} className="animate-spin" /> : <Plus size={12} />} Import target
          </button>
        </div>
      )}

      {tab === 'emulator' && (
        <div className="space-y-2">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <div>
              <label className={labelCls} htmlFor="add-emu-name">Emulator name</label>
              <input id="add-emu-name" value={emuName} onChange={(e) => setEmuName(e.target.value)}
                placeholder="BlueStacks 5" className={cn(inputCls, 'font-sans')} />
            </div>
            <div>
              <label className={labelCls} htmlFor="add-emu-args">Launch arguments (optional)</label>
              <input id="add-emu-args" value={emuArgs} onChange={(e) => setEmuArgs(e.target.value)}
                placeholder="--instance Raccoon" className={inputCls} />
            </div>
          </div>
          <div>
            <label className={labelCls} htmlFor="add-emu-path">Full path to the emulator's .exe</label>
            <input id="add-emu-path" value={emuPath} onChange={(e) => setEmuPath(e.target.value)}
              placeholder="C:\\Program Files\\BlueStacks_nxt\\HD-Player.exe" className={inputCls} />
          </div>
          <p className="text-[11px] text-text-tertiary">After registering, associate games with this emulator from the Executable tab. Games inside the emulator are not auto-discovered — add them manually and pick this emulator when adding.</p>
          <button className={btnCls} disabled={busy || !emuPath.trim() || !emuName.trim()}
            onClick={() => run(async () => {
              await lib.addEmulator(emuName.trim(), emuPath.trim(), emuArgs.trim())
              setEmuName(''); setEmuPath(''); setEmuArgs('')
              return 'Emulator registered. Associate games with it from the Executable tab.'
            })}>
            {busy ? <Loader2 size={12} className="animate-spin" /> : <Plus size={12} />} Register emulator
          </button>
          {lib.emulators.length > 0 && (
            <ul className="space-y-1 pt-1">
              {lib.emulators.map((e) => (
                <li key={e.id} className="flex items-center gap-2 text-[11.5px] bg-surface-2 rounded-lg px-2.5 py-1.5">
                  <TerminalSquare size={12} className="text-text-tertiary shrink-0" />
                  <span className="font-medium">{e.name}</span>
                  <span className="truncate font-mono text-text-tertiary" title={e.exe_path}>{e.exe_path}</span>
                  <button onClick={() => run(async () => { await lib.removeEmulator(e.id); return `Removed ${e.name} — its games stay in the library, unassociated.` })}
                    className="ml-auto text-text-tertiary hover:text-red shrink-0" aria-label={`Remove emulator ${e.name}`}>
                    <X size={12} />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {msg && (
        <p role="status" className="flex items-center gap-2 text-[12px] text-green bg-green-dim rounded-lg px-3 py-2">
          <Activity size={12} /> {msg}
        </p>
      )}
      {err && (
        <p role="alert" className="flex items-center gap-2 text-[12px] text-red bg-red-dim rounded-lg px-3 py-2">
          <CircleAlert size={12} /> {err}
        </p>
      )}
    </section>
  )
}
