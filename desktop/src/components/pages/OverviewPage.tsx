import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Zap, Play, Check, Loader2, AlertTriangle, ArrowRight, ShieldAlert,
  Star, Gamepad2, Activity, ChevronRight, Info, Gauge,
  CircleCheck, CircleAlert, TriangleAlert, Cpu, Monitor, MemoryStick,
  Thermometer, Timer, X,
} from 'lucide-react'
import { cn, formatDuration, formatRelative } from '../../lib/utils'
import { useMountedRef } from '../../hooks/useMountedRef'
import { api } from '../../lib/api'
import type {
  Overview, OptimizeRun, PresetMode, GameProfileSummary, OverviewAction,
} from '../../types'
import type { Library } from '../../hooks/useLibrary'
import type { IconComponent } from '../../nav'

interface OverviewPageProps {
  onNavigate: (id: string) => void
  library: Library
  onOptimizingChange: (busy: boolean) => void
}

const VITAL_POLL_MS = 4000
const MAX_SHOWN_GAMES = 6

export function OverviewPage({
  onNavigate, library, onOptimizingChange,
}: OverviewPageProps) {
  const [data, setData] = useState<Overview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [presets, setPresets] = useState<PresetMode[]>([])
  const [run, setRun] = useState<OptimizeRun | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [ping, setPing] = useState<number | null>(null)
  const [pinging, setPinging] = useState(false)
  const [notice, setNotice] = useState<{ tone: 'ok' | 'warn' | 'error'; text: string } | null>(null)
  const [games, setGames] = useState<GameProfileSummary[]>([])

  const mounted = useMountedRef()

  const load = useCallback(async (opts: { quiet?: boolean } = {}) => {
    try {
      const d = await api.overview()
      if (!mounted.current) return
      setData(d)
      setError(null)
    } catch (e) {
      if (mounted.current && !opts.quiet) {
        setError((e as Error).message)
      }
    } finally {
      if (mounted.current) setLoading(false)
    }
  }, [])

  /* Initial load, then a quiet poll so the strip stays live without re-rendering
     every card in the tree. */
  useEffect(() => {
    load()
    const id = setInterval(() => load({ quiet: true }), VITAL_POLL_MS)
    return () => clearInterval(id)
  }, [load])

  useEffect(() => {
    api.presets().then((r) => mounted.current && setPresets(r.presets)).catch(() => {})
    api.gameProfiles().then((r) => mounted.current && setGames(r.profiles)).catch(() => {})
  }, [])

  const runPreset = useCallback(async (id: string) => {
    if (busy) return
    setBusy(id)
    setNotice(null)
    onOptimizingChange(true)
    try {
      const r = await api.optimizeQuick(id)
      if (!mounted.current) return
      setRun(r)
      setNotice(
        r.succeeded === r.total
          ? { tone: 'ok', text: `${r.name} complete — ${r.succeeded}/${r.total} steps applied.` }
          : { tone: 'warn', text: `${r.name} finished with ${r.total - r.succeeded} step(s) skipped. See details below.` },
      )
      await load({ quiet: true })
    } catch (e) {
      if (mounted.current) setNotice({ tone: 'error', text: `Run failed: ${(e as Error).message}` })
    } finally {
      if (mounted.current) setBusy(null)
      onOptimizingChange(false)
    }
  }, [busy, load, onOptimizingChange])

  const applyProfile = useCallback(async (gameId: string, gameName: string) => {
    if (busy) return
    setBusy(`game:${gameId}`)
    onOptimizingChange(true)
    try {
      const r = await api.applyGameProfile(gameId)
      const okCount = r.results.filter((x) => x.success).length
      if (mounted.current) {
        setNotice(
          okCount === r.results.length
            ? { tone: 'ok', text: `${gameName} profile applied — ${okCount}/${r.results.length} steps.` }
            : { tone: 'warn', text: `${gameName} profile applied with ${r.results.length - okCount} failure(s).` },
        )
      }
    } catch (e) {
      if (mounted.current) setNotice({ tone: 'error', text: `Profile failed: ${(e as Error).message}` })
    } finally {
      if (mounted.current) setBusy(null)
      onOptimizingChange(false)
    }
  }, [busy, onOptimizingChange])

  const measurePing = useCallback(async () => {
    setPinging(true)
    try {
      const r = await api.speedTestPing('1.1.1.1', 4)
      if (!mounted.current) return
      if (r.error || !r.avg_ms || !r.samples) {
        setPing(null)
        setNotice({ tone: 'warn', text: `Ping test failed${r.error ? `: ${r.error}` : ' — no replies from 1.1.1.1'}.` })
      } else {
        setPing(Math.round(r.avg_ms))
      }
    } catch {
      if (mounted.current) setNotice({ tone: 'warn', text: 'Ping test could not reach 1.1.1.1.' })
    } finally {
      if (mounted.current) setPinging(false)
    }
  }, [])

  const shownGames = useMemo(() => {
    const pinned = games.filter((g) => library.isGameFavorite(g.id))
    const detected = data?.detected_game
      ? games.filter((g) => g.id === data.detected_game?.id)
      : []
    const rest = games.filter((g) => !library.isGameFavorite(g.id) && g.id !== detected[0]?.id)
    return [...pinned, ...detected, ...rest].slice(0, MAX_SHOWN_GAMES)
  }, [games, library, data?.detected_game])

  if (loading) return <OverviewSkeleton />

  if (error && !data) {
    return (
      <div className="max-w-[720px] animate-rise">
        <Card>
          <div className="flex items-start gap-3">
            <CircleAlert size={18} className="text-red shrink-0 mt-0.5" />
            <div>
              <h1 className="text-[15px] font-medium">Could not reach the Optinix service</h1>
              <p className="text-[12.5px] text-text-secondary mt-1">{error}</p>
              <p className="text-[12px] text-text-tertiary mt-2">
                The backend runs on 127.0.0.1:5420. Restart the app if this persists.
              </p>
            </div>
          </div>
        </Card>
      </div>
    )
  }

  if (!data) return null

  const v = data.vitals
  const status = deriveStatus(data)
  const topActions = data.actions.filter((a) => a.severity !== 'ok').slice(0, 5)

  return (
    <div className="page space-y-4 animate-rise pb-4">
      {notice && <NoticeBar notice={notice} onDismiss={() => setNotice(null)} />}

      {/* 1. Status + 2. Primary action ------------------------------------- */}
      <Card className="overflow-hidden">
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_auto]">
          <div className="p-5 min-w-0">
            <div className="flex items-start gap-4">
              <HealthRing score={data.health.overall} label={healthLabel(data.health.overall)} />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h1 className="page-title">{status.headline}</h1>
                  <StatusPill tone={status.tone}>{status.label}</StatusPill>
                </div>
                <p className="page-subtitle mt-1.5 max-w-[60ch]">{status.detail}</p>

                {data.detected_game ? (
                  <div className="mt-3.5 flex flex-wrap items-center gap-2.5 rounded-[10px] border border-accent-line bg-accent-dim/50 px-3 py-2">
                    <Gamepad2 size={14} className="text-accent-ink shrink-0" />
                    <span className="text-[12.5px] font-medium">{data.detected_game.name}</span>
                    <span className="text-[11.5px] text-text-tertiary hidden sm:inline">
                      {data.detected_game.description}
                    </span>
                    <button
                      onClick={() => applyProfile(data.detected_game!.id, data.detected_game!.name)}
                      disabled={!!busy}
                      className="ml-auto flex items-center gap-1.5 h-7 px-2.5 rounded-lg bg-accent text-surface-0 text-[11.5px] font-medium hover:bg-accent-hover disabled:opacity-50 transition-colors duration-150"
                    >
                      {busy === `game:${data.detected_game.id}`
                        ? <Loader2 size={11} className="animate-spin" />
                        : <Play size={11} fill="currentColor" />}
                      Apply profile
                    </button>
                  </div>
                ) : (
                  <div className="mt-3.5 flex items-center gap-2 text-[12px] text-text-tertiary">
                    <Gamepad2 size={13} className="shrink-0" />
                    No supported game detected. Start one and Optinix will apply its profile.
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Primary action */}
          <div className="p-5 lg:border-l border-border lg:w-[300px] shrink-0 bg-surface-1/50">
            <p className="eyebrow mb-1.5">Primary action</p>
            <h2 className="text-[14px] font-medium mb-1">Boost this PC</h2>
            <p className="text-[11.5px] text-text-tertiary leading-[1.5] mb-3">
              Clears temp and cache files, tunes the network stack, disables startup
              delay and trims working sets. Safe to repeat; nothing is removed.
            </p>
            <button
              onClick={() => runPreset('balanced')}
              disabled={!!busy}
              className={cn(
                'w-full h-10 rounded-[10px] flex items-center justify-center gap-2',
                'text-[13px] font-medium transition-all duration-200',
                'disabled:cursor-not-allowed',
                busy
                  ? 'bg-surface-3 text-text-tertiary'
                  : 'bg-accent text-surface-0 hover:bg-accent-hover active:scale-[0.985]',
              )}
            >
              {busy
                ? <><Loader2 size={14} className="animate-spin" /> Optimizing…</>
                : <><Zap size={14} fill="currentColor" /> Optimize now</>}
            </button>
            <div className="mt-2.5 flex items-center justify-between text-[11px] text-text-tertiary">
              <span>{run ? `Last run ${formatDuration(run.steps.reduce((a, s) => a + s.duration_ms, 0))}` : 'No run yet'}</span>
              <button
                onClick={() => onNavigate('oneclick')}
                className="flex items-center gap-1 h-6 px-1 -ml-1 rounded-md hover:text-text-secondary hover:bg-surface-2 transition-colors"
              >
                Full pass <ChevronRight size={11} />
              </button>
            </div>
          </div>
        </div>

        {/* Run progress */}
        {busy && (
          <div className="h-0.5 bg-surface-3 overflow-hidden">
            <div className="h-full w-1/3 bg-accent animate-sweep" />
          </div>
        )}
      </Card>

      {/* 3. Live strip ------------------------------------------------------ */}
      <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-2.5">
        <VitalCard
          icon={Cpu} label="CPU" value={`${Math.round(v.cpu_percent)}%`}
          sub={`${v.cpu_cores}C / ${v.cpu_threads}T`} ratio={v.cpu_percent / 100}
        />
        <VitalCard
          icon={Monitor} label="GPU"
          value={v.gpu.usage == null ? '—' : `${Math.round(v.gpu.usage)}%`}
          sub={v.gpu.name === 'N/A' ? 'Not detected' : shortenGpu(v.gpu.name)}
          ratio={v.gpu.usage == null ? null : v.gpu.usage / 100}
        />
        <VitalCard
          icon={MemoryStick} label="Memory"
          value={`${Math.round(v.ram_percent)}%`}
          sub={`${v.ram_used_gb} / ${v.ram_total_gb} GB`}
          ratio={v.ram_percent / 100}
        />
        <VitalCard
          icon={Thermometer} label="Temperature"
          value={v.gpu.temperature != null ? `${Math.round(v.gpu.temperature)}°C` : v.cpu_temp != null ? `${Math.round(v.cpu_temp)}°C` : '—'}
          sub={v.gpu.temperature != null ? 'GPU' : v.cpu_temp != null ? 'CPU' : 'Unavailable'}
          ratio={v.gpu.temperature != null ? v.gpu.temperature / 100 : null}
          warn={v.gpu.temperature != null && v.gpu.temperature >= 85}
        />
        <VitalCard
          icon={Gauge} label="FPS"
          value="—"
          sub="No counter"
          hint="Optinix does not inject into games. Use the in-game counter or a dedicated overlay."
        />
        <button
          onClick={measurePing}
          disabled={pinging}
          title="Measure latency to 1.1.1.1"
          className="surface-card surface-card-interactive p-3 text-left disabled:opacity-70"
        >
          <div className="flex items-center gap-1.5 mb-1.5">
            <Timer size={12} className="text-text-tertiary" />
            <span className="text-[10px] font-semibold uppercase tracking-[0.06em] text-text-tertiary">Ping</span>
            {pinging && <Loader2 size={10} className="ml-auto animate-spin text-accent-ink" />}
          </div>
          <div className="text-[19px] font-semibold tnum leading-none">
            {ping == null ? <span className="text-text-tertiary text-[15px]">Test</span> : `${ping} ms`}
          </div>
          <div className="text-[10.5px] text-text-tertiary mt-1 truncate">
            {ping == null ? 'Tap to measure' : toneForPing(ping)}
          </div>
        </button>
      </div>

      {/* 4. Recommended actions -------------------------------------------- */}
      <Card>
        <div className="flex items-center justify-between px-4 py-3 border-b border-border">
          <div>
            <h2 className="text-[13.5px] font-medium">Recommended actions</h2>
            <p className="text-[11.5px] text-text-tertiary mt-0.5">
              Derived from measured system state, not generic advice.
            </p>
          </div>
          {topActions.length > 0 && (
            <span className="text-[11px] text-text-tertiary tnum">
              {topActions.length} to review
            </span>
          )}
        </div>
        {topActions.length === 0 ? (
          <div className="px-4 py-6 flex items-center gap-2.5">
            <CircleCheck size={16} className="text-green shrink-0" />
            <p className="text-[12.5px] text-text-secondary">
              Nothing needs attention. Memory, storage and power are all in healthy ranges.
            </p>
          </div>
        ) : (
          <ul className="divide-y divide-border">
            {topActions.map((a) => (
              <ActionRow key={a.id} action={a} onNavigate={onNavigate} />
            ))}
          </ul>
        )}
      </Card>

      {/* 5. Games ------------------------------------------------------------ */}
      <Card>
        <div className="flex items-center justify-between px-4 py-3 border-b border-border">
          <div>
            <h2 className="text-[13.5px] font-medium">Your games</h2>
            <p className="text-[11.5px] text-text-tertiary mt-0.5">
              {data.detected_game
                ? `${data.detected_game.name} is running.`
                : 'Pinned games appear here. Star one to keep it on top.'}
            </p>
          </div>
          <button
            onClick={() => onNavigate('game-mode')}
            className="flex items-center gap-1 text-[11.5px] text-text-tertiary hover:text-text transition-colors"
          >
            View all {games.length} <ArrowRight size={12} />
          </button>
        </div>
        {shownGames.length === 0 ? (
          <div className="px-4 py-8 text-center">
            <p className="text-[12.5px] text-text-secondary">No game profiles loaded.</p>
            <p className="text-[11.5px] text-text-tertiary mt-1">
              Profiles come from the bundled library in core/game_profiles.py.
            </p>
          </div>
        ) : (
          <div className="p-3 grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-2">
            {shownGames.map((g) => {
              const running = data.detected_game?.id === g.id
              return (
                <div
                  key={g.id}
                  className={cn(
                    'rounded-[10px] border p-2.5 transition-colors duration-150',
                    running
                      ? 'border-accent-line bg-accent-dim/40'
                      : 'border-border bg-surface-1 hover:border-border-light',
                  )}
                >
                  <div className="flex items-start gap-2.5">
                    <span className="w-7 h-7 rounded-lg bg-surface-3 border border-border flex items-center justify-center shrink-0">
                      <Gamepad2 size={13} className="text-text-secondary" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5">
                        <p className="text-[12.5px] font-medium truncate">{g.name}</p>
                        {running && (
                          <span className="text-[9.5px] font-medium text-accent-ink bg-accent-dim px-1.5 py-px rounded shrink-0">
                            running
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-text-tertiary line-clamp-1 mt-0.5">
                        {g.description}
                      </p>
                    </div>
                    <button
                      onClick={() => library.toggleGameFavorite(g.id)}
                      aria-label={library.isGameFavorite(g.id) ? `Unpin ${g.name}` : `Pin ${g.name}`}
                      className={cn(
                        'p-0.5 rounded transition-colors shrink-0',
                        library.isGameFavorite(g.id)
                          ? 'text-accent-ink'
                          : 'text-text-tertiary/40 hover:text-text-secondary',
                      )}
                    >
                      <Star size={12} fill={library.isGameFavorite(g.id) ? 'currentColor' : 'none'} />
                    </button>
                  </div>
                  <button
                    onClick={() => applyProfile(g.id, g.name)}
                    disabled={!!busy}
                    className="mt-2 w-full h-7 rounded-lg border border-border bg-surface-2 text-[11.5px] text-text-secondary hover:text-text hover:border-border-light disabled:opacity-50 transition-colors duration-150 flex items-center justify-center gap-1.5"
                  >
                    {busy === `game:${g.id}`
                      ? <Loader2 size={11} className="animate-spin" />
                      : <Play size={10} fill="currentColor" />}
                    Apply profile
                  </button>
                </div>
              )
            })}
          </div>
        )}
      </Card>

      {/* 6. Presets + results ---------------------------------------------- */}
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_400px] gap-4 items-start">
        <Card>
          <div className="flex items-center justify-between px-4 py-3 border-b border-border">
            <div>
              <h2 className="text-[13.5px] font-medium">Preset modes</h2>
              <p className="text-[11.5px] text-text-tertiary mt-0.5">
                Each preset lists exactly what it changes before you run it.
              </p>
            </div>
          </div>
          <div className="p-3 grid grid-cols-1 sm:grid-cols-2 gap-2">
            {presets.map((p) => (
              <PresetRow
                key={p.id}
                preset={p}
                busy={busy === p.id}
                disabled={!!busy}
                onRun={() => runPreset(p.id)}
              />
            ))}
            {presets.length === 0 && (
              <p className="col-span-full px-1 py-4 text-[12px] text-text-tertiary">
                Preset list unavailable.
              </p>
            )}
          </div>
        </Card>

        <Card>
          <div className="flex items-center justify-between px-4 py-3 border-b border-border">
            <h2 className="text-[13.5px] font-medium">Results</h2>
            {run && (
              <button
                onClick={() => { setRun(null); setNotice(null) }}
                className="flex items-center gap-1 text-[11px] text-text-tertiary hover:text-text-secondary transition-colors"
              >
                <X size={11} /> Clear
              </button>
            )}
          </div>
          <ResultsPanel run={run} last={data.last_optimization} />
        </Card>
      </div>
    </div>
  )
}

/* ============================================================ sub-components */

function Card({ children, className }: { children: React.ReactNode; className?: string }) {
  return <section className={cn('surface-card', className)}>{children}</section>
}

function NoticeBar({ notice, onDismiss }: {
  notice: { tone: 'ok' | 'warn' | 'error'; text: string }
  onDismiss: () => void
}) {
  const Icon = notice.tone === 'ok' ? CircleCheck : notice.tone === 'warn' ? TriangleAlert : CircleAlert
  const tone = notice.tone === 'ok' ? 'text-green' : notice.tone === 'warn' ? 'text-yellow' : 'text-red'
  const bg = notice.tone === 'ok' ? 'bg-green-dim/50' : notice.tone === 'warn' ? 'bg-yellow-dim/50' : 'bg-red-dim/50'
  return (
    <div className={cn('flex items-center gap-2.5 px-4 py-2.5 rounded-[10px] border animate-fade-in', bg, 'border-border')}>
      <Icon size={15} className={cn('shrink-0', tone)} />
      <p className="text-[12.5px] flex-1">{notice.text}</p>
      <button onClick={onDismiss} aria-label="Dismiss" className="text-text-tertiary hover:text-text transition-colors">
        <X size={13} />
      </button>
    </div>
  )
}

function HealthRing({ score, label }: { score: number; label: string }) {
  const clamped = Math.max(0, Math.min(100, score || 0))
  const r = 26
  const c = 2 * Math.PI * r
  const tone = clamped >= 80 ? 'text-green' : clamped >= 60 ? 'text-yellow' : 'text-red'
  const stroke = clamped >= 80 ? 'var(--color-green)' : clamped >= 60 ? 'var(--color-yellow)' : 'var(--color-red)'
  return (
    <div className="shrink-0 w-[62px] text-center">
      <div className="relative w-[62px] h-[62px]">
        <svg viewBox="0 0 62 62" className="w-full h-full -rotate-90">
          <circle cx="31" cy="31" r={r} fill="none" stroke="var(--color-surface-4)" strokeWidth="5" />
          <circle
            cx="31" cy="31" r={r} fill="none" stroke={stroke} strokeWidth="5" strokeLinecap="round"
            strokeDasharray={c} strokeDashoffset={c * (1 - clamped / 100)}
            style={{ transition: 'stroke-dashoffset 500ms var(--ease-out-quart)' }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={cn('text-[15px] font-semibold tnum leading-none', tone)}>{Math.round(clamped)}</span>
          <span className="text-[8.5px] uppercase tracking-[0.06em] text-text-tertiary mt-0.5">score</span>
        </div>
      </div>
      <p className={cn('text-[10.5px] mt-1.5', tone)}>{label}</p>
    </div>
  )
}

function StatusPill({ tone, children }: { tone: 'ok' | 'warn' | 'bad' | 'idle'; children: React.ReactNode }) {
  const map = {
    ok: 'text-green bg-green-dim border-green/25',
    warn: 'text-yellow bg-yellow-dim border-yellow/25',
    bad: 'text-red bg-red-dim border-red/25',
    idle: 'text-text-tertiary bg-surface-3 border-border',
  }
  return (
    <span className={cn('text-[10.5px] font-medium px-2 py-0.5 rounded-md border', map[tone])}>
      {children}
    </span>
  )
}

function VitalCard({ icon: Icon, label, value, sub, ratio, warn, hint }: {
  icon: IconComponent
  label: string
  value: string
  sub: string
  ratio?: number | null
  warn?: boolean
  hint?: string
}) {
  return (
    <div className="surface-card p-3" title={hint}>
      <div className="flex items-center gap-1.5 mb-1.5">
        <Icon size={12} className="text-text-tertiary shrink-0" />
        <span className="text-[10px] font-semibold uppercase tracking-[0.06em] text-text-tertiary truncate">
          {label}
        </span>
      </div>
      <div className={cn('text-[19px] font-semibold tnum leading-none', warn && 'text-red')}>
        {value}
      </div>
      <div className="text-[10.5px] text-text-tertiary mt-1 truncate">{sub}</div>
      {ratio != null && (
        <div className="mt-2 h-[3px] rounded-full bg-surface-4 overflow-hidden">
          <div
            className={cn(
              'h-full rounded-full transition-[width] duration-500 ease-out',
              ratio > 0.9 ? 'bg-red' : ratio > 0.75 ? 'bg-yellow' : 'bg-accent',
            )}
            style={{ width: `${Math.min(100, Math.max(2, ratio * 100))}%` }}
          />
        </div>
      )}
    </div>
  )
}

function ActionRow({ action, onNavigate }: { action: OverviewAction; onNavigate: (id: string) => void }) {
  const Icon = action.severity === 'high' ? CircleAlert : action.severity === 'medium' ? TriangleAlert : Info
  const tone = action.severity === 'high' ? 'text-red' : action.severity === 'medium' ? 'text-yellow' : 'text-text-tertiary'
  return (
    <li>
      <button
        onClick={() => onNavigate(action.page)}
        className="w-full flex items-start gap-3 px-4 py-3 text-left hover:bg-surface-1 transition-colors duration-150 group"
      >
        <Icon size={15} className={cn('shrink-0 mt-0.5', tone)} />
        <span className="min-w-0 flex-1">
          <span className="flex items-center gap-2">
            <span className="text-[12.5px] font-medium">{action.title}</span>
            {action.action && (
              <span className="text-[10px] text-text-tertiary bg-surface-3 px-1.5 py-px rounded">
                fix available
              </span>
            )}
          </span>
          <span className="block text-[11.5px] text-text-tertiary mt-0.5 leading-[1.45]">
            {action.detail}
          </span>
        </span>
        <ChevronRight size={14} className="text-text-tertiary opacity-0 group-hover:opacity-100 shrink-0 mt-0.5 transition-opacity duration-150" />
      </button>
    </li>
  )
}

function PresetRow({ preset, busy, disabled, onRun }: {
  preset: PresetMode
  busy: boolean
  disabled: boolean
  onRun: () => void
}) {
  const [open, setOpen] = useState(false)
  return (
    <div className="rounded-[10px] border border-border bg-surface-1 overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="w-full flex items-center gap-2.5 px-3 py-2.5 text-left hover:bg-surface-2 transition-colors duration-150"
      >
        <div className="min-w-0 flex-1">
          <p className="text-[12.5px] font-medium">{preset.name}</p>
          <p className="text-[11px] text-text-tertiary mt-0.5 line-clamp-1">{preset.summary}</p>
        </div>
        <ChevronRight
          size={13}
          className={cn('text-text-tertiary shrink-0 transition-transform duration-200', open && 'rotate-90')}
        />
      </button>
      {open && (
        <div className="px-3 pb-3 border-t border-border pt-2.5 animate-fade-in">
          <p className="eyebrow mb-1.5">This will change</p>
          <ul className="space-y-1 mb-3">
            {preset.detail.map((d) => (
              <li key={d} className="flex items-start gap-1.5 text-[11.5px] text-text-secondary">
                <Check size={11} className="text-text-tertiary shrink-0 mt-0.5" />
                <span>{d}</span>
              </li>
            ))}
          </ul>
          <button
            onClick={onRun}
            disabled={disabled}
            className="w-full h-8 rounded-lg bg-surface-3 text-[12px] font-medium text-text hover:bg-surface-4 disabled:opacity-50 transition-colors duration-150 flex items-center justify-center gap-1.5"
          >
            {busy ? <Loader2 size={12} className="animate-spin" /> : <Zap size={12} />}
            {busy ? 'Running…' : `Apply ${preset.name}`}
          </button>
        </div>
      )}
    </div>
  )
}

function ResultsPanel({ run, last }: {
  run: OptimizeRun | null
  last: Overview['last_optimization']
}) {
  if (run) {
    return (
      <div className="p-4 space-y-3 animate-fade-in">
        <div className="flex items-center gap-2">
          <span className="text-[12.5px] font-medium">{run.name}</span>
          <span className="text-[11px] text-text-tertiary tnum">
            {run.succeeded}/{run.total} steps
          </span>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <Delta
            label="Memory in use"
            before={`${run.before.ram_used_gb} GB`}
            after={`${run.after.ram_used_gb} GB`}
            delta={run.deltas.ram_used_gb}
            unit=" GB"
            lowerIsBetter
          />
          <Delta
            label="Memory available"
            before={`${run.before.ram_available_gb} GB`}
            after={`${run.after.ram_available_gb} GB`}
            delta={run.deltas.ram_available_gb}
            unit=" GB"
          />
          <Delta
            label="Processes"
            before={String(run.before.process_count)}
            after={String(run.after.process_count)}
            delta={run.deltas.process_count}
          />
          <Delta
            label="Disk free"
            before={`${run.before.disk_free_gb} GB`}
            after={`${run.after.disk_free_gb} GB`}
            delta={run.deltas.disk_free_gb}
            unit=" GB"
          />
        </div>
        <details className="pt-1">
          <summary className="text-[11.5px] text-text-tertiary cursor-pointer hover:text-text transition-colors select-none">
            Step detail
          </summary>
          <ul className="mt-2 space-y-1">
            {run.steps.map((s) => (
              <li key={s.id} className="flex items-start gap-2 text-[11px]">
                {s.success
                  ? <Check size={11} className="text-green shrink-0 mt-0.5" />
                  : <AlertTriangle size={11} className="text-yellow shrink-0 mt-0.5" />}
                <span className="min-w-0 flex-1">
                  <span className="text-text-secondary">{s.label}</span>
                  {s.message && (
                    <span className="block text-text-tertiary truncate" title={s.message}>{s.message}</span>
                  )}
                </span>
                <span className="text-text-tertiary tnum shrink-0">{formatDuration(s.duration_ms)}</span>
              </li>
            ))}
          </ul>
        </details>
        {!run.is_admin && (
          <p className="flex items-start gap-1.5 text-[11px] text-yellow bg-yellow-dim/50 rounded-lg px-2.5 py-2">
            <ShieldAlert size={12} className="shrink-0 mt-0.5" />
            Ran without Administrator rights, so privileged steps were skipped.
          </p>
        )}
      </div>
    )
  }

  const cmp = last?.benchmark_comparison
  if (last && cmp && Object.keys(cmp).length) {
    return (
      <div className="p-4 space-y-3 animate-fade-in">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[12.5px] font-medium">{last.name}</span>
          <span className="text-[11px] text-text-tertiary">
            {formatRelative(last.timestamp) ?? 'unknown time'}
          </span>
        </div>
        <ul className="space-y-1.5">
          {Object.entries(cmp).map(([key, c]) => (
            <li key={key} className="flex items-center gap-2 text-[11.5px]">
              <span className="text-text-tertiary capitalize w-[86px] shrink-0">{key}</span>
              <span className="flex-1 h-[3px] rounded-full bg-surface-4 overflow-hidden">
                <span
                  className={cn('block h-full rounded-full', c.improved ? 'bg-green' : 'bg-red')}
                  style={{ width: `${Math.min(100, Math.abs(c.percent))}%` }}
                />
              </span>
              <span className={cn('tnum w-[62px] text-right shrink-0', c.improved ? 'text-green' : 'text-red')}>
                {c.percent > 0 ? '+' : ''}{c.percent.toFixed(1)}%
              </span>
            </li>
          ))}
        </ul>
        <p className="text-[11px] text-text-tertiary">
          {last.success_count}/{last.total_count} steps applied in{' '}
          {formatDuration(last.duration_ms)}. Run a preset to get fresh numbers.
        </p>
      </div>
    )
  }

  return (
    <div className="px-4 py-10 text-center">
      <Activity size={16} className="mx-auto text-text-tertiary" />
      <p className="text-[12.5px] text-text-secondary mt-2.5">Not enough data yet</p>
      <p className="text-[11.5px] text-text-tertiary mt-1 max-w-[34ch] mx-auto leading-[1.5]">
        Run a preset to capture real before and after measurements. Nothing is estimated.
      </p>
    </div>
  )
}

function Delta({ label, before, after, delta, unit = '', lowerIsBetter }: {
  label: string
  before: string
  after: string
  delta: number
  unit?: string
  lowerIsBetter?: boolean
}) {
  const rounded = Math.round(delta * 100) / 100
  const improved = lowerIsBetter ? rounded < 0 : rounded > 0
  const neutral = rounded === 0
  return (
    <div className="rounded-lg border border-border bg-surface-1 p-2.5">
      <p className="text-[10.5px] text-text-tertiary truncate">{label}</p>
      <p className="text-[12px] text-text-secondary tnum mt-1">
        {before} <span className="text-text-tertiary">→</span> {after}
      </p>
      <p className={cn(
        'text-[11px] tnum mt-0.5',
        neutral ? 'text-text-tertiary' : improved ? 'text-green' : 'text-text-tertiary',
      )}>
        {neutral ? 'no change' : `${rounded > 0 ? '+' : ''}${rounded}${unit}`}
      </p>
    </div>
  )
}

function OverviewSkeleton() {
  return (
    <div className="page space-y-4 animate-fade-in">
      <div className="surface-card h-[188px] animate-pulse-subtle" />
      <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-2.5">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="surface-card h-[86px] animate-pulse-subtle" />
        ))}
      </div>
      <div className="surface-card h-[196px] animate-pulse-subtle" />
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_400px] gap-4">
        <div className="surface-card h-[240px] animate-pulse-subtle" />
        <div className="surface-card h-[240px] animate-pulse-subtle" />
      </div>
    </div>
  )
}

/* =================================================================== helpers */

interface DerivedStatus {
  headline: string
  detail: string
  label: string
  tone: 'ok' | 'warn' | 'bad' | 'idle'
}

function deriveStatus(d: Overview): DerivedStatus {
  const high = d.actions.filter((a) => a.severity === 'high').length
  const last = d.last_optimization
  const age = last ? Date.now() - Date.parse(last.timestamp || '') : null
  const stale = age == null || Number.isNaN(age) || age > 3 * 86400_000

  if (high > 0) {
    return {
      headline: 'Needs attention',
      detail: `${high} issue${high === 1 ? '' : 's'} found. Start with the recommendation below — each one is measurable.`,
      label: `${high} critical`,
      tone: 'bad',
    }
  }
  if (stale) {
    return {
      headline: last ? 'Tune-up recommended' : 'Not optimized yet',
      detail: last
        ? `Last run was ${formatRelative(last.timestamp) ?? 'a while ago'}. A fresh pass usually takes under a minute.`
        : 'Run your first optimization to capture a baseline. Every future run then shows a real before and after.',
      label: last ? 'stale' : 'new',
      tone: 'warn',
    }
  }
  return {
    headline: 'Looking good',
    detail: `Optimized ${formatRelative(last?.timestamp) ?? 'recently'}. No critical issues detected right now.`,
    label: 'optimized',
    tone: 'ok',
  }
}

function healthLabel(score: number): string {
  if (score >= 85) return 'Excellent'
  if (score >= 70) return 'Good'
  if (score >= 50) return 'Fair'
  if (score > 0) return 'Poor'
  return 'Scoring'
}

function shortenGpu(name: string): string {
  return name.replace(/NVIDIA GeForce\s*/i, '').replace(/\s*\(.*\)\s*/g, '').slice(0, 22)
}

function toneForPing(ms: number): string {
  if (ms < 30) return 'Excellent for gaming'
  if (ms < 60) return 'Good for most regions'
  if (ms < 100) return 'Playable, high ping'
  return 'High — check connection'
}
