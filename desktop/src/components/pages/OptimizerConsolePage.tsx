import { useEffect, useState } from 'react'
import {
  CheckCircle2, Circle, CircleAlert, Loader2, Plus, ShieldAlert, XCircle,
} from 'lucide-react'
import { cn } from '../../lib/utils'
import { toolsInZone, groupsInZone } from '../../nav'
import { api } from '../../lib/api'
import { useOptimizerGames } from '../../hooks/useOptimizerGames'
import type { Library } from '../../hooks/useLibrary'
import type { OptimizeRun, Overview, PingResult, PresetMode } from '../../types'
import { GameProfileCard } from '../../components/optimizer/GameProfileCard'
import { OtherGameCard } from '../../components/optimizer/OtherGameCard'
import { ToolCard } from '../../components/optimizer/ToolCard'

/** The backend titles cases step ids ("memory_free" → "Memory Free"); the
    queued list must read exactly like what the backend will report. */
const planLabel = (id: string) =>
  id.replace(/_/g, ' ').replace(/(^|\s)\S/g, (c) => c.toUpperCase())

/** While the run is in flight the only honest claim about a step is that it
    exists and has not reported an outcome — never a fake "in progress". */
type StepStatus = 'queued' | 'success' | 'fail'

interface PlanStep { id: string; label: string }

/** If the service hiccup, the console stays usable with an honest default. */
const FALLBACK_PRESET: PresetMode = {
  id: 'balanced', name: 'Balanced', summary: 'Safe default pass.', detail: [], categories: [], post: [],
}

interface OptimizerConsolePageProps {
  onNavigate: (id: string) => void
  library: Library
}

/** ExitLag-mode console for the Optimizer zone: a dark green-accented activation
 * screen driving the app's real optimization backend. Every status shown comes
 * from an actual backend response; nothing is simulated.
 *
 * Structure: the Games section (scan, matching, apply/revert) is owned by
 * useOptimizerGames; the Activation console (overview, presets, ping, run)
 * lives here; the cards are presentation-only components. */
export function OptimizerConsolePage({ onNavigate, library }: OptimizerConsolePageProps) {
  const [ov, setOv] = useState<Overview | null>(null)
  const [run, setRun] = useState<OptimizeRun | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [preset, setPreset] = useState<PresetMode | null>(null)
  /** The preset's real plan (categories + post actions), captured the moment
      Activate is pressed, so rows exist while the request is still blocking. */
  const [plan, setPlan] = useState<PlanStep[] | null>(null)
  const [presets, setPresets] = useState<PresetMode[]>([])
  const [ping, setPing] = useState<PingResult | null>(null)

  const gamesSection = useOptimizerGames()

  const tools = toolsInZone('optimizer')
  const groups = groupsInZone('optimizer')

  useEffect(() => {
    let alive = true
    api.overview().then((d) => { if (alive) setOv(d) }).catch(() => { /* hero shows dashes */ })
    api.presets().then((d) => {
      if (!alive) return
      setPresets(d.presets)
      const def = d.presets.find((p) => p.id === 'balanced') ?? d.presets[0] ?? null
      setPreset(def)
    }).catch(() => { /* fallback preset below */ })
    api.speedTestPing('1.1.1.1', 4).then((p) => { if (alive) setPing(p) }).catch(() => {
      /* A failed measurement must not keep saying "measuring…" forever. */
      if (alive) setPing({ host: '1.1.1.1', error: 'Could not measure' })
    })
    return () => { alive = false }
  }, [])

  const presetShown = preset ?? FALLBACK_PRESET

  const admin = ov?.vitals?.is_admin ?? null
  const reclaim = ov?.reclaimable ?? null

  async function activate() {
    if (busy) return
    setBusy(true)
    setErr(null)
    setRun(null)
    /* The queue is the preset's own plan — the same categories and post
       actions the backend executes, in the same order. Nothing is invented
       beyond what the user just asked to run. */
    setPlan([
      ...presetShown.categories.map((id) => ({ id, label: planLabel(id) })),
      ...presetShown.post.map((id) => ({ id, label: planLabel(id) })),
    ])
    try {
      const res = await api.optimizeQuick(presetShown.id)
      setRun(res)
    } catch (e) {
      setErr(e instanceof Error ? e.message : `Could not run ${presetShown.name}`)
    } finally {
      setBusy(false)
    }
  }

  /** The visible step list: plan rows until the response lands, then each row
      promoted strictly to its actual reported outcome. A fail is a fail. */
  const stepViews: { id: string; label: string; status: StepStatus; message: string | null }[] = (() => {
    if (!plan) return []
    if (!run) return plan.map((p) => ({ ...p, status: 'queued' as StepStatus, message: null }))
    const reported = new Map(run.steps.map((s) => [s.id, s]))
    const rows = plan.map((p) => {
      const s = reported.get(p.id)
      return {
        ...p,
        status: (s ? (s.success ? 'success' : 'fail') : 'queued') as StepStatus,
        message: s?.message ?? null,
      }
    })
    /* Steps the backend reports that the plan missed (custom profiles) keep
       their real outcome instead of silently vanishing. */
    for (const s of run.steps) {
      if (!plan.some((p) => p.id === s.id)) {
        rows.push({ id: s.id, label: s.label, status: s.success ? 'success' : 'fail', message: s.message })
      }
    }
    return rows
  })()

  /* The bar fills with actually-successful steps only — a gated fail lowers
      it, exactly like the "x/y steps applied" header does. */
  const settleFraction = run && run.total > 0 ? run.succeeded / run.total : 0

  const ramAvail = ov?.vitals ? ov.vitals.ram_total_gb - ov.vitals.ram_used_gb : null
  const ramDelta = run ? run.deltas.ram_available_gb : null
  /* process_count delta is already after-minus-before; it needs no negation. */
  const procDelta = run ? run.deltas.process_count : null
  const diskDelta = run ? run.deltas.disk_free_gb : null

  return (
    <div className="page animate-rise">
      {/* ---------------- Hero band ---------------- */}
      <section className="band-hero relative overflow-hidden mb-5">
        <div aria-hidden className="pointer-events-none absolute inset-0 z-0 overflow-hidden rounded-[inherit]">
          <span className="hero-key" />
          <span className="hero-key hero-key-violet" />
          <span className="hero-shaft" />
          <span className="hero-baseline" />
          <span className="hero-grain absolute inset-0" />
        </div>
        <div className="relative z-10 flex justify-between items-end flex-wrap gap-8 p-6 lg:p-7">
          <div className="min-w-0">
            <div className="mb-2.5 flex items-center gap-2.5">
              <span className="h-1 w-4 rounded-full bg-accent" aria-hidden />
              <span className="eyebrow text-accent-ink/85">One pass</span>
            </div>
            <h1 className="font-display text-[30px] leading-[1.1] font-bold tracking-[-0.035em]">
              Optimize your system
            </h1>
            <p className="page-subtitle mt-2 max-w-[58ch]">
              Free memory, trim what runs in the background and stabilise the connection in one pass.
              Every step is a real Windows change — nothing here is simulated.
            </p>
          </div>

          {/* Live read-outs: real values only, same plate language as the shell. */}
          <dl className="hidden lg:flex gap-7">
            <Stat label="ping" top={ping?.avg_ms != null ? `${Math.round(ping.avg_ms)}` : '—'} tail={ping?.avg_ms != null ? 'ms · 1.1.1.1' : (ping?.error ? 'unavailable' : 'measuring…')} />
            <Stat label="ram available" top={ramAvail != null ? ramAvail.toFixed(1) : '—'} tail={ramAvail != null ? 'GB' : ''} />
            <Stat label="junk found" top={reclaim && reclaim.total_bytes > 0 ? (reclaim.total_bytes / 1024 ** 3).toFixed(1) : '—'} tail={reclaim && reclaim.total_bytes > 1024 ** 3 ? 'GB' : ''} />
            <Stat label="processes" top={ov?.vitals ? `${ov.vitals.process_count}` : '—'} tail="" />
          </dl>
        </div>
      </section>

      <div>
        {/* ---------------- Games (installed only, with covers) ---------------- */}
        <section className="mb-7">
          <h3 className="font-display text-[13px] font-semibold uppercase tracking-[0.07em] text-text-secondary mb-3">
            Games
          </h3>
          <p className="text-[10px] text-text-tertiary mt-1">
            Games verified on this PC — a profile is offered only when its installation is confirmed.
          </p>
          {gamesSection.state === 'loading' && (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2.5">
              {[0, 1, 2, 3].map((i) => <div key={i} className="surface-card aspect-[3/4] animate-pulse-subtle" />)}
            </div>
          )}
          {gamesSection.state === 'error' && (
            <p className="text-[12.5px] text-text-secondary">Could not scan for installed games — retry from the Games page.</p>
          )}
          {gamesSection.state === 'ready'
            && gamesSection.profileList?.length === 0 && gamesSection.others.length === 0 && (
            <p className="text-[12.5px] text-text-secondary">
              No games detected on this PC. The scan reads the Steam library and installed-programs list — it guesses nothing.
            </p>
          )}
          {gamesSection.state === 'ready'
            && ((gamesSection.profileList?.length ?? 0) > 0 || gamesSection.others.length > 0) && (
            <>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2.5">
                {gamesSection.profileList?.map((p) => (
                  <GameProfileCard
                    key={p.id}
                    profile={p}
                    detected={gamesSection.detectedId === p.id}
                    applied={gamesSection.appliedId === p.id && gamesSection.busyId !== p.id}
                    busy={gamesSection.busyId === p.id}
                    feed={gamesSection.applyFeed?.id === p.id ? gamesSection.applyFeed.rows : null}
                    onApply={() => gamesSection.apply(p)}
                    onRevert={gamesSection.revert}
                  />
                ))}
                {gamesSection.others.map((g) => <OtherGameCard key={g.name} game={g} />)}
                {/* A single verified game used to leave a 4-column row with
                    three holes in it. The row now ends on a real destination
                    instead of empty track. */}
                <button
                  onClick={() => onNavigate('games')}
                  className="group flex aspect-[3/4] flex-col items-center justify-center gap-2 rounded-[14px]
                    border border-dashed border-border text-text-tertiary
                    transition-colors hover:border-accent/40 hover:text-text"
                >
                  <Plus size={17} />
                  <span className="text-[11.5px] font-medium">Browse library</span>
                  <span className="max-w-[15ch] text-center text-[10.5px] leading-[1.4] text-text-tertiary">
                    Every game Optinix verified on this PC
                  </span>
                </button>
              </div>
              {gamesSection.others.length > 0 && (
                <p className="text-[11px] text-text-tertiary mt-2">
                  Installed games without an optimization profile yet. Add one from the Games page.
                </p>
              )}
            </>
          )}
        </section>

        {/* ---------------- Activation console ---------------- */}
        <section className="surface-card p-6 mb-7">
          <div className="grid lg:grid-cols-[1fr_auto] gap-7 items-center">
            <div>
              <h2 className="font-display text-[22px] font-semibold uppercase tracking-[0.01em]">
                {presetShown.name}
              </h2>
              <p className="text-[13px] text-text-secondary mt-1.5 max-w-[62ch]">
                {presetShown.summary}
              </p>
              <div className="flex flex-wrap gap-2 mt-4" role="radiogroup" aria-label="Optimization preset">
                {presets.length > 0 ? presets.map((p) => {
                  const on = preset?.id === p.id
                  return (
                    <button
                      key={p.id}
                      role="radio"
                      aria-checked={on}
                      onClick={() => { setPreset(p); setRun(null); setErr(null) }}
                      className={cn(
                        'font-display uppercase text-[12px] font-semibold tracking-[0.04em] px-4 py-2 rounded-lg border transition-colors duration-150',
                        on ? 'bg-eg-green-dim text-eg-green border-eg-line'
                           : 'text-text-secondary bg-surface-2 border-border hover:text-text hover:border-border-light',
                      )}
                    >
                      {p.name}
                    </button>
                  )
                }) : (
                  <span className="text-[12px] text-text-tertiary">Optimizer presets are loading…</span>
                )}
              </div>
            </div>

            <div className="text-center lg:px-6">
              <button
                onClick={activate}
                disabled={busy}
                className={cn(
                  'eg-activate font-display uppercase font-bold text-[16px] tracking-[0.08em] px-12 py-4 rounded-xl transition-all duration-150',
                  busy && 'cursor-wait',
                )}
              >
                {busy ? <span className="inline-flex items-center gap-2"><Loader2 size={17} className="animate-spin" /> Optimizing…</span>
                  : run ? 'Apply again' : 'Activate'}
              </button>
              <p className="text-[11px] text-text-tertiary mt-2.5 tnum max-w-[26ch] mx-auto">
                {admin === false
                  ? 'Not running as administrator — system-level steps will be skipped.'
                  : admin === true ? 'Administrator privileges detected.' : 'Checking session privileges…'}
              </p>
            </div>
          </div>

          {/* Progress area: one bar + one step list for the whole run. While
              the request is in flight the bar sweeps honestly and every planned
              step waits dimmed; the response promotes rows to their real
              outcomes and the fill settles on actual successes only. */}
          {(busy || run) && (
            <div className="eg-feed mt-6 pl-6">
              <div className="flex items-baseline justify-between mb-2">
                <p className={cn('text-[13px]', run ? 'text-text' : 'text-text-secondary')}>
                  {run
                    ? (<>
                        <CheckCircle2 size={15} className="inline -mt-0.5 text-eg-green mr-1.5" />
                        {run.name} finished — <span className="tnum">{run.succeeded}/{run.total}</span> steps applied
                      </>)
                    : <><Loader2 size={14} className="inline -mt-0.5 mr-1.5 animate-spin align-baseline" />{presetShown.name} is running…</>}
                </p>
                <span className="text-[15px] font-display font-bold tnum text-eg-green">
                  {Math.round(settleFraction * 100)}%
                </span>
              </div>
              <div
                className="eg-bar mb-3"
                role="progressbar"
                aria-valuenow={Math.round(settleFraction * 100)}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={`${presetShown.name} optimization progress`}
              >
                <div
                  className="eg-bar-fill"
                  data-indeterminate={run ? undefined : 'true'}
                  style={{ width: run ? `${settleFraction * 100}%` : '25%' }}
                />
              </div>
              <ul className="space-y-1.5">
                {stepViews.map((s, i) => (
                  <li
                    key={s.id}
                    className={cn(
                      'eg-feed-row flex items-start gap-2 text-[12px]',
                      s.status === 'queued' && 'eg-step-queued',
                    )}
                    style={{ animationDelay: `${i * 60}ms` }}
                  >
                    {s.status === 'queued'
                      ? <Circle size={13} className="text-text-tertiary mt-0.5 shrink-0" />
                      : s.status === 'success'
                        ? <CheckCircle2 size={13} className="text-eg-green mt-0.5 shrink-0" />
                        : <XCircle size={13} className="text-red mt-0.5 shrink-0" />}
                    <span className={cn('text-text-secondary', s.status === 'success' && 'text-text')}>{s.label}</span>
                    {s.message && <span className="text-text-tertiary">{s.message}</span>}
                  </li>
                ))}
              </ul>
              {run && (
                <p className="text-[11.5px] text-text-secondary mt-3 tnum">
                  {ramDelta != null && ramDelta !== 0 && <span className="mr-4">RAM available {ramDelta > 0 ? '+' : ''}{ramDelta.toFixed(2)} GB</span>}
                  {diskDelta != null && diskDelta !== 0 && <span className="mr-4">Disk free {diskDelta > 0 ? '+' : ''}{diskDelta.toFixed(2)} GB</span>}
                  {procDelta != null && procDelta !== 0 && <span>Processes {procDelta > 0 ? '+' : ''}{procDelta}</span>}
                  {(ramDelta == null || ramDelta === 0) && (diskDelta == null || diskDelta === 0) && (procDelta == null || procDelta === 0)
                    && 'No measurable change this run.'}
                </p>
              )}
            </div>
          )}

          {err && (
            <div className="flex items-start gap-2.5 mt-5">
              <CircleAlert size={16} className="text-red shrink-0 mt-0.5" />
              <div>
                <p className="text-[13px] text-text">The optimization did not complete</p>
                <p className="text-[12px] text-text-secondary mt-0.5">{err}</p>
              </div>
            </div>
          )}

          {admin === false && (
            <p className="mt-5 inline-flex items-center gap-1.5 text-[11px] text-yellow bg-yellow-dim px-2.5 py-1.5 rounded-md">
              <ShieldAlert size={12} />
              Restart as administrator for the full pass.
            </p>
          )}
        </section>

        {/* ---------------- Tool grid ---------------- */}
        {groups.map((group) => {
          const items = tools.filter((t) => t.group === group)
          if (!items.length) return null
          return (
            <section key={group} className="mb-8">
              <h3 className="font-display text-[13px] font-semibold uppercase tracking-[0.07em] text-text-secondary mb-3">
                {group}
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-2.5">
                {items.map((tool) => (
                  <ToolCard
                    key={tool.id}
                    tool={tool}
                    onOpen={() => onNavigate(tool.id)}
                    onTogglePin={() => library.toggleFavorite(tool.id)}
                    pinned={library.isFavorite(tool.id)}
                  />
                ))}
              </div>
            </section>
          )
        })}

        <p className="text-[11px] text-text-tertiary mt-2 mb-2">
          Session state (this run, the ping read-out) clears when Optinix closes. Optimizations themselves persist in Windows until reverted.
        </p>
      </div>
    </div>
  )
}

function Stat({ label, top, tail }: { label: string; top: string; tail: string | null }) {
  return (
    <div className="text-right">
      <dt className="text-[9.5px] font-semibold uppercase tracking-[0.12em] text-text-tertiary">{label}</dt>
      <dd className="metric-value mt-1 text-[26px] leading-none text-text">{top}</dd>
      {tail && <dd className="mt-1 text-[9.5px] font-semibold uppercase tracking-[0.08em] text-accent-ink/85">{tail}</dd>}
    </div>
  )
}
