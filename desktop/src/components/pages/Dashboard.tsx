import { useCallback, useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  Brain,
  Camera,
  CheckCircle2,
  Cpu,
  Eraser,
  Gamepad2,
  MemoryStick as MemoryIcon,
  Monitor,
  MousePointer2,
  Network,
  Radar,
  Rocket,
  ShieldCheck,
  Sparkles,
  Timer,
  Wifi,
  Zap,
  ChevronRight,
  Gauge,
} from 'lucide-react'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'
import { ProgressBar } from '../ui/ProgressBar'
import { Skeleton } from '../ui/Skeleton'
import { PageHero } from '../ui/PageHero'
import { Sparkline } from '../ui/charts/Sparkline'
import { StreamArea } from '../ui/charts/StreamArea'
import { RadialMeter } from '../ui/charts/RadialMeter'
import { useRollingSeries } from '../../hooks/useRollingSeries'
import { cn, formatBytes, formatSpeed, healthScore } from '../../lib/utils'
import { api } from '../../lib/api'
import type { AiBottleneck, AiHealthScoreResponse, AiRecommendation, SmartDetect, SystemInfo } from '../../types'

interface DashboardProps {
  systemInfo: SystemInfo | null
  onNavigate?: (page: string) => void
}

type ActionTone = 'core' | 'safe' | 'danger' | 'cyan'

/* Tone lives on the icon chip; the tile surface stays neutral so ten actions in
   a grid do not read as ten alert levels. */
const toneClass: Record<ActionTone, string> = {
  core: 'text-accent border-border hover:border-accent/55',
  safe: 'text-green border-border hover:border-green/55',
  danger: 'text-red border-border hover:border-red/55',
  cyan: 'text-cyan border-border hover:border-cyan/55',
}

const HISTORY = 26

export function Dashboard({ systemInfo, onNavigate }: DashboardProps) {
  const [smartDetect, setSmartDetect] = useState<SmartDetect | null>(null)
  const [loadingSmart, setLoadingSmart] = useState(true)
  const [aiHealth, setAiHealth] = useState<AiHealthScoreResponse | null>(null)
  const [, setLoadingAiHealth] = useState(true)
  const [aiRecs, setAiRecs] = useState<AiRecommendation[]>([])
  const [loadingAiRecs, setLoadingAiRecs] = useState(true)
  const [bottlenecks, setBottlenecks] = useState<AiBottleneck[]>([])
  const [loadingBottlenecks, setLoadingBottlenecks] = useState(true)
  const [activeAction, setActiveAction] = useState<string | null>(null)
  const [actionResult, setActionResult] = useState<{ title: string; message: string; ok: boolean } | null>(null)

  /* Real trends from the shared snapshot — the tiles used to draw random walks. */
  const cpuSeries = useRollingSeries(systemInfo?.cpu.percent ?? null, systemInfo, HISTORY)
  const gpuSeries = useRollingSeries(systemInfo?.gpu.usage ?? null, systemInfo, HISTORY)
  const ramSeries = useRollingSeries(systemInfo?.memory.percent ?? null, systemInfo, HISTORY)
  const netSeries = useRollingSeries(systemInfo?.network.speed_down ?? null, systemInfo, HISTORY)

  useEffect(() => {
    api.smartDetect()
      .then((d) => { setSmartDetect(d); setLoadingSmart(false) })
      .catch(() => setLoadingSmart(false))

    api.aiHealthScore()
      .then((d) => { setAiHealth(d); setLoadingAiHealth(false) })
      .catch(() => setLoadingAiHealth(false))

    api.aiRecommendations()
      .then((d) => { setAiRecs(d.recommendations ?? []); setLoadingAiRecs(false) })
      .catch(() => setLoadingAiRecs(false))

    api.aiBottlenecks()
      .then((d) => { setBottlenecks(d.bottlenecks ?? []); setLoadingBottlenecks(false) })
      .catch(() => setLoadingBottlenecks(false))
  }, [])

  const getHealthColor = useCallback((val: number) => {
    if (val < 40) return 'var(--color-red)'
    if (val < 80) return 'var(--color-yellow)'
    return 'var(--color-green)'
  }, [])

  /* Session model: unchanged shape, kept explicitly labelled as a model. */
  const trendData = useMemo(() =>
    Array.from({ length: 28 }, (_, i) => ({
      time: i,
      latency: Math.max(2, Math.floor(19 - i * 0.35 + Math.random() * 5)),
      fps: Math.floor(170 + i * 2.4 + Math.random() * 18),
      load: Math.floor(Math.random() * 36 + 34),
    })), [])

  const runAction = async (title: string, fn: () => Promise<unknown>) => {
    setActiveAction(title)
    setActionResult(null)
    try {
      const result = await fn()
      const message = typeof result === 'object' && result && 'message' in result
        ? String((result as { message?: unknown }).message)
        : 'Optimization completed'
      setActionResult({ title, message, ok: true })
    } catch (e) {
      setActionResult({ title, message: e instanceof Error ? e.message : 'Action failed', ok: false })
    } finally {
      setActiveAction(null)
    }
  }

  const actions = [
    { title: 'Full Optinix Sweep', desc: 'Runs CPU, memory, disk, network, gaming, startup, and service optimizers.', icon: <Rocket size={19} />, tone: 'core' as const, run: () => api.optimizeAll(), tags: ['one click', 'safe first'] },
    { title: 'Tournament Game Mode', desc: 'Prioritizes active games, applies affinity, and reduces background contention.', icon: <Gamepad2 size={19} />, tone: 'safe' as const, run: () => api.gameModeEnable(), tags: ['fps', 'focus'] },
    { title: 'GPU Max Performance', desc: 'Applies GPU scheduling and driver-level performance preferences.', icon: <Monitor size={19} />, tone: 'cyan' as const, run: () => api.gpuOptimize(), tags: ['gpu', 'frames'] },
    { title: 'RAM Purge', desc: 'Frees standby memory and starts automatic memory optimization.', icon: <MemoryIcon size={19} />, tone: 'safe' as const, run: () => api.memoryFree(), tags: ['ram', 'stutter'] },
    { title: 'Low Ping Network', desc: 'Applies adapter and TCP tuning for lower queueing and smoother packets.', icon: <Network size={19} />, tone: 'cyan' as const, run: () => api.advancedNetwork(), tags: ['ping', 'buffer'] },
    { title: 'Input Precision', desc: 'Optimizes mouse handling, pointer precision, and peripheral responsiveness.', icon: <MousePointer2 size={19} />, tone: 'core' as const, run: () => api.peripheralOptimize(), tags: ['latency'] },
    { title: 'Clean Temp Cache', desc: 'Clears temp, cache, and cleanup targets that can drag load times.', icon: <Eraser size={19} />, tone: 'safe' as const, run: () => api.diskCleanAll(), tags: ['storage'] },
    { title: 'Driver Scan', desc: 'Checks outdated, missing, and risky drivers before deep tuning.', icon: <Radar size={19} />, tone: 'cyan' as const, run: () => api.driverCheckUpdates(), tags: ['drivers'] },
    { title: 'Create Rollback', desc: 'Saves a restorable snapshot before risky changes.', icon: <Camera size={19} />, tone: 'safe' as const, run: () => api.rollbackCreateSnapshot(), tags: ['safety'] },
    { title: 'Ultimate Mode', desc: 'Aggressive performance mode for plugged-in gaming rigs.', icon: <Zap size={19} />, tone: 'danger' as const, run: () => api.extreme(), tags: ['advanced'] },
  ]

  const recTypeToPage: Record<string, string> = {
    cpu: 'cpu',
    disk: 'storage',
    driver: 'drivers-update',
    gaming: 'gaming',
    gpu: 'gpu',
    memory: 'memory',
    network: 'network',
    performance: 'extreme',
    registry: 'registry',
    security: 'security',
    services: 'services',
    startup: 'startup',
    tweak: 'windows',
  }

  if (!systemInfo) {
    return (
      <div className="page space-y-5">
        <Skeleton className="h-[190px] w-full rounded-[var(--radius-card)]" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-28 w-full rounded-[var(--radius-card)]" />)}
        </div>
        <Skeleton className="h-96 w-full rounded-[var(--radius-card)]" />
      </div>
    )
  }

  const fallbackHealth = healthScore({
    cpu: systemInfo.cpu,
    memory: systemInfo.memory,
    gpu: { usage: systemInfo.gpu.usage },
    disk: { percent: systemInfo.disk[0]?.percent ?? 0 },
  })
  const score = aiHealth?.score ?? fallbackHealth.score
  const scoreLabel = aiHealth?.label ?? fallbackHealth.label
  const disk = systemInfo.disk[0]
  const profileReadiness = Math.round((100 - systemInfo.cpu.percent) * 0.28 + (100 - systemInfo.memory.percent) * 0.24 + (100 - (disk?.percent ?? 50)) * 0.18 + Math.min(score, 100) * 0.3)
  const activeWarnings = bottlenecks.filter((b) => ['critical', 'high'].includes(b.severity)).length

  const resourceCards = [
    { label: 'CPU load', value: `${systemInfo.cpu.percent}%`, sub: `${systemInfo.cpu.physical}C / ${systemInfo.cpu.logical}T`, icon: <Cpu size={16} />, color: 'var(--chart-1)', chart: cpuSeries, progress: systemInfo.cpu.percent },
    { label: 'GPU load', value: `${systemInfo.gpu.usage}%`, sub: systemInfo.gpu.name || 'GPU not detected', icon: <Monitor size={16} />, color: 'var(--chart-2)', chart: gpuSeries, progress: systemInfo.gpu.usage },
    { label: 'Memory', value: `${systemInfo.memory.used_gb.toFixed(1)} GB`, sub: `${systemInfo.memory.available_gb.toFixed(1)} GB available`, icon: <MemoryIcon size={16} />, color: 'var(--chart-3)', chart: ramSeries, progress: systemInfo.memory.percent },
    { label: 'Network', value: formatSpeed(systemInfo.network.speed_down), sub: `${formatSpeed(systemInfo.network.speed_up)} up`, icon: <Wifi size={16} />, color: 'var(--color-violet)', chart: netSeries, progress: Math.min(100, Math.round(systemInfo.network.speed_down / 1024)) },
  ]

  const lanes = [
    { title: 'Base Sweep', label: 'Automated', desc: 'Cleanup, startup, services, registry, memory, drivers, and health checks.', page: 'oneclick', progress: 88 },
    { title: 'Game Layer', label: 'Latency', desc: 'Game Mode, raw input, timer resolution, GPU priority, and power policy.', page: 'gaming', progress: profileReadiness },
    { title: 'Deep Tune', label: 'Advanced', desc: 'BIOS recommendations, rollback, compatibility checks, and extreme tuning.', page: 'bios', progress: score },
  ]

  const healthRows = aiHealth
    ? Object.entries(aiHealth.components)
    : [['cpu', systemInfo.cpu.percent], ['memory', systemInfo.memory.percent], ['disk', disk?.percent ?? 0], ['gpu', systemInfo.gpu.usage]] as [string, number][]

  return (
    <div className="page stagger-rise space-y-5">
      <PageHero
        eyebrow="Performance bay"
        title="One surface for the whole rig"
        subtitle="FPS, input latency, network stability, cleanup, drivers, power, BIOS guidance, rollback and AI health scoring — in the order that actually moves your numbers."
        icon={<Gauge size={19} />}
        badges={
          <>
            <Badge variant="success">Live rig profile</Badge>
            <Badge variant={activeWarnings ? 'danger' : 'accent'}>
              {activeWarnings ? `${activeWarnings} priority ${activeWarnings === 1 ? 'fix' : 'fixes'}` : 'Tournament ready'}
            </Badge>
            <span className="text-[11px] text-text-tertiary">{systemInfo.os.os_name} {systemInfo.os.release}</span>
          </>
        }
        stats={[
          { label: 'Gaming readiness', value: `${profileReadiness}%`, tone: 'accent' },
          { label: 'Health score', value: `${score}/100`, tone: score >= 80 ? 'good' : score >= 60 ? 'warn' : 'bad', hint: scoreLabel },
          { label: 'Free memory', value: `${systemInfo.memory.available_gb.toFixed(1)} GB` },
          { label: 'Primary disk', value: disk ? `${100 - Math.round(disk.percent)}% free` : '—' },
        ]}
        actions={
          <>
            <Button
              variant="primary"
              size="lg"
              icon={<Rocket size={17} />}
              loading={activeAction === 'Full Optinix Sweep'}
              onClick={() => runAction('Full Optinix Sweep', () => api.optimizeAll())}
            >
              Optimize now
            </Button>
            <Button variant="secondary" size="lg" icon={<Gamepad2 size={17} />} onClick={() => onNavigate?.('gaming')}>
              Open Gaming Lab
            </Button>
            <Button variant="ghost" size="lg" icon={<Camera size={17} />} onClick={() => runAction('Create Rollback', () => api.rollbackCreateSnapshot())}>
              Snapshot
            </Button>
          </>
        }
      />

      {actionResult && (
        <div className={cn('animate-rise rounded-[var(--radius-control)] border px-4 py-3 text-[12.5px]', actionResult.ok ? 'border-green/30 bg-green-dim text-green' : 'border-red/30 bg-red-dim text-red')}>
          <span className="font-semibold">{actionResult.title}:</span> {actionResult.message}
        </div>
      )}

      <section className="grid gap-4 xl:grid-cols-[340px_minmax(0,1fr)]">
        <Card padding="lg" className="flex flex-col items-center">
          <div className="flex w-full items-start justify-between gap-3">
            <div>
              <h2 className="text-[13.5px] font-semibold text-text accent-rail">System health</h2>
              <p className="mt-1 text-[11.5px] text-text-tertiary">{scoreLabel} · AI scored</p>
            </div>
            <Badge variant={score >= 80 ? 'success' : score >= 60 ? 'warning' : 'danger'}>{score}</Badge>
          </div>

          <RadialMeter
            value={score}
            label="Health"
            size={172}
            caption={scoreLabel}
            /* Explicit tone: the dial has to agree with the badge beside it, and
               the default auto rule treats 80-84 as "warn" while the score band
               calls it good. */
            tone={score >= 80 ? 'good' : score >= 60 ? 'warn' : 'bad'}
            className="my-2"
          />

          <div className="w-full space-y-2.5">
            {healthRows.map(([key, raw]) => {
              const value = Number(raw)
              const normalized = aiHealth ? value : Math.max(0, 100 - value)
              return (
                <div key={key}>
                  <div className="mb-1 flex justify-between text-[11px]">
                    <span className="capitalize text-text-secondary">{key}</span>
                    <span className="font-semibold tnum" style={{ color: getHealthColor(normalized) }}>{Math.round(normalized)}</span>
                  </div>
                  <ProgressBar value={normalized} color={getHealthColor(normalized)} size="sm" />
                </div>
              )
            })}
          </div>
        </Card>

        <div className="grid grid-cols-2 gap-4">
          {resourceCards.map((card) => (
            <Card key={card.label} hover padding="md">
              <div className="flex items-start justify-between gap-3">
                <span className="icon-chip h-9 w-9" style={{ color: card.color }}>{card.icon}</span>
                <Sparkline
                  values={card.chart}
                  width={86}
                  height={30}
                  stroke={card.color}
                  ariaLabel={`${card.label} trend over ${card.chart.length} samples`}
                />
              </div>
              <div className="mt-3.5 text-[23px] font-semibold leading-none tracking-[-0.02em] text-text tnum">{card.value}</div>
              <div className="mt-1.5 text-[11.5px] text-text-secondary">{card.label}</div>
              <ProgressBar value={card.progress} color={card.color} size="sm" className="mt-3" />
              <div className="mt-2 truncate text-[10.5px] text-text-tertiary" title={card.sub}>{card.sub}</div>
            </Card>
          ))}
        </div>
      </section>

      <section className="grid grid-cols-1 xl:grid-cols-[0.95fr_1.05fr] gap-4">
        <Card padding="lg">
          <div className="flex items-center gap-2 mb-4">
            <ShieldCheck size={17} className="text-accent" />
            <h2 className="text-[13.5px] font-semibold text-text">Optimization stack</h2>
          </div>
          <div className="space-y-3">
            {lanes.map((lane) => (
              <button
                key={lane.title}
                onClick={() => onNavigate?.(lane.page)}
                className="group card-depth sheen w-full rounded-[var(--radius-control)] border border-border bg-surface-2/45 p-4 text-left transition-colors hover:border-accent/45 hover:bg-surface-2"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="text-[10px] uppercase tracking-widest text-accent">{lane.label}</div>
                    <div className="mt-1 flex items-center gap-1 text-[13.5px] font-semibold text-text">
                      {lane.title}
                      <ChevronRight size={14} className="text-text-tertiary transition-transform group-hover:translate-x-0.5" />
                    </div>
                    <p className="mt-1 text-[11.5px] leading-5 text-text-secondary">{lane.desc}</p>
                  </div>
                  <div className="text-xl font-semibold text-text tnum">{lane.progress}%</div>
                </div>
                <ProgressBar value={lane.progress} className="mt-3" size="sm" />
              </button>
            ))}
          </div>
        </Card>

        <Card padding="lg">
          <div className="flex items-center gap-2 mb-3">
            <Activity size={17} className="text-cyan" />
            <h2 className="text-[13.5px] font-semibold text-text">FPS / latency projection</h2>
            <span className="ml-auto text-[10px] uppercase tracking-widest text-text-tertiary">session model</span>
          </div>

          <StreamArea
            series={[{ key: 'fps', label: 'FPS', color: 'var(--chart-1)', values: trendData.map((d) => d.fps) }]}
            height={150}
            unit=" fps"
            ariaLabel="Projected frame rate across the session model"
          />

          <div className="mt-3 grid grid-cols-2 gap-3">
            <div className="rounded-[var(--radius-control)] border border-border bg-surface-2/40 p-2.5">
              <div className="flex items-center justify-between">
                <span className="text-[10.5px] uppercase tracking-[0.05em] text-text-tertiary">Latency</span>
                <span className="text-[11.5px] font-medium text-text tnum">{trendData[trendData.length - 1].latency} ms</span>
              </div>
              <Sparkline values={trendData.map((d) => d.latency)} width={150} height={26} stroke="var(--chart-4)" ariaLabel="Projected latency" />
            </div>
            <div className="rounded-[var(--radius-control)] border border-border bg-surface-2/40 p-2.5">
              <div className="flex items-center justify-between">
                <span className="text-[10.5px] uppercase tracking-[0.05em] text-text-tertiary">Render load</span>
                <span className="text-[11.5px] font-medium text-text tnum">{trendData[trendData.length - 1].load}%</span>
              </div>
              <Sparkline values={trendData.map((d) => d.load)} width={150} height={26} stroke="var(--chart-2)" ariaLabel="Projected render load" />
            </div>
          </div>

          <div className="mt-3 grid grid-cols-3 gap-3 border-t border-border pt-3">
            {[
              { label: 'FPS target', value: 'Stable' },
              { label: 'Frame time', value: '< 8 ms' },
              { label: 'Queueing', value: 'Reduced' },
            ].map((m) => (
              <div key={m.label}>
                <div className="text-[10px] uppercase tracking-wider text-text-tertiary">{m.label}</div>
                <div className="text-[12.5px] font-semibold text-text">{m.value}</div>
              </div>
            ))}
          </div>
        </Card>
      </section>

      <section>
        <div className="mb-3 flex items-center gap-2">
          <Zap size={16} className="text-accent" />
          <h2 className="text-[13.5px] font-semibold text-text">Tuning actions</h2>
          <span className="text-[11px] text-text-tertiary">safe, advanced, and gaming-focused controls</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-4">
          {actions.map((action) => (
            <motion.button
              key={action.title}
              whileHover={activeAction ? undefined : { y: -3 }}
              whileTap={activeAction ? undefined : { scale: 0.985 }}
              transition={{ type: 'spring', stiffness: 380, damping: 28 }}
              disabled={Boolean(activeAction)}
              onClick={() => runAction(action.title, action.run)}
              className={cn(
                'card-depth sheen rounded-[var(--radius-card)] border bg-surface-1 p-4 text-left shadow-e1 transition-colors disabled:cursor-not-allowed disabled:opacity-60',
                toneClass[action.tone],
              )}
            >
              <div className="flex items-start justify-between gap-2">
                <span className="icon-chip h-9 w-9">
                  {activeAction === action.title ? <Sparkles className="animate-spin" size={18} /> : action.icon}
                </span>
                {action.tone === 'danger' && <AlertTriangle size={14} className="text-yellow" />}
              </div>
              <div className="mt-3.5 text-[13px] font-semibold text-text">{action.title}</div>
              <p className="mt-1 min-h-[50px] text-[11.5px] leading-[1.5] text-text-secondary">{action.desc}</p>
              <div className="mt-2.5 flex flex-wrap gap-1.5">
                {action.tags.map((tag) => (
                  <span key={tag} className="rounded border border-border bg-surface-3/70 px-1.5 py-0.5 text-[10px] font-medium text-text-tertiary">{tag}</span>
                ))}
              </div>
            </motion.button>
          ))}
        </div>
      </section>

      <section className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <Card padding="lg">
          <div className="mb-4 flex items-center gap-2">
            <Brain size={17} className="text-accent" />
            <h2 className="text-[13.5px] font-semibold text-text">AI recommendations</h2>
            {loadingAiRecs && <span className="ml-auto text-[11px] text-text-tertiary">Scanning…</span>}
          </div>
          <div className="space-y-2">
            {loadingAiRecs ? Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-16 w-full rounded-[var(--radius-control)]" />) : (
              aiRecs.length ? aiRecs.slice(0, 5).map((rec, i) => (
                <button
                  key={`${rec.title}-${i}`}
                  onClick={() => onNavigate?.(recTypeToPage[rec.type] ?? 'oneclick')}
                  className="group w-full rounded-[var(--radius-control)] border border-border bg-surface-2/40 p-3 text-left transition-colors hover:border-accent/45"
                >
                  <div className="flex items-center gap-2">
                    <Sparkles size={13} className="text-accent" />
                    <span className="text-[12.5px] font-semibold text-text">{rec.title}</span>
                    <Badge variant={rec.priority === 'high' ? 'danger' : rec.priority === 'medium' ? 'warning' : 'info'}>{rec.priority}</Badge>
                    <ChevronRight size={13} className="ml-auto text-text-tertiary transition-transform group-hover:translate-x-0.5" />
                  </div>
                  <p className="mt-1 text-[11.5px] leading-5 text-text-secondary">{rec.description}</p>
                </button>
              )) : (
                <div className="flex items-center gap-2 rounded-[var(--radius-control)] border border-green/25 bg-green-dim p-3 text-[12.5px] text-green">
                  <CheckCircle2 size={15} />
                  No AI recommendations right now.
                </div>
              )
            )}
          </div>
        </Card>

        <Card padding="lg">
          <div className="mb-4 flex items-center gap-2">
            <AlertCircle size={17} className="text-red" />
            <h2 className="text-[13.5px] font-semibold text-text">Bottleneck watch</h2>
            {loadingSmart && <span className="ml-auto text-[11px] text-text-tertiary">Hardware scan…</span>}
          </div>
          <div className="space-y-2">
            {loadingBottlenecks ? Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-16 w-full rounded-[var(--radius-control)]" />) : (
              bottlenecks.length ? bottlenecks.slice(0, 4).map((bn, i) => (
                <button
                  key={`${bn.type}-${i}`}
                  onClick={() => onNavigate?.(recTypeToPage[bn.type] ?? 'diagnostics')}
                  className="group w-full rounded-[var(--radius-control)] border border-border bg-surface-2/40 p-3 text-left transition-colors hover:border-red/40"
                >
                  <div className="flex items-center gap-2">
                    <Timer size={13} className={bn.severity === 'critical' || bn.severity === 'high' ? 'text-red' : 'text-yellow'} />
                    <span className="text-[12.5px] font-semibold capitalize text-text">{bn.type} bottleneck</span>
                    <Badge variant={bn.severity === 'critical' || bn.severity === 'high' ? 'danger' : 'warning'}>{bn.severity}</Badge>
                    <ChevronRight size={13} className="ml-auto text-text-tertiary transition-transform group-hover:translate-x-0.5" />
                  </div>
                  <p className="mt-1 text-[11.5px] leading-5 text-text-secondary">{bn.recommendation || bn.description}</p>
                </button>
              )) : (
                <div className="space-y-2">
                  {(smartDetect?.recommendations ?? []).slice(0, 3).map((rec, i) => (
                    <div key={`${rec.type}-${i}`} className="rounded-[var(--radius-control)] border border-border bg-surface-2/40 p-3 text-[11.5px] leading-5 text-text-secondary">
                      {rec.message}
                    </div>
                  ))}
                  {!smartDetect?.recommendations?.length && (
                    <div className="flex items-center gap-2 rounded-[var(--radius-control)] border border-green/25 bg-green-dim p-3 text-[12.5px] text-green">
                      <CheckCircle2 size={15} />
                      No obvious bottlenecks detected.
                    </div>
                  )}
                </div>
              )
            )}
          </div>
        </Card>
      </section>

      <Card padding="lg">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[
            { label: 'Processor', value: systemInfo.system.processor, title: systemInfo.system.processor },
            { label: 'Graphics', value: systemInfo.gpu.name || 'Not detected', title: systemInfo.gpu.name },
            { label: 'Storage', value: disk ? `${formatBytes(disk.used)} used of ${formatBytes(disk.total)}` : 'No disk data' },
            { label: 'Uptime', value: systemInfo.system.uptime },
          ].map((row) => (
            <div key={row.label} className="min-w-0">
              <div className="text-[10px] uppercase tracking-widest text-text-tertiary">{row.label}</div>
              <div className="mt-1 truncate text-[12.5px] text-text" title={row.title}>{row.value}</div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
