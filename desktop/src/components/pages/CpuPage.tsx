import { useMemo, useState } from 'react'
import { Cpu, Thermometer, Layers, Hash, Zap, Gauge, Battery, CircleAlert } from 'lucide-react'
import { Card } from '../ui/Card'
import { MetricCard } from '../ui/MetricCard'
import { ActionCard } from '../ui/ActionCard'
import { Skeleton } from '../ui/Skeleton'
import { Badge } from '../ui/Badge'
import { PageHero } from '../ui/PageHero'
import { RadialMeter } from '../ui/charts/RadialMeter'
import { StreamArea } from '../ui/charts/StreamArea'
import { ChartGhost } from '../ui/charts/ChartGhost'
import { useRollingSeries } from '../../hooks/useRollingSeries'
import { api } from '../../lib/api'
import type { SystemInfo } from '../../types'

const HISTORY = 45
/* Readings needed before the plot is drawn. Below this the panel shows its
   collecting state, which is designed rather than an empty rectangle. */
const COLLECTING_TARGET = 6

export function CpuPage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const [busy, setBusy] = useState<string | null>(null)
  const [notice, setNotice] = useState<{ ok: boolean; text: string } | null>(null)

  const cpu = systemInfo?.cpu
  const percent = cpu?.percent ?? 0
  const temp = cpu?.temperature
  const threads = cpu?.logical ?? 0
  const cores = cpu?.physical ?? 0

  /* Real samples from the shared snapshot, not a generated walk. The chart is
     labelled "Live" only because every point on it was actually measured. */
  const history = useRollingSeries(cpu?.percent ?? null, systemInfo, HISTORY)

  const series = useMemo(
    () => [{ key: 'cpu', label: 'CPU', color: 'var(--chart-1)', values: history }],
    [history],
  )

  async function run(label: string, fn: () => Promise<unknown>, done: string) {
    setBusy(label)
    setNotice(null)
    try {
      await fn()
      setNotice({ ok: true, text: done })
    } catch (e) {
      setNotice({ ok: false, text: e instanceof Error ? e.message : `${label} failed` })
    } finally {
      setBusy(null)
    }
  }

  if (!systemInfo) {
    return (
      <div className="page space-y-5">
        <Skeleton className="h-[168px] w-full rounded-[var(--radius-card)]" />
        <div className="grid grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-28 rounded-[var(--radius-card)]" />)}
        </div>
        <Skeleton className="h-72 rounded-[var(--radius-card)]" />
      </div>
    )
  }

  const tempTone = temp == null ? ('default' as const) : temp > 80 ? ('bad' as const) : temp > 60 ? ('warn' as const) : ('good' as const)

  return (
    <div className="page stagger-rise space-y-5">
      <PageHero
        eyebrow="Performance · Hardware"
        title="CPU"
        subtitle="Live processor telemetry, thermal headroom and one-click tuning for the part that decides your frame pacing."
        icon={<Cpu size={19} />}
        badges={<Badge variant="success">Live</Badge>}
        stats={[
          { label: 'Usage', value: `${percent.toFixed(1)}%`, tone: percent > 80 ? 'bad' : percent > 55 ? 'warn' : 'good', hint: 'right now' },
          { label: 'Package', value: temp != null ? `${temp}°C` : '—', tone: tempTone === 'default' ? 'default' : tempTone, hint: temp != null ? (temp > 80 ? 'critical' : temp > 60 ? 'warm' : 'normal') : 'no sensor' },
          { label: 'Cores', value: `${cores}`, hint: `${threads} threads` },
          { label: 'Samples', value: `${history.length}`, hint: '4 s interval' },
        ]}
      />

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_308px]">
        <Card padding="lg">
          <div className="flex items-start justify-between gap-3 mb-1">
            <div>
              <h2 className="text-[13.5px] font-semibold text-text accent-rail">Usage history</h2>
              <p className="text-[11.5px] text-text-tertiary mt-0.5">
                Each point is a real reading from the system poller.
              </p>
            </div>
            <Badge variant="info">{history.length >= COLLECTING_TARGET ? 'Recording' : 'Collecting'}</Badge>
          </div>

          {history.length >= COLLECTING_TARGET ? (
            <div className="mt-3">
              <StreamArea
                series={series}
                height={228}
                yMax={100}
                guides={[25, 50, 75]}
                showHead
                ariaLabel={`CPU usage history, ${history.length} samples, latest ${percent.toFixed(1)} percent`}
              />
            </div>
          ) : (
            <div className="mt-3">
              <ChartGhost
                height={228}
                samples={history.length}
                target={COLLECTING_TARGET}
                title="Collecting CPU samples"
                hint="One poll every 4 seconds. The plot appears once six readings have landed — nothing here is simulated."
              />
            </div>
          )}
        </Card>

        <Card padding="lg" className="flex flex-col items-center justify-center gap-4">
          <RadialMeter value={percent} label="Load" size={168} invert caption={temp != null ? `${temp}°C package` : undefined} />
          <div className="w-full space-y-2 pt-1">
            <div className="flex items-center justify-between text-[11.5px]">
              <span className="text-text-tertiary">Threads</span>
              <span className="text-text tnum font-medium">{threads}</span>
            </div>
            <div className="flex items-center justify-between text-[11.5px]">
              <span className="text-text-tertiary">Physical cores</span>
              <span className="text-text tnum font-medium">{cores}</span>
            </div>
            <div className="flex items-center justify-between text-[11.5px]">
              <span className="text-text-tertiary">Thermal state</span>
              <span className={temp == null ? 'text-text-tertiary' : temp > 80 ? 'text-red' : temp > 60 ? 'text-yellow' : 'text-green'}>
                {temp == null ? 'unavailable' : temp > 80 ? 'critical' : temp > 60 ? 'warm' : 'normal'}
              </span>
            </div>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <MetricCard icon={<Cpu size={16} />} label="Usage" value={`${percent.toFixed(1)}%`} progress={percent} />
        <MetricCard
          icon={<Thermometer size={16} />}
          label="Temperature"
          value={temp != null ? `${temp}°C` : '--'}
          sub={temp != null ? (temp > 80 ? 'Critical' : temp > 60 ? 'Warm' : 'Normal') : 'No sensor reported'}
        />
        <MetricCard icon={<Layers size={16} />} label="Threads" value={`${threads}`} sub={`${cores} physical cores`} />
        <MetricCard icon={<Hash size={16} />} label="Samples collected" value={`${history.length}`} sub="since this page opened" />
      </div>

      {notice && (
        <div
          className={`animate-rise flex items-start gap-2.5 rounded-[var(--radius-control)] border px-3.5 py-2.5 text-[12.5px] ${
            notice.ok ? 'border-green/30 bg-green-dim text-green' : 'border-red/30 bg-red-dim text-red'
          }`}
        >
          {!notice.ok && <CircleAlert size={15} className="shrink-0 mt-0.5" />}
          <span className="min-w-0 break-words">{notice.text}</span>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <ActionCard
          icon={<Zap size={19} />}
          title="Core Parking"
          desc="Toggle core parking to balance power efficiency and performance"
          tags={['Power', 'Performance']}
          loading={busy === 'Core Parking'}
          disabled={busy !== null && busy !== 'Core Parking'}
          onClick={() => run('Core Parking', () => api.optimize('cpu'), 'CPU optimization applied.')}
        />
        <ActionCard
          icon={<Gauge size={19} />}
          title="Priority Boost"
          desc="Adjust process priority settings for foreground applications"
          tags={['Performance', 'Latency']}
          loading={busy === 'Priority Boost'}
          disabled={busy !== null && busy !== 'Priority Boost'}
          onClick={() => run('Priority Boost', () => api.affinityOptimize(), 'Affinity priorities tuned.')}
        />
        <ActionCard
          icon={<Battery size={19} />}
          title="Power Plan"
          desc="Switch between power plans for optimal CPU performance"
          tags={['Balanced', 'High Perf.']}
          loading={busy === 'Power Plan'}
          disabled={busy !== null && busy !== 'Power Plan'}
          onClick={() => run('Power Plan', () => api.setPowerPlan('ultimate'), 'Ultimate power plan applied.')}
        />
      </div>
    </div>
  )
}
