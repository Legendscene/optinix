import { useState, useEffect, useRef, useCallback } from 'react'
import { motion } from 'framer-motion'
import { Activity, Cpu, MemoryStick as MemoryIcon, Monitor, Wifi, HardDrive, Thermometer, Gauge, Play, Square, Clock, CircleAlert, RefreshCw } from 'lucide-react'
import { Card } from '../ui/Card'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { PageHero } from '../ui/PageHero'
import { ProgressBar } from '../ui/ProgressBar'
import { Skeleton } from '../ui/Skeleton'
import { Sparkline } from '../ui/charts/Sparkline'
import { StreamArea } from '../ui/charts/StreamArea'
import { api } from '../../lib/api'
import { formatChartTick } from '../../lib/utils'
import type { SystemInfo, MonitorMetrics } from '../../types'

interface DataPoint {
  ts: number
  cpu: number
  ram: number
  gpu: number | null
  disk: number
}

/* Chart colours follow the theme tokens so the monitor matches the rest of
   the app in every accent theme, instead of pinning the old fixed hexes. */
const COLORS = {
  cpu: 'var(--chart-1)',
  ram: 'var(--chart-2)',
  gpu: 'var(--color-violet)',
  disk: 'var(--chart-3)',
}

const containerVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.06 } },
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { type: 'spring' as const, stiffness: 260, damping: 24 } },
}

const periods = [
  { key: '1h', label: '1H' },
  { key: '24h', label: '24H' },
  { key: '7d', label: '7D' },
]

export function LiveMonitorPage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const [running, setRunning] = useState(false)
  const [data, setData] = useState<DataPoint[]>([])
  const [current, setCurrent] = useState<MonitorMetrics | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdated, setLastUpdated] = useState<number | null>(null)
  // Wall-clock sample used only to re-render the "Last updated" counter. It
  // must advance independently of the fetch interval: background tabs throttle
  // timers, so if the counter were derived at fetch-time a stale tab would keep
  // showing a small, reassuring "Ns ago" while the data was minutes old.
  const [now, setNow] = useState(() => Date.now())
  const [loading, setLoading] = useState(true)
  const [historyPeriod, setHistoryPeriod] = useState('1h')
  const [historyData, setHistoryData] = useState<{ timestamp: number; value: number }[]>([])
  const [historyCategory, setHistoryCategory] = useState('cpu')
  const [historyLoading, setHistoryLoading] = useState(false)
  const runningRef = useRef(false)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchCurrent = useCallback(async () => {
    try {
      const m = await api.monitorCurrent()
      setCurrent(m)
      setError(null)
      const receivedAt = Date.now()
      setLastUpdated(receivedAt)
      setData(prev => {
        // While paused, a fresh sample still updates the cards, but appending
        // a live chart point would draw a misleading line as if sampling
        // continued. Only append while the monitor is running.
        if (!runningRef.current) return prev
        // The snapshot carries no timestamp; the sample's real time is when
        // this client received it, so label the point with receipt time.
        const point: DataPoint = {
          ts: receivedAt,
          cpu: m.cpu,
          ram: m.ram,
          gpu: m.gpu,
          disk: m.disk_usage_percent,
        }
        const next = [...prev, point]
        return next.length > 120 ? next.slice(next.length - 120) : next
      })
      setLoading(false)
    } catch (e) {
      setError((e as Error).message)
      setLoading(false)
    }
  }, [])

  const fetchHistory = useCallback(async (category: string, period: string) => {
    setHistoryLoading(true)
    try {
      const res = await api.monitorHistory(category, period)
      // Backend stores epoch seconds; new Date() needs ms, so scale up. Guard
      // against malformed points so one bad sample can't poison the axis.
      const pts = (res.entries ?? [])
        .filter((p) => typeof p?.timestamp === 'number' && typeof p?.value === 'number')
        .map((p) => ({ timestamp: p.timestamp * 1000, value: p.value }))
      setHistoryData(pts)
    } catch {
      setHistoryData([])
    }
    setHistoryLoading(false)
  }, [])

  const startMonitor = useCallback(async () => {
    try { await api.monitorStart() } catch { }
    runningRef.current = true
    setRunning(true)
    fetchCurrent()
    intervalRef.current = setInterval(fetchCurrent, 3000)
  }, [fetchCurrent])

  const stopMonitor = useCallback(async () => {
    try { await api.monitorStop() } catch { }
    runningRef.current = false
    setRunning(false)
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }, [])

  useEffect(() => {
    fetchCurrent()
    // Background tabs throttle timers to ~1/min, so the 3s interval freezes
    // silently and the chart just stops advancing. On returning to the
    // foreground, take one immediate sample and restart the interval.
    const onVis = () => {
      if (document.hidden || !runningRef.current) return
      fetchCurrent()
      if (intervalRef.current) clearInterval(intervalRef.current)
      intervalRef.current = setInterval(fetchCurrent, 3000)
    }
    document.addEventListener('visibilitychange', onVis)
    return () => {
      document.removeEventListener('visibilitychange', onVis)
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [fetchCurrent])

  /* Advance the "Last updated" staleness counter on wall-clock time. Kept
     separate from the fetch interval so a background-tab timer throttle slows
     sampling but never freezes the counter — staleness stays truthful. */
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    fetchHistory(historyCategory, historyPeriod)
  }, [historyCategory, historyPeriod, fetchHistory])

  /* Auto-start once, on the first system snapshot. Keyed on a ref rather than
     `running`: depending on `running` made every poll restart the monitor
     right after the user pressed Stop, so the control could never stop it. */
  const autoStarted = useRef(false)
  useEffect(() => {
    if (systemInfo && !autoStarted.current) {
      autoStarted.current = true
      startMonitor()
    }
  }, [systemInfo, startMonitor])

  const toggleMonitor = () => {
    if (running) stopMonitor()
    else startMonitor()
  }

  const historyChartData = historyData.map(p => ({ ts: p.timestamp, value: p.value }))

  const secondsAgo = lastUpdated ? Math.max(0, Math.floor((now - lastUpdated) / 1000)) : null

  if (loading && !current) {
    return (
      <div className="page space-y-6">
        <div className="flex items-center justify-between">
          <div><Skeleton className="h-8 w-40 mb-1" /><Skeleton className="h-4 w-56" /></div>
          <Skeleton className="h-9 w-28 rounded-lg" />
        </div>
        <div className="grid grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-32 rounded-xl" />)}
        </div>
        <Skeleton className="h-72 rounded-xl" />
        <div className="grid grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-28 rounded-xl" />)}
        </div>
      </div>
    )
  }

  if (error && !current) {
    return (
      <div className="page space-y-6">
        <div>
          <h1 className="page-title text-text flex items-center gap-3">
            <Activity className="text-accent" size={28} />
            Live Monitor
          </h1>
          <p className="page-subtitle mt-1">Real-time system performance monitoring</p>
        </div>
        <div className="surface-card p-5 flex items-start gap-3">
          <CircleAlert size={18} className="text-red shrink-0 mt-0.5" />
          <div>
            <h2 className="text-[15px] font-medium">Could not reach the Optinix service</h2>
            <p className="text-[12.5px] text-text-secondary mt-1">{error}</p>
            <p className="text-[12px] text-text-tertiary mt-2">
              The backend runs on 127.0.0.1:5420. Metrics stay blank until it responds —
              Optinix never fills them with placeholder values.
            </p>
            <button
              onClick={() => { setLoading(true); fetchCurrent() }}
              className="mt-3 inline-flex items-center gap-1.5 h-8 px-3 rounded-lg bg-surface-3
                hover:bg-surface-4 text-[12.5px] text-text transition-colors"
            >
              <RefreshCw size={13} /> Try again
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <motion.div variants={containerVariants} initial="hidden" animate="show" className="page space-y-6">
      <motion.div variants={itemVariants}>
        <PageHero
          eyebrow="Monitoring · Telemetry"
          title="Live Monitor"
          subtitle="Real-time system performance, sampled from this machine and charted as it arrives."
          icon={<Activity size={19} />}
          badges={
            <>
              <Badge variant={running ? 'success' : 'info'}>{running ? 'Recording' : 'Idle'}</Badge>
              {secondsAgo != null && (
                <Badge>Updated {secondsAgo}s ago</Badge>
              )}
            </>
          }
          stats={[
            { label: 'CPU', value: current ? `${Math.round(current.cpu)}%` : '--', tone: 'accent' },
            {
              label: 'RAM',
              value: current ? `${current.ram_used_gb.toFixed(1)} GB` : '--',
              hint: current ? `of ${current.ram_total_gb.toFixed(0)} GB` : 'no sample yet',
            },
            {
              label: 'GPU',
              value: current?.gpu != null ? `${Math.round(current.gpu)}%` : '--',
              hint: current?.gpu_temp != null ? `${current.gpu_temp}°C` : 'no sensor',
            },
            {
              label: 'Disk',
              value: current ? `${Math.round(current.disk_usage_percent)}%` : '--',
              hint: current ? `${current.disk_read_mbs.toFixed(0)} / ${current.disk_write_mbs.toFixed(0)} MB/s` : undefined,
            },
          ]}
          actions={
            <Button
              variant={running ? 'danger' : 'primary'}
              size="md"
              icon={running ? <Square size={16} /> : <Play size={16} />}
              onClick={toggleMonitor}
            >
              {running ? 'Stop' : 'Start'}
            </Button>
          }
        />
      </motion.div>

      <motion.div variants={itemVariants} className="grid grid-cols-4 gap-4">
        <Card padding="md" tilt>
          <div className="flex items-center gap-2 mb-2">
            <Cpu size={16} style={{ color: COLORS.cpu }} />
            <span className="text-xs text-text-secondary">CPU</span>
          </div>
          <div className="text-2xl font-semibold text-text">{current?.cpu != null ? `${current.cpu}%` : '--'}</div>
          {current?.cpu != null && <ProgressBar value={current.cpu} color={COLORS.cpu} size="sm" className="mt-2" />}
          {data.filter(d => d.cpu != null).length >= 2 ? (
            <div className="h-8 mt-2">
              <Sparkline
                values={data.slice(-30).map(d => d.cpu)}
                width={200} height={32} stroke={COLORS.cpu}
                className="w-full" ariaLabel="CPU trend"
              />
            </div>
          ) : (
            <div className="h-8 mt-2 flex items-center text-[10px] text-text-tertiary">
              {running ? 'Collecting samples…' : 'Start the monitor to record a trend'}
            </div>
          )}
        </Card>

        <Card padding="md" tilt>
          <div className="flex items-center gap-2 mb-2">
            <MemoryIcon size={16} style={{ color: COLORS.ram }} />
            <span className="text-xs text-text-secondary">RAM</span>
          </div>
          <div className="text-2xl font-semibold text-text">
            {current?.ram_used_gb != null ? current.ram_used_gb.toFixed(1) : '--'}
            <span className="text-sm text-text-tertiary font-normal"> / {current?.ram_total_gb != null ? `${current.ram_total_gb.toFixed(0)} GB` : '? GB'}</span>
          </div>
          {current?.ram != null && <ProgressBar value={current.ram} color={COLORS.ram} size="sm" className="mt-2" />}
          {data.filter(d => d.ram != null).length >= 2 ? (
            <div className="h-8 mt-2">
              <Sparkline
                values={data.slice(-30).map(d => d.ram)}
                width={200} height={32} stroke={COLORS.ram}
                className="w-full" ariaLabel="RAM trend"
              />
            </div>
          ) : (
            <div className="h-8 mt-2 flex items-center text-[10px] text-text-tertiary">
              {running ? 'Collecting samples…' : 'Start the monitor to record a trend'}
            </div>
          )}
        </Card>

        <Card padding="md" tilt>
          <div className="flex items-center gap-2 mb-2">
            <Monitor size={16} style={{ color: COLORS.gpu }} />
            <span className="text-xs text-text-secondary">GPU</span>
          </div>
          <div className="text-2xl font-semibold text-text">{current?.gpu != null ? `${current.gpu}%` : '--'}</div>
          {current?.gpu != null && <ProgressBar value={current.gpu} color={COLORS.gpu} size="sm" className="mt-2" />}
          <div className="flex items-center gap-2 mt-2 text-[11px] text-text-tertiary">
            <Thermometer size={12} />
            {current?.gpu_temp != null ? `${current.gpu_temp}°C` : '--'}
            {current?.gpu_memory_used != null && (
              <span className="ml-auto">{current.gpu_memory_used}GB VRAM</span>
            )}
          </div>
        </Card>

        <Card padding="md" tilt>
          <div className="flex items-center gap-2 mb-2">
            <HardDrive size={16} style={{ color: COLORS.disk }} />
            <span className="text-xs text-text-secondary">Disk</span>
          </div>
          <div className="text-2xl font-semibold text-text">{current?.disk_usage_percent != null ? `${current.disk_usage_percent}%` : '--'}</div>
          {current?.disk_usage_percent != null && <ProgressBar value={current.disk_usage_percent} color={COLORS.disk} size="sm" className="mt-2" />}
          <div className="flex items-center gap-2 mt-2 text-[11px] text-text-tertiary">
            <span>&darr; {current?.disk_read_mbs != null ? `${current.disk_read_mbs.toFixed(1)} MB/s` : '--'}</span>
            <span>&uarr; {current?.disk_write_mbs != null ? `${current.disk_write_mbs.toFixed(1)} MB/s` : '--'}</span>
          </div>
        </Card>
      </motion.div>

      <motion.div variants={itemVariants}>
        <Card padding="lg" className="overflow-hidden">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-text flex items-center gap-2">
              <Gauge size={16} className="text-accent" />
              CPU & RAM History
            </h2>
            <Badge variant={running ? 'success' : 'default'}>
              {running ? 'Live' : 'Paused'}
            </Badge>
          </div>
          {data.length >= 2 ? (
            <StreamArea
              height={240}
              yMax={100}
              series={[
                { key: 'cpu', label: 'CPU', color: COLORS.cpu, values: data.map(d => d.cpu) },
                { key: 'ram', label: 'RAM', color: COLORS.ram, values: data.map(d => d.ram) },
              ]}
              labels={data.map(d => formatChartTick(d.ts))}
              ariaLabel="CPU and RAM load over this live session"
            />
          ) : (
            <div className="h-72 flex flex-col items-center justify-center text-center gap-1.5">
              <p className="text-sm text-text-secondary">No live samples yet</p>
              <p className="text-xs text-text-tertiary max-w-[42ch]">
                The CPU and RAM trend draws from real samples only — it stays empty until the monitor has collected at least two minutes of data.
              </p>
            </div>
          )}
          <p className="text-[10.5px] text-text-tertiary mt-2">
            {data.length >= 2
              ? `${data.length} real samples · hover the plot to read them`
              : 'Samples are appended every 3s while the monitor runs.'}
          </p>
        </Card>
      </motion.div>

      <motion.div variants={itemVariants} className="grid grid-cols-3 gap-4">
        <Card padding="md" className="relative overflow-hidden">
          <div className="flex items-center gap-2 mb-1">
            <Wifi size={16} className="text-accent" />
            <span className="text-xs text-text-secondary">Network</span>
          </div>
          <div className="flex items-center gap-4 mt-2">
            <div>
              <div className="text-[10px] text-text-tertiary">Download</div>
              <div className="text-lg font-semibold text-text">{current?.network_recv_mbs != null ? `${current.network_recv_mbs.toFixed(1)} MB/s` : '--'}</div>
            </div>
            <div>
              <div className="text-[10px] text-text-tertiary">Upload</div>
              <div className="text-lg font-semibold text-text">{current?.network_sent_mbs != null ? `${current.network_sent_mbs.toFixed(1)} MB/s` : '--'}</div>
            </div>
          </div>
        </Card>

        <Card padding="md" tilt>
          <div className="flex items-center gap-2 mb-1">
            <Gauge size={16} className="text-accent" />
            <span className="text-xs text-text-secondary">Processes</span>
          </div>
          <div className="text-2xl font-semibold text-text mt-1">{current?.processes != null ? current.processes : '--'}</div>
          <div className="text-[11px] text-text-tertiary mt-1">Running processes</div>
        </Card>

        <Card padding="md" tilt>
          <div className="flex items-center gap-2 mb-1">
            <Thermometer size={16} className="text-accent" />
            <span className="text-xs text-text-secondary">Temperature</span>
          </div>
          <div className="text-2xl font-semibold text-text mt-1">
            {current?.temperature != null ? `${current.temperature}°C` : '--'}
          </div>
          <div className="text-[11px] text-text-tertiary mt-1">System temperature</div>
        </Card>
      </motion.div>

      <motion.div variants={itemVariants}>
        <Card padding="lg">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-text flex items-center gap-2">
              <Clock size={16} className="text-accent" />
              Metric History
            </h2>
            <div className="flex items-center gap-2">
              {['cpu', 'ram', 'gpu', 'disk'].map(cat => (
                <Button
                  key={cat}
                  size="sm"
                  variant={historyCategory === cat ? 'primary' : 'secondary'}
                  onClick={() => setHistoryCategory(cat)}
                  className="capitalize"
                >
                  {cat}
                </Button>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-2 mb-4">
            {periods.map(p => (
              <Button
                key={p.key}
                size="sm"
                variant={historyPeriod === p.key ? 'primary' : 'secondary'}
                onClick={() => setHistoryPeriod(p.key)}
              >
                {p.label}
              </Button>
            ))}
          </div>
          {historyLoading ? (
            <Skeleton className="h-56 w-full rounded-xl" />
          ) : historyChartData.length === 0 ? (
            <div className="h-56 flex flex-col items-center justify-center text-center gap-1.5">
              <p className="text-sm text-text-secondary">No {historyCategory.toUpperCase()} history yet</p>
              <p className="text-xs text-text-tertiary max-w-[42ch]">
                Samples appear here once the monitor has run for a few minutes on this period.
              </p>
            </div>
          ) : (
            <StreamArea
              height={224}
              yMax={100}
              unit="%"
              series={[{
                key: historyCategory,
                label: historyCategory.toUpperCase(),
                color: COLORS[historyCategory as keyof typeof COLORS],
                values: historyChartData.map(p => p.value),
              }]}
              labels={historyChartData.map(p => formatChartTick(p.ts))}
              ariaLabel={`${historyCategory} history for the last ${historyPeriod}`}
            />
          )}
        </Card>
      </motion.div>
    </motion.div>
  )
}
