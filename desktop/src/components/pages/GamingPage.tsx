import { useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import {
  Activity,
  BatteryCharging,
  CheckCircle2,
  Cpu,
  Crosshair,
  Gamepad2,
  Gauge,
  HardDrive,
  Joystick,
  Keyboard,
  MemoryStick,
  Monitor,
  MousePointer2,
  Network,
  RadioTower,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  Timer,
  Trash2,
  TriangleAlert,
  Wifi,
  Zap,
} from 'lucide-react'
import { ActionCard } from '../ui/ActionCard'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'
import { MetricCard } from '../ui/MetricCard'
import { Skeleton } from '../ui/Skeleton'
import { PageHero } from '../ui/PageHero'
import { StreamArea } from '../ui/charts/StreamArea'
import { Sparkline } from '../ui/charts/Sparkline'
import { cn, formatSpeed } from '../../lib/utils'
import type { SystemInfo } from '../../types'
import { api } from '../../lib/api'

type ToggleKey =
  | 'gameDvr'
  | 'gpuPriority'
  | 'visualEffects'
  | 'timerResolution'
  | 'coreParking'
  | 'qos'
  | 'defender'
  | 'windowsUpdate'
  | 'hpet'

const toggleApiMap: Partial<Record<ToggleKey, string>> = {
  gameDvr: 'game_dvr',
  gpuPriority: 'gpu_priority',
  visualEffects: 'visual_effects',
}

export function GamingPage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const [loadingAction, setLoadingAction] = useState<string | null>(null)
  const [result, setResult] = useState<{ key: string; message: string; success: boolean } | null>(null)
  const [profile, setProfile] = useState<'competitive' | 'streaming' | 'battery'>('competitive')
  const [toggles, setToggles] = useState<Record<ToggleKey, boolean>>({
    gameDvr: false,
    gpuPriority: true,
    visualEffects: true,
    timerResolution: false,
    coreParking: false,
    qos: false,
    defender: true,
    windowsUpdate: false,
    hpet: false,
  })

  /* Session model, unchanged: a projection the page labels as such. */
  const chartData = useMemo(() =>
    Array.from({ length: 32 }, (_, i) => ({
      tick: i,
      fps: Math.round(188 + i * 1.8 + Math.sin(i / 2) * 13),
      latency: Math.max(3, Math.round(17 - i * 0.25 + Math.cos(i / 3) * 2)),
      frametime: Math.max(4, Math.round(10 - i * 0.08 + Math.sin(i) * 1.4)),
    })), [])

  const runAction = async (key: string, fn: () => Promise<unknown>, successMsg: string) => {
    setLoadingAction(key)
    setResult(null)
    try {
      await fn()
      setResult({ key, message: successMsg, success: true })
    } catch (e) {
      setResult({ key, message: e instanceof Error ? e.message : 'Operation failed', success: false })
    } finally {
      setLoadingAction(null)
    }
  }

  const toggleSwitch = async (key: ToggleKey) => {
    const next = !toggles[key]
    setToggles((prev) => ({ ...prev, [key]: next }))
    try {
      if (key in toggleApiMap && toggleApiMap[key]) {
        await api.tweakStateSet({ [toggleApiMap[key] as string]: next })
        return
      }
      if (key === 'timerResolution') await (next ? api.gameModeTimerResolution(0.5) : api.gameModeTimerRestore())
      if (key === 'coreParking' && next) await api.gameModeCoreParking()
      if (key === 'qos') await (next ? api.networkPriorityQosEnable() : api.networkPriorityQosDisable())
      if (key === 'defender') await api.toggleDefender(next)
      if (key === 'windowsUpdate') await api.toggleWindowsUpdate(next)
      if (key === 'hpet' && next) await api.disableHpet()
    } catch {
      setToggles((prev) => ({ ...prev, [key]: !next }))
    }
  }

  if (!systemInfo) {
    return (
      <div className="page space-y-5">
        <Skeleton className="h-[190px] w-full rounded-[var(--radius-card)]" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Skeleton className="h-28 w-full rounded-[var(--radius-card)]" />
          <Skeleton className="h-28 w-full rounded-[var(--radius-card)]" />
          <Skeleton className="h-28 w-full rounded-[var(--radius-card)]" />
        </div>
        <Skeleton className="h-96 w-full rounded-[var(--radius-card)]" />
      </div>
    )
  }

  const readiness = Math.round((100 - systemInfo.cpu.percent) * 0.25 + (100 - systemInfo.memory.percent) * 0.2 + Math.max(0, 100 - systemInfo.gpu.usage) * 0.15 + 40)
  const gpuMemoryPercent = systemInfo.gpu.memory_total ? Math.round((systemInfo.gpu.memory_used / systemInfo.gpu.memory_total) * 100) : 0

  const profileCopy = {
    competitive: {
      label: 'Competitive',
      desc: 'Lowest latency, maximum foreground priority, overlays and background capture reduced.',
      tags: ['FPS', 'latency', 'raw input'],
    },
    streaming: {
      label: 'Streaming',
      desc: 'Keeps capture, audio, and GPU encoding stable while trimming unnecessary load.',
      tags: ['OBS', 'encoding', 'stability'],
    },
    battery: {
      label: 'Laptop Safe',
      desc: 'Performance lift without pushing thermals too hard on mobile hardware.',
      tags: ['temps', 'balanced', 'safe'],
    },
  }[profile]

  const actions = [
    { key: 'gaming', title: 'Full Gaming Optimization', desc: 'Applies the full gaming optimizer stack.', icon: <Zap className="w-5 h-5" />, tags: ['recommended', 'one click'], fn: () => api.optimize('gaming'), msg: 'Gaming optimization applied' },
    { key: 'game-mode', title: 'Activate Game Mode', desc: 'Raises foreground game priority and trims background pressure.', icon: <Gamepad2 className="w-5 h-5" />, tags: ['priority'], fn: () => api.gameModeEnable(), msg: 'Game Mode activated' },
    { key: 'affinity', title: 'CPU Affinity Tuner', desc: 'Pins game workloads to the strongest available CPU path.', icon: <Cpu className="w-5 h-5" />, tags: ['cpu', 'stutter'], fn: () => api.affinityOptimize(), msg: 'CPU affinity tuned' },
    { key: 'gpu', title: 'GPU Performance Path', desc: 'Applies graphics scheduling and driver performance preferences.', icon: <Monitor className="w-5 h-5" />, tags: ['gpu'], fn: () => api.gpuOptimize(), msg: 'GPU optimization applied' },
    { key: 'memory', title: 'Standby RAM Cleaner', desc: 'Frees standby memory before launching a match.', icon: <MemoryStick className="w-5 h-5" />, tags: ['ram'], fn: () => api.memoryFree(), msg: 'Memory cleaned' },
    { key: 'network', title: 'Low Ping Network', desc: 'Tunes adapter and TCP settings for smoother packets.', icon: <Network className="w-5 h-5" />, tags: ['ping'], fn: () => api.advancedNetwork(), msg: 'Network tuned for low latency' },
    { key: 'bufferbloat', title: 'Bufferbloat Preset', desc: 'Applies gaming queue controls to reduce ping spikes.', icon: <RadioTower className="w-5 h-5" />, tags: ['jitter'], fn: () => api.networkPriorityBufferbloatApply('gaming'), msg: 'Gaming bufferbloat preset applied' },
    { key: 'dns', title: 'Fast DNS', desc: 'Switches DNS to a fast gaming-friendly resolver.', icon: <Wifi className="w-5 h-5" />, tags: ['dns'], fn: () => api.dns('cloudflare'), msg: 'DNS optimized' },
    { key: 'peripheral', title: 'Raw Input Setup', desc: 'Disables mouse acceleration and tightens device response.', icon: <MousePointer2 className="w-5 h-5" />, tags: ['mouse'], fn: () => api.peripheralOptimize(), msg: 'Peripheral response optimized' },
    { key: 'power', title: 'Ultimate Power Plan', desc: 'Applies a high-performance power profile for gaming.', icon: <BatteryCharging className="w-5 h-5" />, tags: ['power'], fn: () => api.setPowerPlan('ultimate'), msg: 'Power plan applied' },
    { key: 'cleanup', title: 'Shader / Temp Cleanup', desc: 'Clears temp files that can slow launches and patches.', icon: <Trash2 className="w-5 h-5" />, tags: ['cleanup'], fn: () => api.diskCleanAll(), msg: 'Temp cache cleaned' },
    { key: 'restore', title: 'Rollback Snapshot', desc: 'Creates a restore snapshot before advanced tweaks.', icon: <RotateCcw className="w-5 h-5" />, tags: ['safety'], fn: () => api.rollbackCreateSnapshot(), msg: 'Rollback snapshot created' },
  ]

  const togglesList: { key: ToggleKey; label: string; desc: string; icon: React.ReactNode; caution?: boolean }[] = [
    { key: 'gameDvr', label: 'Game DVR / capture off', desc: 'Stops background recording overhead when you are not clipping.', icon: <Joystick size={16} /> },
    { key: 'gpuPriority', label: 'GPU hardware priority', desc: 'Lets the game path receive a stronger GPU scheduling preference.', icon: <Monitor size={16} /> },
    { key: 'visualEffects', label: 'Lean Windows visuals', desc: 'Reduces transparency, animations, and desktop effects.', icon: <Sparkles size={16} /> },
    { key: 'timerResolution', label: '0.5 ms timer resolution', desc: 'Improves timing consistency while active.', icon: <Timer size={16} />, caution: true },
    { key: 'coreParking', label: 'Unpark CPU cores', desc: 'Keeps CPU cores awake for frame pacing under load.', icon: <Cpu size={16} />, caution: true },
    { key: 'qos', label: 'Gaming QoS policy', desc: 'Prioritizes game traffic over low-priority background transfers.', icon: <RadioTower size={16} /> },
    { key: 'defender', label: 'Defender enabled', desc: 'Keep protection on unless troubleshooting a known false positive.', icon: <ShieldCheck size={16} /> },
    { key: 'windowsUpdate', label: 'Windows Update enabled', desc: 'Turn off during sessions if updates interrupt matches.', icon: <Activity size={16} />, caution: true },
    { key: 'hpet', label: 'Disable HPET', desc: 'Advanced timer tweak; use only if your rig benefits from it.', icon: <Gauge size={16} />, caution: true },
  ]

  const checklist = [
    { label: 'Rollback snapshot created', ok: result?.key === 'restore' && result.success },
    { label: 'Game Mode available', ok: true },
    { label: 'GPU priority configured', ok: toggles.gpuPriority },
    { label: 'Capture overhead reduced', ok: !toggles.gameDvr },
    { label: 'Network priority ready', ok: toggles.qos },
    { label: 'Security protection visible', ok: toggles.defender },
  ]

  return (
    <div className="page stagger-rise space-y-5">
      <PageHero
        eyebrow="Gaming lab"
        title="FPS, latency and input control"
        subtitle={profileCopy.desc}
        icon={<Crosshair size={19} />}
        badges={
          <>
            <Badge variant="success">Gaming Lab</Badge>
            <Badge variant="accent">{profileCopy.label}</Badge>
            <span className="text-[11px] text-text-tertiary">
              GPU {systemInfo.gpu.usage}% · RAM {systemInfo.memory.percent}%
            </span>
          </>
        }
        stats={[
          { label: 'Readiness', value: `${readiness}%`, tone: 'accent', hint: 'profile fit' },
          { label: 'Input goal', value: '< 5 ms', hint: 'raw input' },
          { label: 'Net down', value: formatSpeed(systemInfo.network.speed_down), hint: 'current link' },
          { label: 'VRAM load', value: `${gpuMemoryPercent}%`, tone: gpuMemoryPercent > 90 ? 'bad' : 'default', hint: 'of total' },
        ]}
        actions={
          <div className="flex flex-wrap gap-2">
            {(['competitive', 'streaming', 'battery'] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => setProfile(mode)}
                aria-pressed={profile === mode}
                className={cn(
                  'rounded-[var(--radius-control)] border px-3 py-1.5 text-[11.5px] font-semibold transition-colors',
                  profile === mode
                    ? 'border-accent/45 bg-accent-dim text-accent'
                    : 'border-border bg-surface-2/55 text-text-secondary hover:text-text',
                )}
              >
                {mode === 'competitive' ? 'Competitive' : mode === 'streaming' ? 'Streaming' : 'Laptop Safe'}
              </button>
            ))}
            <div className="flex flex-wrap items-center gap-1.5 ml-1">
              {profileCopy.tags.map((tag) => (
                <span key={tag} className="rounded border border-border bg-surface-3/70 px-2 py-0.5 text-[10px] uppercase tracking-wider text-text-tertiary">{tag}</span>
              ))}
            </div>
          </div>
        }
      />

      {result && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className={cn('rounded-[var(--radius-control)] border px-4 py-3', result.success ? 'bg-green-dim border-green/30' : 'bg-red-dim border-red/30')}
        >
          <div className="flex items-center gap-3">
            {result.success ? <CheckCircle2 className="w-4 h-4 text-green" /> : <TriangleAlert className="w-4 h-4 text-red" />}
            <p className={cn('text-[12.5px] font-medium', result.success ? 'text-green' : 'text-red')}>{result.message}</p>
          </div>
        </motion.div>
      )}

      <section className="grid grid-cols-1 xl:grid-cols-[minmax(0,1.3fr)_minmax(0,0.7fr)] gap-4">
        <Card padding="lg">
          <div className="flex items-center gap-2 mb-3">
            <Crosshair size={17} className="text-accent" />
            <h2 className="text-[13.5px] font-semibold text-text">Session model</h2>
            <Badge variant="info">Stable frames</Badge>
            <span className="ml-auto text-[10px] uppercase tracking-widest text-text-tertiary">projection</span>
          </div>

          <StreamArea
            series={[{ key: 'fps', label: 'FPS', color: 'var(--chart-1)', values: chartData.map((d) => d.fps) }]}
            height={172}
            unit=" fps"
            ariaLabel="Projected frame rate for the selected profile"
          />

          <div className="mt-3 grid grid-cols-2 gap-3">
            <div className="rounded-[var(--radius-control)] border border-border bg-surface-2/40 p-2.5">
              <div className="flex items-center justify-between">
                <span className="text-[10.5px] uppercase tracking-[0.05em] text-text-tertiary">Latency</span>
                <span className="text-[11.5px] font-medium text-text tnum">{chartData[chartData.length - 1].latency} ms</span>
              </div>
              <Sparkline values={chartData.map((d) => d.latency)} width={160} height={26} stroke="var(--chart-4)" ariaLabel="Projected latency" />
            </div>
            <div className="rounded-[var(--radius-control)] border border-border bg-surface-2/40 p-2.5">
              <div className="flex items-center justify-between">
                <span className="text-[10.5px] uppercase tracking-[0.05em] text-text-tertiary">Frame time</span>
                <span className="text-[11.5px] font-medium text-text tnum">{chartData[chartData.length - 1].frametime} ms</span>
              </div>
              <Sparkline values={chartData.map((d) => d.frametime)} width={160} height={26} stroke="var(--chart-2)" ariaLabel="Projected frame time" />
            </div>
          </div>
        </Card>

        <Card padding="lg" className="flex flex-col">
          <div className="mb-4 flex items-center gap-2">
            <HardDrive size={17} className="text-cyan" />
            <h2 className="text-[13.5px] font-semibold text-text">Launch checklist</h2>
          </div>
          <div className="flex-1 space-y-2.5">
            {checklist.map((row) => (
              <div key={row.label} className="flex items-center gap-3 rounded-[var(--radius-control)] border border-border bg-surface-2/40 p-2.5">
                <span className={cn('h-2.5 w-2.5 rounded-full shrink-0', row.ok ? 'bg-green' : 'bg-surface-4')} />
                <span className="text-[12px] text-text-secondary">{row.label}</span>
              </div>
            ))}
          </div>
          <Button
            variant="primary"
            size="lg"
            icon={<Gamepad2 size={17} />}
            loading={loadingAction === 'gaming'}
            onClick={() => runAction('gaming', () => api.optimize('gaming'), 'Gaming optimization applied')}
            className="mt-4 w-full justify-center"
          >
            Prime for match
          </Button>
        </Card>
      </section>

      <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard
          icon={<Cpu size={16} />}
          label="CPU headroom"
          value={`${100 - systemInfo.cpu.percent}%`}
          progress={100 - systemInfo.cpu.percent}
          progressColor="var(--chart-1)"
        />
        <MetricCard
          icon={<Monitor size={16} />}
          label="GPU headroom"
          value={`${100 - systemInfo.gpu.usage}%`}
          progress={100 - systemInfo.gpu.usage}
          progressColor="var(--chart-2)"
        />
        <MetricCard
          icon={<MemoryStick size={16} />}
          label="RAM available"
          value={`${systemInfo.memory.available_gb.toFixed(1)} GB`}
          progress={100 - systemInfo.memory.percent}
          progressColor="var(--chart-3)"
        />
      </section>

      <section>
        <div className="mb-3 flex items-center gap-2">
          <Zap size={16} className="text-accent" />
          <h2 className="text-[13.5px] font-semibold text-text">Gaming optimization arsenal</h2>
          <span className="text-[11px] text-text-tertiary">FPS, latency, network, power, input, cleanup, and recovery</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          {actions.map((action) => (
            <ActionCard
              key={action.key}
              icon={action.icon}
              title={action.title}
              desc={action.desc}
              tags={action.tags}
              loading={loadingAction === action.key}
              disabled={Boolean(loadingAction)}
              variant={action.key === 'restore' ? 'success' : action.key === 'hpet' ? 'danger' : 'default'}
              onClick={() => !loadingAction && runAction(action.key, action.fn, action.msg)}
            />
          ))}
        </div>
      </section>

      <Card padding="lg">
        <div className="mb-4 flex items-center gap-2">
          <Keyboard size={17} className="text-accent" />
          <h2 className="text-[13.5px] font-semibold text-text">Session toggles</h2>
          <span className="ml-auto text-[11px] text-text-tertiary">applied immediately</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {togglesList.map((t) => (
            <button
              key={t.key}
              onClick={() => toggleSwitch(t.key)}
              aria-pressed={toggles[t.key]}
              className={cn(
                'card-depth rounded-[var(--radius-control)] border p-3 text-left transition-colors',
                toggles[t.key]
                  ? 'border-accent/35 bg-accent-dim'
                  : 'border-border bg-surface-2/40 hover:border-border-light',
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <div className={toggles[t.key] ? 'text-accent' : 'text-text-secondary'}>{t.icon}</div>
                <span className={cn('relative h-5 w-10 rounded-full transition-colors', toggles[t.key] ? 'bg-accent' : 'bg-surface-4')}>
                  <motion.span
                    animate={{ x: toggles[t.key] ? 20 : 2 }}
                    transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                    className="absolute top-0.5 h-4 w-4 rounded-full bg-surface-0 shadow"
                  />
                </span>
              </div>
              <div className="mt-3 flex items-center gap-2">
                <p className="text-[12.5px] font-semibold text-text">{t.label}</p>
                {t.caution && <TriangleAlert size={12} className="text-yellow" />}
              </div>
              <p className="mt-1 text-[11.5px] leading-5 text-text-secondary">{t.desc}</p>
            </button>
          ))}
        </div>
      </Card>
    </div>
  )
}
