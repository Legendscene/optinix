import { useMemo, useState } from 'react'
import {
  Monitor, Thermometer, MemoryStick, Cpu, RotateCcw, RefreshCw, Zap, Maximize2, Minimize2,
  CircleAlert,
} from 'lucide-react'
import { Card } from '../ui/Card'
import { MetricCard } from '../ui/MetricCard'
import { ActionCard } from '../ui/ActionCard'
import { Skeleton } from '../ui/Skeleton'
import { Badge } from '../ui/Badge'
import { PageHero } from '../ui/PageHero'
import { RadialMeter } from '../ui/charts/RadialMeter'
import { HBars } from '../ui/charts/HBars'
import { StreamArea } from '../ui/charts/StreamArea'
import { ChartGhost } from '../ui/charts/ChartGhost'
import { useRollingSeries } from '../../hooks/useRollingSeries'
import { cn } from '../../lib/utils'
import { api } from '../../lib/api'
import type { SystemInfo } from '../../types'

const HISTORY = 45
/* Readings needed before the plot is drawn. Below this the panel shows its
   collecting state, which is designed rather than an empty rectangle. */
const COLLECTING_TARGET = 6

export function GpuPage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const [busy, setBusy] = useState<string | null>(null)
  const [result, setResult] = useState<{ ok: boolean; text: string } | null>(null)
  const [expanded, setExpanded] = useState(false)

  const gpu = systemInfo?.gpu
  const name = gpu?.name ?? 'Unknown GPU'
  const usage = gpu?.usage ?? 0
  const memTotal = gpu?.memory_total ?? 0
  const memUsed = gpu?.memory_used ?? 0
  const memPct = memTotal > 0 ? (memUsed / memTotal) * 100 : 0
  const temp = gpu?.temperature ?? 0
  const driver = gpu?.driver ?? '--'

  /* Real polled usage. The GPU counter can be absent on some drivers, in which
     case the series simply stays empty and the card says so. */
  const usageHistory = useRollingSeries(gpu?.usage ?? null, systemInfo, HISTORY)
  const series = useMemo(
    () => [{ key: 'gpu', label: 'GPU', color: 'var(--chart-2)', values: usageHistory }],
    [usageHistory],
  )

  const memBars = useMemo(
    () => [
      { key: 'used', label: 'Used', value: memUsed / 1024, color: 'var(--chart-2)' },
      { key: 'free', label: 'Free', value: Math.max(memTotal - memUsed, 0) / 1024, color: 'var(--color-surface-4)' },
    ],
    [memUsed, memTotal],
  )

  async function run(label: string, fn: () => Promise<unknown>, done: string) {
    setBusy(label)
    setResult(null)
    try {
      await fn()
      setResult({ ok: true, text: done })
    } catch (e) {
      setResult({ ok: false, text: e instanceof Error ? e.message : `${label} failed` })
    } finally {
      setBusy(null)
    }
  }

  function handleUpdateDriver() {
    const url = name.toLowerCase().includes('nvidia')
      ? 'https://www.nvidia.com/drivers'
      : 'https://www.amd.com/drivers'
    window.open(url, '_blank', 'noopener,noreferrer')
  }

  if (!systemInfo) {
    return (
      <div className="page space-y-5">
        <Skeleton className="h-[168px] w-full rounded-[var(--radius-card)]" />
        <div className="grid grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-28 rounded-[var(--radius-card)]" />)}
        </div>
        <div className="grid grid-cols-[1fr_340px] gap-4">
          <Skeleton className="h-56 rounded-[var(--radius-card)]" />
          <Skeleton className="h-56 rounded-[var(--radius-card)]" />
        </div>
      </div>
    )
  }

  const tempTone = temp > 80 ? 'bad' : temp > 65 ? 'warn' : 'good'

  return (
    <div className="page stagger-rise space-y-5">
      <PageHero
        eyebrow="Performance · Hardware"
        title="GPU"
        subtitle={name}
        icon={<Monitor size={19} />}
        badges={<Badge variant="info">Driver {driver}</Badge>}
        stats={[
          { label: 'Load', value: `${usage.toFixed(1)}%`, tone: usage > 90 ? 'warn' : 'accent', hint: 'engine utilisation' },
          { label: 'VRAM', value: `${memPct.toFixed(0)}%`, tone: memPct > 90 ? 'bad' : 'default', hint: `${(memUsed / 1024).toFixed(1)} of ${(memTotal / 1024).toFixed(1)} GB` },
          { label: 'Core temp', value: `${temp}°C`, tone: tempTone, hint: temp > 80 ? 'hot' : temp > 65 ? 'warm' : 'cool' },
          { label: 'Samples', value: `${usageHistory.length}`, hint: '4 s interval' },
        ]}
      />

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_308px]">
        <Card padding="lg">
          <div className="flex items-start justify-between gap-3 mb-1">
            <div>
              <h2 className="text-[13.5px] font-semibold text-text accent-rail">Engine load</h2>
              <p className="text-[11.5px] text-text-tertiary mt-0.5">
                Real GPU utilisation samples from the system poller.
              </p>
            </div>
            <Badge variant="info">{usageHistory.length >= COLLECTING_TARGET ? 'Recording' : 'Collecting'}</Badge>
          </div>
          {usageHistory.length >= COLLECTING_TARGET ? (
            <div className="mt-3">
              <StreamArea
                series={series}
                height={200}
                yMax={100}
                guides={[25, 50, 75]}
                ariaLabel={`GPU usage history, ${usageHistory.length} samples, latest ${usage.toFixed(1)} percent`}
              />
            </div>
          ) : (
            <div className="mt-3">
              <ChartGhost
                height={200}
                samples={usageHistory.length}
                target={COLLECTING_TARGET}
                title="Waiting for GPU counters"
                hint="Some drivers do not expose utilisation, in which case the plot stays empty rather than showing a guess."
              />
            </div>
          )}
        </Card>

        <Card padding="lg" className="flex flex-col items-center justify-center gap-4">
          <RadialMeter value={usage} label="Load" size={168} invert caption={`${temp}°C`} />
          <div className="w-full">
            <p className="text-[10.5px] font-semibold uppercase tracking-[0.06em] text-text-tertiary mb-2">
              VRAM allocation
            </p>
            <HBars
              data={memBars}
              max={memTotal > 0 ? memTotal / 1024 : 1}
              format={(v) => `${v.toFixed(1)} GB`}
              ariaLabel={`VRAM: ${(memUsed / 1024).toFixed(1)} GB used of ${(memTotal / 1024).toFixed(1)} GB`}
            />
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <MetricCard icon={<Monitor size={16} />} label="Usage" value={`${usage.toFixed(1)}%`} progress={usage} />
        <MetricCard
          icon={<Thermometer size={16} />}
          label="Temperature"
          value={`${temp}°C`}
          progress={Math.min(100, temp)}
          progressColor={temp > 80 ? 'var(--color-red)' : temp > 65 ? 'var(--color-yellow)' : 'var(--color-green)'}
          sub={temp > 80 ? 'Hot' : temp > 65 ? 'Warm' : 'Cool'}
        />
        <MetricCard
          icon={<MemoryStick size={16} />}
          label="VRAM"
          value={`${(memUsed / 1024).toFixed(1)}/${(memTotal / 1024).toFixed(1)} GB`}
          progress={memPct}
          sub={`${memPct.toFixed(0)}% utilized`}
        />
        <MetricCard icon={<Cpu size={16} />} label="Driver" value={driver.length > 18 ? `${driver.slice(0, 16)}…` : driver} sub="Version" />
      </div>

      <Card padding="lg">
        <button
          onClick={() => setExpanded(!expanded)}
          aria-expanded={expanded}
          className="flex w-full items-center justify-between gap-3 text-left"
        >
          <h2 className="text-[13.5px] font-semibold text-text accent-rail">Adapter details</h2>
          <span className="flex items-center gap-1.5 text-[11.5px] text-text-tertiary">
            {expanded ? 'Hide' : 'Show'}
            {expanded ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
          </span>
        </button>

        <dl className="mt-3 grid grid-cols-2 gap-x-6 gap-y-2.5 md:grid-cols-4">
          <div className="min-w-0">
            <dt className="text-[10.5px] uppercase tracking-[0.05em] text-text-tertiary">Name</dt>
            <dd className="text-[12.5px] text-text truncate" title={name}>{name}</dd>
          </div>
          <div>
            <dt className="text-[10.5px] uppercase tracking-[0.05em] text-text-tertiary">Driver</dt>
            <dd className="text-[12.5px] text-text tnum">{driver}</dd>
          </div>
          <div>
            <dt className="text-[10.5px] uppercase tracking-[0.05em] text-text-tertiary">VRAM</dt>
            <dd className="text-[12.5px] text-text tnum">{(memTotal / 1024).toFixed(1)} GB</dd>
          </div>
          <div>
            <dt className="text-[10.5px] uppercase tracking-[0.05em] text-text-tertiary">Thermals</dt>
            <dd className={cn('text-[12.5px] tnum', temp > 80 ? 'text-red' : temp > 65 ? 'text-yellow' : 'text-text')}>
              {temp}°C · {usage.toFixed(0)}% load
            </dd>
          </div>
        </dl>

        <div
          className={cn(
            'grid transition-[grid-template-rows,opacity] duration-300',
            expanded ? 'grid-rows-[1fr] opacity-100 mt-3' : 'grid-rows-[0fr] opacity-0',
          )}
        >
          <div className="overflow-hidden">
            <div className="border-t border-border pt-3 grid grid-cols-2 gap-x-6 gap-y-2 md:grid-cols-4">
              <Detail label="VRAM used" value={`${(memUsed / 1024).toFixed(2)} GB`} />
              <Detail label="VRAM free" value={`${(Math.max(memTotal - memUsed, 0) / 1024).toFixed(2)} GB`} />
              <Detail label="Allocation" value={`${memPct.toFixed(1)}%`} />
              <Detail label="Live samples" value={`${usageHistory.length}`} />
            </div>
          </div>
        </div>
      </Card>

      {result && (
        <div
          className={cn(
            'animate-rise flex items-start gap-2.5 rounded-[var(--radius-control)] border px-3.5 py-2.5 text-[12.5px]',
            result.ok ? 'border-green/30 bg-green-dim text-green' : 'border-red/30 bg-red-dim text-red',
          )}
        >
          {!result.ok && <CircleAlert size={15} className="shrink-0 mt-0.5" />}
          <span className="min-w-0 break-words">{result.text}</span>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <ActionCard
          icon={<Zap size={19} />}
          title="Optimize GPU"
          desc="Apply performance tweaks and optimal graphics settings"
          tags={['Performance']}
          loading={busy === 'optimize'}
          disabled={busy !== null && busy !== 'optimize'}
          onClick={() => run('optimize', () => api.gpuOptimize(), 'GPU optimization complete.')}
        />
        <ActionCard
          icon={<RotateCcw size={19} />}
          title="Reset GPU"
          desc="Reset graphics driver and restore default settings"
          variant="danger"
          tags={['Driver']}
          loading={busy === 'reset'}
          disabled={busy !== null && busy !== 'reset'}
          onClick={() => run('reset', () => api.tweakStateSet({ gpu_reset: true }), 'GPU reset complete.')}
        />
        <ActionCard
          icon={<RefreshCw size={19} />}
          title="Update Driver"
          desc="Check for and install the latest GPU driver version"
          tags={['Driver', 'Update']}
          onClick={handleUpdateDriver}
        />
      </div>
    </div>
  )
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[10.5px] uppercase tracking-[0.05em] text-text-tertiary">{label}</div>
      <div className="text-[12.5px] text-text tnum">{value}</div>
    </div>
  )
}
