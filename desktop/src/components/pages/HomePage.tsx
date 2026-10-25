import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Zap, Play, Loader2, Gamepad2, ChevronRight, Cpu, Monitor, MemoryStick,
  HardDrive, Thermometer, Activity, CircleAlert, CircleCheck, ArrowRight,
  TriangleAlert, Info,
} from 'lucide-react'
import { cn, formatDuration, formatRelative } from '../../lib/utils'
import { useMountedRef } from '../../hooks/useMountedRef'
import { api } from '../../lib/api'
import { Sparkline } from '../ui/charts/Sparkline'
import { BarPair } from '../ui/charts/BarPair'
import { RadialMeter } from '../ui/charts/RadialMeter'
import { StreamArea } from '../ui/charts/StreamArea'
import { RadarScores } from '../ui/charts/RadarScores'
import { TiltCard } from '../ui/TiltCard'
import { HeroExperience } from '../three/HeroExperience'
import type { Overview, PresetMode, GameProfileSummary, TimelineEvent } from '../../types'
import type { Library } from '../../hooks/useLibrary'
import type { IconComponent } from '../../nav'

interface HomePageProps {
  onNavigate: (id: string) => void
  library?: Library
  onOptimizingChange?: (busy: boolean) => void
}

const POLL_MS = 4000
const HISTORY_MAX = 30
const MAX_ACTIONS = 4

type Notice = { tone: 'ok' | 'warn' | 'error'; text: string }

/* Rolling client-side history: every point is a real sample from a completed
   overview poll. Nothing here is generated, interpolated or guessed. */
interface SampleHistory {
  cpu: number[]
  ram: number[]
  disk: number[]
  gpu: number[]
  t: number[]
}

const EMPTY_HISTORY: SampleHistory = { cpu: [], ram: [], disk: [], gpu: [], t: [] }

function pushSample(h: SampleHistory, o: Overview): SampleHistory {
  const v = o.vitals
  const next = {
    cpu: [...h.cpu, v.cpu_percent],
    ram: [...h.ram, v.ram_percent],
    disk: [...h.disk, v.disk_percent],
    gpu: [...h.gpu, v.gpu.usage ?? Number.NaN],
    t: [...h.t, Date.now()],
  }
  for (const key of Object.keys(next) as (keyof SampleHistory)[]) {
    if (next[key].length > HISTORY_MAX) next[key] = next[key].slice(-HISTORY_MAX)
  }
  return next
}

export function HomePage({ onNavigate, library, onOptimizingChange }: HomePageProps) {
  const [data, setData] = useState<Overview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [history, setHistory] = useState<SampleHistory>(EMPTY_HISTORY)

  const [presets, setPresets] = useState<PresetMode[]>([])
  const [busy, setBusy] = useState<string | null>(null)
  const [notice, setNotice] = useState<Notice | null>(null)
  const [games, setGames] = useState<GameProfileSummary[]>([])
  const [recent, setRecent] = useState<TimelineEvent[]>([])
  const [ping, setPing] = useState<number | null>(null)
  const [pinging, setPinging] = useState(false)

  const mounted = useMountedRef()

  const load = useCallback(async (opts: { quiet?: boolean } = {}) => {
    try {
      const d = await api.overview()
      if (!mounted.current) return
      setData((prev) => {
        setHistory((h) => (prev ? pushSample(h, d) : h))
        return d
      })
      setError(null)
    } catch (e) {
      if (mounted.current && !opts.quiet) setError((e as Error).message)
    } finally {
      if (mounted.current) setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
    const id = setInterval(() => {
      if (!document.hidden) load({ quiet: true })
    }, POLL_MS)
    return () => clearInterval(id)
  }, [load])

  useEffect(() => {
    api.presets().then((r) => mounted.current && setPresets(r.presets)).catch(() => {})
    api.gameProfiles().then((r) => mounted.current && setGames(r.profiles)).catch(() => {})
    api.timelineEvents(6).then((r) => mounted.current && setRecent(r.events ?? [])).catch(() => {})
  }, [])

  const runPreset = useCallback(async (presetId: string) => {
    if (busy) return
    setBusy(presetId)
    setNotice(null)
    onOptimizingChange?.(true)
    try {
      const r = await api.optimizeQuick(presetId)
      if (!mounted.current) return
      setNotice(
        r.succeeded === r.total
          ? { tone: 'ok', text: `${r.name} complete — ${r.succeeded}/${r.total} steps applied.` }
          : { tone: 'warn', text: `${r.name} finished with ${r.total - r.succeeded} step(s) skipped. Nothing was applied for those.` },
      )
      await load({ quiet: true })
      api.timelineEvents(6).then((e) => mounted.current && setRecent(e.events ?? [])).catch(() => {})
    } catch (e) {
      if (mounted.current) setNotice({ tone: 'error', text: `Run failed: ${(e as Error).message}` })
    } finally {
      if (mounted.current) setBusy(null)
      onOptimizingChange?.(false)
    }
  }, [busy, load, onOptimizingChange])

  const applyGameProfile = useCallback(async (gameId: string, gameName: string) => {
    if (busy) return
    setBusy(`game:${gameId}`)
    onOptimizingChange?.(true)
    try {
      const r = await api.applyGameProfile(gameId)
      const ok = r.results.filter((x) => x.success).length
      if (mounted.current) {
        setNotice(
          ok === r.results.length
            ? { tone: 'ok', text: `${gameName} profile applied — ${ok}/${r.results.length} steps.` }
            : { tone: 'warn', text: `${gameName} profile applied with ${r.results.length - ok} failure(s).` },
        )
      }
    } catch (e) {
      if (mounted.current) setNotice({ tone: 'error', text: `Profile failed: ${(e as Error).message}` })
    } finally {
      if (mounted.current) setBusy(null)
      onOptimizingChange?.(false)
    }
  }, [busy, onOptimizingChange])

  const measurePing = useCallback(async () => {
    setPinging(true)
    try {
      const r = await api.speedTestPing('1.1.1.1', 4)
      if (!mounted.current) return
      if (r.error || r.avg_ms == null || !r.samples) {
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

  const status = useMemo(() => deriveStatus(data), [data])

  /* Health dimensions for the radar: only what the backend actually scored.
     `v.label` is the band name for the score ("Excellent", "Moderate"), not
     the dimension, so the axis label comes from the key instead. */
  const healthShape = useMemo(
    () => Object.entries(data?.health.scores ?? {})
      .sort(([a], [b]) => rankScoreKey(a) - rankScoreKey(b))
      .slice(0, 6)
      .map(([key, v]) => ({
        key,
        label: HEALTH_LABELS[key] ?? humanize(key),
        value: v.score,
      })),
    [data],
  )

  if (loading && !data) return <HomeSkeleton />

  if (error && !data) {
    return (
      <div className="max-w-[720px] animate-rise">
        <div className="surface-card p-5 flex items-start gap-3">
          <CircleAlert size={18} className="text-red shrink-0 mt-0.5" />
          <div>
            <h1 className="text-[15px] font-medium">Could not reach the Optinix service</h1>
            <p className="text-[12.5px] text-text-secondary mt-1">{error}</p>
            <p className="text-[12px] text-text-tertiary mt-2">
              The backend runs on 127.0.0.1:5420. Restart the app if this persists.
            </p>
            <button
              onClick={() => { setLoading(true); load() }}
              className="mt-3 h-8 px-3 rounded-lg bg-surface-3 hover:bg-surface-4 text-[12.5px] text-text transition-colors"
            >
              Try again
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (!data) return null

  const v = data.vitals
  const topActions = data.actions.filter((a) => a.severity !== 'ok').slice(0, MAX_ACTIONS)
  const primaryPreset = presets[0]
  const detectedGame = data.detected_game
  const pinnedGames = library
    ? games.filter((g) => library!.isGameFavorite(g.id)).slice(0, 3)
    : []

  return (
    <div className="page space-y-4 stagger-rise pb-4">
      {notice && <NoticeBar notice={notice} onDismiss={() => setNotice(null)} />}

      {/* Status band: the opening scene of the product. A lit stage, the
          live health dial, the machine's own headline and the primary
          action — with the 3D tower as the focal object rather than a
          decorative badge. The canvas is pointer-transparent, so it can
          never sit between the user and a control. */}
      <section className="band-hero relative isolate overflow-hidden">
        <div aria-hidden className="pointer-events-none absolute inset-0 z-0 overflow-hidden rounded-[inherit]">
          <span className="hero-key" />
          <span className="hero-key hero-key-violet" />
          <span className="hero-shaft" />
          <span className="hero-baseline" />
          <span className="hero-grain absolute inset-0" />
        </div>

        {/* Three columns on xl+: copy, 3D stage, primary action. Below xl
            the stage drops out and the band keeps two columns. */}
        <div className="relative z-10 grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_280px] min-[1420px]:grid-cols-[minmax(0,1fr)_400px_292px]">
          <div className="min-w-0 p-6 xl:py-7 flex flex-col justify-center">
            <div className="flex flex-wrap items-center gap-2.5">
              <span className="eyebrow text-accent-ink/85">System status</span>
              <span className="h-3 w-px bg-border" />
              <span className={cn(
                'inline-flex items-center gap-1.5 text-[11px] font-medium px-2 py-0.5 rounded-full',
                status.tone === 'ok' && 'text-green bg-green-dim',
                status.tone === 'warn' && 'text-yellow bg-yellow-dim',
                status.tone === 'bad' && 'text-red bg-red-dim',
              )}>
                <span className="w-1.5 h-1.5 rounded-full bg-current" />
                {status.label}
              </span>
            </div>

            <h1 className="mt-3 font-display text-[27px] font-bold leading-[1.1] tracking-[-0.038em] max-w-[30ch]">
              {status.headline}
            </h1>
            <p className="page-subtitle mt-2 max-w-[52ch]">{status.detail}</p>

            <div className="mt-5 flex items-end gap-4">
              <RadialMeter
                value={data.health.overall}
                label="Health"
                size={104}
                tone={data.health.overall >= 85 ? 'good' : data.health.overall >= 60 ? 'warn' : 'bad'}
              />

              <div className="min-w-0 flex-1 pb-1">
                {detectedGame ? (
                  <div className="hero-game rounded-[12px] border border-accent-line/70 px-3 py-2.5">
                    <div className="flex items-center gap-2">
                      <span className="icon-chip text-accent-ink h-6 w-6 shrink-0">
                        <Gamepad2 size={12} />
                      </span>
                      <span className="min-w-0 flex-1 text-[12px] font-medium leading-tight truncate">
                        {detectedGame.name}
                      </span>
                      <button
                        onClick={() => applyGameProfile(detectedGame.id, detectedGame.name)}
                        disabled={!!busy}
                        className="flex items-center gap-1.5 h-6 px-2 rounded-md bg-accent-dim text-accent-ink text-[10.5px] font-medium hover:bg-accent hover:text-on-accent disabled:opacity-50 transition-colors duration-150 shrink-0"
                      >
                        {busy === `game:${detectedGame.id}`
                          ? <Loader2 size={10} className="animate-spin" />
                          : <Play size={10} fill="currentColor" />}
                        Apply
                      </button>
                    </div>
                    <p className="mt-1 ps-8 text-[10.5px] text-text-tertiary truncate">
                      {detectedGame.description}
                    </p>
                  </div>
                ) : (
                  <div className="flex items-center gap-2 text-[12px] text-text-tertiary">
                    <Gamepad2 size={13} className="shrink-0" />
                    No supported game detected. Start one and Optinix will offer its profile.
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* The signature 3D object: a lit tower. Hidden below xl so narrow
              windows keep a two-column band. */}
          <div className="relative hidden min-[1420px]:flex items-center justify-center min-h-[340px]">
            <span aria-hidden className="hero-pool" />
            {/* Load drives the scene: a busy machine burns brighter and its
                intake fan spins faster. */}
            <HeroExperience
              className="relative w-[400px] h-[336px]"
              level={Math.min(1, Math.max(0.08, Math.max(v.cpu_percent, v.gpu.usage ?? 0) / 100))}
            />
          </div>

          {/* Primary action: the one filled control on the page. */}
          <div className="hero-action relative shrink-0 border-t lg:border-t-0 lg:border-l border-border p-5 xl:p-6">
            <p className="eyebrow mb-2">Primary action</p>
            <h2 className="font-display text-[15px] font-semibold mb-1">
              {primaryPreset ? primaryPreset.name : 'Boost this PC'}
            </h2>
            <p className="text-[11.5px] text-text-tertiary leading-[1.55] mb-4">
              {primaryPreset
                ? primaryPreset.summary
                : 'Clears temp and cache files, tunes the network stack and trims working sets. Safe to repeat.'}
            </p>
            <button
              onClick={() => primaryPreset && runPreset(primaryPreset.id)}
              disabled={!primaryPreset || !!busy}
              className={cn(
                'w-full h-11 rounded-[11px] flex items-center justify-center gap-2',
                'font-display text-[13.5px] font-semibold tracking-[-0.01em]',
                'transition-all duration-200 disabled:cursor-not-allowed',
                busy
                  ? 'bg-surface-3 text-text-tertiary'
                  : 'bg-[image:var(--grad-control)] text-on-accent shadow-glow-accent hover:brightness-110 active:scale-[0.985]',
              )}
            >
              {busy
                ? <><Loader2 size={14} className="animate-spin" /> Optimizing…</>
                : <><Zap size={14} fill="currentColor" /> Optimize now</>}
            </button>

            <dl className="mt-4 space-y-2 text-[11px] border-t border-white/[0.05] pt-3.5">
              <div className="flex items-center justify-between gap-2">
                <dt className="text-text-tertiary">Last run</dt>
                <dd className="text-text-secondary font-medium">
                  {data.last_optimization
                    ? formatRelative(data.last_optimization.timestamp)
                    : 'No run yet'}
                </dd>
              </div>
              <div className="flex items-center justify-between gap-2">
                <dt className="text-text-tertiary">Mode</dt>
                <dd className="text-text-secondary font-medium">Safe &amp; reversible</dd>
              </div>
            </dl>

            <button
              onClick={() => onNavigate('oneclick')}
              className="mt-3 flex items-center gap-1 h-7 px-1 -ml-1 rounded-md text-[11px] text-text-tertiary hover:text-text-secondary transition-colors"
            >
              Full pass <ChevronRight size={11} />
            </button>
          </div>
        </div>
        {busy && (
          <div className="absolute inset-x-0 bottom-0 h-0.5 bg-surface-3 overflow-hidden">
            <div className="h-full w-1/3 bg-accent animate-sweep" />
          </div>
        )}
      </section>

      {/* Live vitals: real samples, accumulating one per poll. */}
      <section aria-label="Live metrics" className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-2.5">
        <VitalCard icon={Cpu} label="CPU" value={`${Math.round(v.cpu_percent)}%`}
          sub={`${v.cpu_cores}C / ${v.cpu_threads}T`} series={history.cpu} invert />
        <VitalCard icon={Monitor} label="GPU"
          value={v.gpu.usage == null ? '—' : `${Math.round(v.gpu.usage)}%`}
          sub={v.gpu.name === 'N/A' ? 'Not detected' : v.gpu.name}
          series={history.gpu} invert
          hint={v.gpu.usage == null ? 'No readable GPU load on this machine. Other GPU tools still work.' : undefined} />
        <VitalCard icon={MemoryStick} label="Memory" value={`${Math.round(v.ram_percent)}%`}
          sub={`${v.ram_used_gb} / ${v.ram_total_gb} GB`} series={history.ram} invert />
        <VitalCard icon={HardDrive} label="Storage" value={`${Math.round(v.disk_percent)}%`}
          sub={`${v.disk_free_gb} GB free`} series={history.disk} invert />
        <VitalCard icon={Thermometer} label="Temp"
          value={v.gpu.temperature != null ? `${Math.round(v.gpu.temperature)}°`
            : v.cpu_temp != null ? `${Math.round(v.cpu_temp)}°` : '—'}
          sub={v.gpu.temperature != null ? 'GPU' : v.cpu_temp != null ? 'CPU' : 'Unavailable'}
          warn={(v.gpu.temperature ?? v.cpu_temp ?? 0) >= 85} />
        <button
          onClick={measurePing}
          disabled={pinging}
          className="readout-tile p-3.5 text-left focus-visible:outline-2 focus-visible:outline-accent"
        >
          <div className="flex items-center justify-between mb-1.5">
            <span className="flex items-center gap-1.5 text-[9.5px] font-semibold tracking-[0.1em] text-text-tertiary uppercase">
              <Activity size={11} /> Ping
            </span>
            {pinging && <Loader2 size={11} className="animate-spin text-accent-ink" />}
          </div>
          <div className="readout-value">
            {ping == null ? '—' : ping}
            {ping != null && <span className="text-[11px] font-medium text-text-tertiary ml-1 tracking-normal">ms</span>}
          </div>
          <div className="text-[10.5px] text-text-tertiary mt-2 leading-tight">
            {ping == null ? 'Measure against 1.1.1.1' : 'Cloudflare, 4 samples'}
          </div>
        </button>
      </section>

      {/* Live shape: the same real samples, drawn by d3. Each poll morphs the
          curve instead of replacing the picture, so change is legible. */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 surface-card p-4 min-w-0">
          <div className="flex items-start justify-between gap-3 mb-1">
            <div>
              <h2 className="card-title">Live load</h2>
              <p className="text-[11.5px] text-text-tertiary mt-0.5">
                {history.cpu.length >= 2
                  ? `${history.cpu.length} samples · refreshed every ${POLL_MS / 1000}s`
                  : 'Collecting samples…'}
              </p>
            </div>
            <span className="text-[10.5px] text-text-tertiary tnum shrink-0 mt-0.5">
              {history.cpu.length >= 2 ? 'hover to inspect' : 'waiting'}
            </span>
          </div>
          {history.cpu.length >= 2 ? (
            <StreamArea
              height={156}
              yMax={100}
              unit="%"
              series={[
                { key: 'cpu', label: 'CPU', color: 'var(--chart-1)', values: history.cpu },
                /* One filled series keeps the plot readable: three stacked
                   area washes turn into a grey slab on a dark surface. */
                { key: 'ram', label: 'RAM', color: 'var(--chart-2)', values: history.ram, fill: false },
                { key: 'disk', label: 'Disk', color: 'var(--chart-3)', values: history.disk, fill: false },
              ]}
              ariaLabel="CPU, memory and disk load over the last samples"
            />
          ) : (
            <div className="h-[156px] flex items-center justify-center text-[12px] text-text-tertiary">
              Two samples are needed to draw a trend — the next poll lands in a few seconds.
            </div>
          )}
        </div>

        <div className="surface-card p-4 flex flex-col items-center min-w-0">
          <div className="self-start">
            <h2 className="card-title">Health shape</h2>
            <p className="text-[11.5px] text-text-tertiary mt-0.5">
              {healthShape.length ? `${data.health.overall}/100 overall` : 'No dimension scores reported'}
            </p>
          </div>
          <div className="flex-1 flex items-center justify-center py-2">
            <RadarScores
              scores={healthShape}
              size={186}
              ariaLabel="Health dimension scores"
            />
          </div>
        </div>
      </section>

      {/* Two-column: recommendations | recent activity */}
      <section className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        {/* Recommendations */}
        <div className="lg:col-span-3 surface-card p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="card-title">Needs attention</h2>
            <button
              onClick={() => onNavigate('health-scores')}
              className="flex items-center gap-1 text-[11.5px] text-text-tertiary hover:text-text transition-colors"
            >
              All scores <ArrowRight size={11} />
            </button>
          </div>

          {topActions.length === 0 ? (
            <div className="py-6 flex flex-col items-center text-center gap-2">
              <CircleCheck size={22} className="text-green" />
              <p className="text-[13px] text-text-secondary">Nothing needs attention</p>
              <p className="text-[11.5px] text-text-tertiary max-w-[36ch]">
                Memory, storage and power are within healthy ranges.
              </p>
            </div>
          ) : (
            <ul className="space-y-1.5">
              {topActions.map((a) => {
                const SevIcon = a.severity === 'high' ? CircleAlert
                  : a.severity === 'medium' ? TriangleAlert : Info
                return (
                  <li key={a.id}>
                    <button
                      onClick={() => onNavigate(a.page)}
                      className="w-full flex items-start gap-3 rounded-[10px] p-2.5 text-left
                        hover:bg-surface-3 transition-colors duration-150 group"
                    >
                      <span className={cn(
                        'mt-0.5 w-6 h-6 rounded-md flex items-center justify-center shrink-0',
                        a.severity === 'high' ? 'bg-red-dim text-red'
                          : a.severity === 'medium' ? 'bg-yellow-dim text-yellow'
                            : 'bg-surface-4 text-text-secondary',
                      )}>
                        <SevIcon size={13} />
                      </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-[12.5px] font-medium text-text">{a.title}</span>
                      <span className="block text-[11.5px] text-text-tertiary leading-[1.45] mt-0.5">
                        {a.detail}
                      </span>
                    </span>
                    <ChevronRight size={13} className="text-text-tertiary mt-1 shrink-0
                      opacity-0 group-hover:opacity-100 transition-opacity" />
                  </button>
                </li>
                )
              })}
            </ul>
          )}

          {/* Last run, with real before/after benchmarks when the backend recorded them */}
          {data.last_optimization && (
            <div className="mt-4 pt-3.5 border-t border-border">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-[12px] font-semibold text-text-secondary">Last optimization</h3>
                <span className="text-[11px] text-text-tertiary">
                  {formatRelative(data.last_optimization.timestamp)}
                </span>
              </div>
              <p className="text-[12px] text-text-secondary mb-1">
                {data.last_optimization.name} — {data.last_optimization.success_count}/
                {data.last_optimization.total_count} steps in{' '}
                {formatDuration(data.last_optimization.duration_ms)}
              </p>
              {data.last_optimization.benchmark_before && data.last_optimization.benchmark_after && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2 mt-2.5">
                  {Object.keys(data.last_optimization.benchmark_before).slice(0, 4).map((key) => (
                    <BarPair
                      key={key}
                      label={key.replace(/_/g, ' ')}
                      before={data.last_optimization!.benchmark_before![key]}
                      after={data.last_optimization!.benchmark_after![key] ?? data.last_optimization!.benchmark_before![key]}
                    />
                  ))}
                </div>
              )}
              <button
                onClick={() => onNavigate('timeline')}
                className="mt-2.5 flex items-center gap-1 text-[11.5px] text-accent-ink hover:text-accent transition-colors"
              >
                Open timeline <ArrowRight size={11} />
              </button>
            </div>
          )}
        </div>

        {/* Right rail: games + recent activity */}
        <div className="lg:col-span-2 space-y-4">
          <div className="surface-card p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="card-title">Your games</h2>
              <button
                onClick={() => onNavigate('games')}
                className="flex items-center gap-1 text-[11.5px] text-text-tertiary hover:text-text transition-colors"
              >
                Library <ArrowRight size={11} />
              </button>
            </div>
            {games.length === 0 ? (
              <p className="text-[12px] text-text-tertiary py-3">
                No game profiles loaded yet — they ship with the app.
              </p>
            ) : (
              <ul className="space-y-1">
                {[...pinnedGames, ...games.filter((g) => !library?.isGameFavorite(g.id))]
                  .slice(0, 4)
                  .map((g, i) => {
                    const isDetected = detectedGame?.id === g.id
                    return (
                      <li key={`${g.id}-${i}`}>
                        <div className="flex items-center gap-2.5 rounded-[10px] px-2.5 py-2
                          hover:bg-surface-3 transition-colors">
                          <span className="w-7 h-7 rounded-lg bg-surface-4 border border-border
                            flex items-center justify-center text-[12px] font-semibold text-text-secondary shrink-0">
                            {g.name.slice(0, 1)}
                          </span>
                          <span className="min-w-0 flex-1">
                            <span className="block text-[12.5px] truncate">{g.name}</span>
                            <span className="block text-[10.5px] text-text-tertiary truncate">
                              {isDetected ? 'Running now' : g.description}
                            </span>
                          </span>
                          <button
                            onClick={() => applyGameProfile(g.id, g.name)}
                            disabled={!!busy}
                            aria-label={`Apply ${g.name} profile`}
                            className="h-6 px-2 rounded-md text-[11px] font-medium
                              bg-surface-4 hover:bg-accent hover:text-on-accent
                              text-text-secondary transition-colors disabled:opacity-50"
                          >
                            {busy === `game:${g.id}` ? <Loader2 size={11} className="animate-spin" /> : 'Apply'}
                          </button>
                        </div>
                      </li>
                    )
                  })}
              </ul>
            )}
          </div>

          <div className="surface-card p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="card-title">Recent activity</h2>
              <button
                onClick={() => onNavigate('history')}
                className="flex items-center gap-1 text-[11.5px] text-text-tertiary hover:text-text transition-colors"
              >
                History <ArrowRight size={11} />
              </button>
            </div>
            {recent.length === 0 ? (
              <p className="text-[12px] text-text-tertiary py-3">
                Nothing recorded yet. Runs, snapshots and alerts appear here.
              </p>
            ) : (
              <ul className="space-y-2">
                {recent.slice(0, 5).map((e, i) => (
                  <li key={`${e.timestamp}-${i}`} className="flex items-start gap-2.5">
                    <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-accent shrink-0" />
                    <span className="min-w-0 flex-1">
                      <span className="block text-[12px] text-text-secondary leading-snug">{e.name}</span>
                      <span className="block text-[10.5px] text-text-tertiary">
                        {formatRelative(e.timestamp)} · {e.type}
                      </span>
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </section>
    </div>
  )
}

/* ------------------------------------------------------------------ vitals */

function VitalCard({
  icon: Icon, label, value, sub, series, warn, hint,
}: {
  icon: IconComponent
  label: string
  value: string
  sub: string
  series?: number[]
  invert?: boolean
  warn?: boolean
  hint?: string
}) {
  const clean = (series ?? []).filter((n) => !Number.isNaN(n))
  return (
    <TiltCard className="min-w-0 h-full" innerClassName="h-full">
      <div
        className="readout-tile p-3.5 min-w-0 h-full"
        title={hint ?? `${label}: ${value} — ${sub}`}
      >
        <div className="flex items-center justify-between mb-1.5">
          <span className="flex items-center gap-1.5 text-[9.5px] font-semibold tracking-[0.1em] text-text-tertiary uppercase">
            <Icon size={11} className={warn ? 'text-red' : 'text-accent-ink/80'} />
            {label}
          </span>
          {warn && <span className="text-[10px] font-medium text-red bg-red-dim px-1.5 py-px rounded">hot</span>}
        </div>
        <div className={cn('readout-value', warn && 'text-red')}>
          {value}
        </div>
        <div className="text-[10.5px] text-text-tertiary mt-2 truncate" title={sub}>{sub}</div>
        <div className="mt-2 h-7">
          {clean.length >= 2 ? (
            <Sparkline values={clean} width={200} height={28} className="w-full opacity-90" ariaLabel={`${label} trend`} />
          ) : (
            <div className="h-full flex items-center text-[10px] text-text-tertiary">
              {hint ? <span className="leading-tight">{hint}</span> : 'collecting samples…'}
            </div>
          )}
        </div>
      </div>
    </TiltCard>
  )
}

/* --------------------------------------------------------------- formatting */

/** Backend keys are snake_case; the UI reads them as plain words. */
function humanize(s: string): string {
  return s.replace(/[_-]+/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

/* Axis names for the health radar. Keys without an entry fall back to
   humanize(), so a new backend score still renders with a readable name. */
const HEALTH_LABELS: Record<string, string> = {
  pc_health: 'PC health',
  windows_health: 'Windows',
  gaming: 'Gaming',
  security: 'Security',
  storage: 'Storage',
  battery: 'Battery',
  developer: 'Developer',
}

const HEALTH_ORDER = ['pc_health', 'windows_health', 'gaming', 'security', 'storage', 'battery', 'developer']

function rankScoreKey(key: string): number {
  const i = HEALTH_ORDER.indexOf(key)
  return i === -1 ? HEALTH_ORDER.length : i
}

/* ------------------------------------------------------------------ status */

function deriveStatus(data: Overview | null): { headline: string; label: string; tone: 'ok' | 'warn' | 'bad'; detail: string } {
  if (!data) return { headline: 'Reading system…', label: 'Loading', tone: 'warn', detail: '' }
  const score = data.health.overall
  const urgent = data.actions.find((a) => a.severity === 'high')
  const warnings = data.actions.filter((a) => a.severity !== 'ok' && a.severity !== 'high')

  if (urgent) {
    return {
      headline: urgent.title,
      label: 'Needs attention',
      tone: 'bad',
      detail: urgent.detail,
    }
  }
  if (warnings.length > 0 || score < 85) {
    return {
      headline: 'Running well, with notes',
      label: 'Advisories',
      tone: 'warn',
      detail: warnings[0]?.detail ?? `Health score is ${score}/100. Review the advisories below.`,
    }
  }
  return {
    headline: 'Everything looks good',
    label: 'Healthy',
    tone: 'ok',
    detail: 'Memory, storage and power are all within healthy ranges. Safe to play.',
  }
}

/* ---------------------------------------------------------------- skeleton */

function HomeSkeleton() {
  return (
    <div className="page space-y-4">
      <div className="surface-card h-[260px] animate-pulse-subtle" />
      <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-2.5">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="surface-card h-[108px] animate-pulse-subtle" />
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        <div className="lg:col-span-3 surface-card h-[300px] animate-pulse-subtle" />
        <div className="lg:col-span-2 surface-card h-[300px] animate-pulse-subtle" />
      </div>
    </div>
  )
}

function NoticeBar({ notice, onDismiss }: { notice: Notice; onDismiss: () => void }) {
  return (
    <div
      role="status"
      className={cn(
        'flex items-start gap-2.5 rounded-[10px] px-3.5 py-2.5 text-[12.5px] animate-rise',
        notice.tone === 'ok' && 'bg-green-dim text-green border border-green/30',
        notice.tone === 'warn' && 'bg-yellow-dim text-yellow border border-yellow/30',
        notice.tone === 'error' && 'bg-red-dim text-red border border-red/30',
      )}
    >
      {notice.tone === 'ok'
        ? <CircleCheck size={15} className="shrink-0 mt-px" />
        : <CircleAlert size={15} className="shrink-0 mt-px" />}
      <span className="flex-1">{notice.text}</span>
      <button onClick={onDismiss} aria-label="Dismiss" className="shrink-0 hover:opacity-70 transition-opacity">
        ×
      </button>
    </div>
  )
}
