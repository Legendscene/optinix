import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  History, Calendar, TrendingUp, Clock, Zap,
  AlertCircle, Cpu, HardDrive, Wifi, Thermometer,
  Database,
} from 'lucide-react'
import { Card } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { Skeleton } from '../ui/Skeleton'
import { PageHero } from '../ui/PageHero'
import { StreamArea } from '../ui/charts/StreamArea'
import { ChartGhost } from '../ui/charts/ChartGhost'
import { VBars } from '../ui/charts/VBars'
import { cn } from '../../lib/utils'
import { api } from '../../lib/api'
import type { SystemInfo, TimelineEvent } from '../../types'

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.05 } } }
const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }

const timeRanges = [
  { value: 24, label: '24h' },
  { value: 168, label: '7d' },
  { value: 720, label: '30d' },
]

const tabs = ['metrics', 'events', 'health-scores', 'boot-times', 'optimization-impact'] as const

const metricIcons: Record<string, React.ReactNode> = {
  cpu: <Cpu className="w-4 h-4" />,
  ram: <Database className="w-4 h-4" />,
  disk: <HardDrive className="w-4 h-4" />,
  network: <Wifi className="w-4 h-4" />,
  temperature: <Thermometer className="w-4 h-4" />,
}

const eventTypeColors: Record<string, string> = {
  optimization: 'text-green bg-green-dim/20 border-green/30',
  rollback: 'text-yellow bg-yellow-dim/20 border-yellow/30',
  maintenance: 'text-cyan bg-cyan-dim/20 border-cyan/30',
  diagnostic: 'text-accent bg-accent-dim/20 border-accent/30',
}

const eventTypeBadge: Record<string, 'success' | 'warning' | 'info' | 'accent'> = {
  optimization: 'success',
  rollback: 'warning',
  maintenance: 'info',
  diagnostic: 'accent',
}

/* Token colours: the seven dimensions keep a stable identity across themes and
   accent presets instead of seven pinned dark-mode hexes. */
const healthScoreColors = [
  { key: 'pc_health', label: 'PC Health', color: 'var(--chart-1)' },
  { key: 'windows_health', label: 'Windows', color: 'var(--chart-2)' },
  { key: 'gaming', label: 'Gaming', color: 'var(--color-green)' },
  { key: 'developer', label: 'Developer', color: 'var(--chart-3)' },
  { key: 'security', label: 'Security', color: 'var(--chart-4)' },
  { key: 'storage', label: 'Storage', color: 'var(--color-cyan)' },
  { key: 'battery', label: 'Battery', color: 'var(--color-violet)' },
]

interface MetricDataPoint {
  timestamp: number
  value: number
}

interface HealthScorePoint {
  timestamp: number
  [key: string]: number
}

interface BootTimePoint {
  timestamp: number
  seconds: number
}

interface OptimizationImpactItem {
  name: string
  before: number
  after: number
  category: string
}

export function TimelinePage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const [timeRange, setTimeRange] = useState(24)
  const [activeTab, setActiveTab] = useState<typeof tabs[number]>('metrics')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [metrics, setMetrics] = useState<Record<string, MetricDataPoint[]>>({})
  const [events, setEvents] = useState<TimelineEvent[]>([])
  const [healthScores, setHealthScores] = useState<HealthScorePoint[]>([])
  const [bootTimes, setBootTimes] = useState<BootTimePoint[]>([])
  const [optimizationImpact, setOptimizationImpact] = useState<OptimizationImpactItem[]>([])

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      switch (activeTab) {
        case 'metrics': {
          const metricsList = ['cpu', 'ram', 'disk', 'network', 'temperature']
          const results = await Promise.allSettled(
            metricsList.map(m => api.timelineMetrics(m, timeRange))
          )
          const data: Record<string, MetricDataPoint[]> = {}
          metricsList.forEach((m, i) => {
            if (results[i].status === 'fulfilled') {
              data[m] = (results[i] as PromiseFulfilledResult<MetricDataPoint[]>).value
            }
          })
          setMetrics(data)
          break
        }
        case 'events': {
          const res = await api.timelineEvents(50)
          setEvents(res.events ?? [])
          break
        }
        case 'health-scores': {
          const days = timeRange === 24 ? 1 : timeRange === 168 ? 7 : 30
          const res = await api.timelineHealthScores(days)
          setHealthScores(Array.isArray(res) ? res : [])
          break
        }
        case 'boot-times': {
          const days = timeRange === 24 ? 1 : timeRange === 168 ? 7 : 30
          const res = await api.timelineBootTimes(days)
          setBootTimes(Array.isArray(res) ? res : [])
          break
        }
        case 'optimization-impact': {
          const res = await api.timelineOptimizationImpact()
          setOptimizationImpact(Array.isArray(res) ? res : [])
          break
        }
      }
    } catch {
      setError('Failed to load timeline data')
    } finally {
      setLoading(false)
    }
  }, [activeTab, timeRange])

  useEffect(() => { fetchData() }, [fetchData])

  const formatTime = (ts: number) => {
    const d = new Date(ts)
    if (timeRange <= 24) return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' })
  }

  const calcStats = (data: MetricDataPoint[]) => {
    if (!data.length) return { min: 0, max: 0, avg: 0, current: 0 }
    const values = data.map(d => d.value)
    return {
      min: Math.min(...values),
      max: Math.max(...values),
      avg: values.reduce((a, b) => a + b, 0) / values.length,
      current: values[values.length - 1],
    }
  }

  /* Keys can exist with empty arrays when the period has no readings; the
     empty state is decided by actual samples, not by key presence. */
  const totalMetricSamples = Object.values(metrics).reduce((n, rows) => n + rows.length, 0)

  if (!systemInfo) {
    return (
      <div className="page space-y-5">
        <div><Skeleton variant="text" width="250px" height="28px" /><Skeleton variant="text" width="350px" height="16px" className="mt-2" /></div>
        <div className="flex gap-4"><Skeleton variant="rectangular" height="40px" width="300px" /><Skeleton variant="rectangular" height="40px" width="200px" /></div>
        <Skeleton variant="rectangular" height="400px" />
      </div>
    )
  }

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="page space-y-5">
      <motion.div variants={item}>
        <PageHero
          eyebrow="History"
          title="System Timeline"
          subtitle="Recorded metrics, events and how earlier optimizations actually moved the numbers."
          icon={<History size={19} />}
          badges={<Badge variant="info">{timeRanges.find((r) => r.value === timeRange)?.label ?? '24h'}</Badge>}
          stats={[
            { label: 'CPU', value: `${systemInfo.cpu.percent}%`, tone: systemInfo.cpu.percent > 80 ? 'bad' : 'default', hint: 'live' },
            { label: 'Memory', value: `${systemInfo.memory.percent}%`, hint: `${systemInfo.memory.available_gb.toFixed(1)} GB free` },
            { label: 'System disk', value: `${systemInfo.disk[0]?.percent ?? 0}%`, hint: 'used' },
            { label: 'GPU', value: `${systemInfo.gpu.usage}%`, hint: systemInfo.gpu.name || 'not detected' },
          ]}
        />
      </motion.div>

      <motion.div variants={item} className="flex items-center justify-between">
        <div className="flex gap-1 p-1 rounded-xl bg-surface-2 w-fit">
          {tabs.map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={cn(
                'px-4 py-2 rounded-lg text-sm font-medium transition-all capitalize',
                activeTab === tab
                  ? 'bg-surface-1 text-text shadow-sm'
                  : 'text-text-secondary hover:text-text'
              )}
            >
              {tab === 'health-scores' ? 'Health Scores' :
               tab === 'boot-times' ? 'Boot Times' :
               tab === 'optimization-impact' ? 'Optimization Impact' : tab}
            </button>
          ))}
        </div>
        <div className="flex gap-1 p-1 rounded-xl bg-surface-2">
          {timeRanges.map(tr => (
            <button
              key={tr.value}
              onClick={() => setTimeRange(tr.value)}
              className={cn(
                'px-3 py-1.5 rounded-lg text-xs font-medium transition-all',
                timeRange === tr.value
                  ? 'bg-surface-1 text-text shadow-sm'
                  : 'text-text-secondary hover:text-text'
              )}
            >
              {tr.label}
            </button>
          ))}
        </div>
      </motion.div>

      {error && (
        <motion.div variants={item} className="p-4 rounded-xl border border-red/30 bg-red-dim/10">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red" />
            <span className="text-sm text-text">{error}</span>
            <button onClick={() => setError(null)} className="ml-auto p-1 rounded-md hover:bg-surface-2 text-text-secondary"><Calendar className="w-4 h-4" /></button>
          </div>
        </motion.div>
      )}

      {loading ? (
        <motion.div variants={item}>
          <Card padding="lg">
            <div className="space-y-4">
              <Skeleton variant="rectangular" height="40px" />
              <div className="grid grid-cols-4 gap-4">
                {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} variant="rectangular" height="80px" />)}
              </div>
              <Skeleton variant="rectangular" height="300px" />
            </div>
          </Card>
        </motion.div>
      ) : (
        <>
          {activeTab === 'metrics' && (
            <motion.div variants={item} className="space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
                {['cpu', 'ram', 'disk', 'network', 'temperature'].map(metric => {
                  const data = metrics[metric] ?? []
                  const stats = calcStats(data)
                  return (
                    <Card key={metric} padding="md" tilt className="text-center">
                      <div className="flex items-center justify-center mb-2">
                        <div className="p-2 rounded-lg bg-surface-3 text-accent">
                          {metricIcons[metric]}
                        </div>
                      </div>
                      <div className="text-lg font-bold text-text capitalize">{metric}</div>
                      {data.length > 0 ? (
                        <div className="mt-2 space-y-1 text-[11px] text-text-tertiary">
                          <div className="flex justify-between"><span>Current</span><span className="text-text font-medium">{stats.current.toFixed(1)}</span></div>
                          <div className="flex justify-between"><span>Avg</span><span>{stats.avg.toFixed(1)}</span></div>
                          <div className="flex justify-between"><span>Min</span><span className="text-green">{stats.min.toFixed(1)}</span></div>
                          <div className="flex justify-between"><span>Max</span><span className="text-red">{stats.max.toFixed(1)}</span></div>
                        </div>
                      ) : (
                        <div className="mt-2.5">
                          <div className="flex items-end justify-center gap-1 h-7" aria-hidden>
                            {[9, 15, 11, 19, 14].map((h, i) => (
                              <span
                                key={i}
                                className="w-1.5 rounded-sm bg-surface-4 opacity-70"
                                style={{ height: h }}
                              />
                            ))}
                          </div>
                          <p className="mt-1.5 text-[10.5px] text-text-tertiary">Waiting for samples</p>
                        </div>
                      )}
                    </Card>
                  )
                })}
              </div>
              {['cpu', 'ram', 'disk', 'network', 'temperature'].map(metric => {
                const data = metrics[metric] ?? []
                if (!data.length) return null
                return (
                  <Card key={`chart-${metric}`} padding="lg">
                    <div className="flex items-center gap-2 mb-3">
                      {metricIcons[metric]}
                      <h3 className="text-sm font-semibold text-text capitalize">{metric} Usage</h3>
                    </div>
                    <div className="mt-1">
                      <StreamArea
                        series={[{ key: metric, label: metric, color: 'var(--chart-1)', values: data.map((d) => d.value) }]}
                        height={192}
                        unit=""
                        labels={data.map((d) => formatTime(d.timestamp))}
                        ariaLabel={`${metric} history over ${data.length} samples`}
                      />
                    </div>
                  </Card>
                )
              })}
              {totalMetricSamples === 0 && (
                <Card padding="lg">
                  <div className="mb-3">
                    <h2 className="text-[13.5px] font-semibold text-text accent-rail">Recorded series</h2>
                    <p className="mt-1 text-[11.5px] text-text-tertiary">
                      One plot per category once the monitor has stored readings.
                    </p>
                  </div>
                  <ChartGhost
                    height={260}
                    samples={0}
                    target={6}
                    title="No samples recorded in this period"
                    hint="The monitor records while Live Monitor is open. Every point stored here is a real poll — nothing is back-filled or estimated."
                  />
                </Card>
              )}
            </motion.div>
          )}

          {activeTab === 'events' && (
            <motion.div variants={item}>
              <Card padding="lg">
                <div className="flex items-center gap-2 mb-4">
                  <History className="w-4 h-4 text-accent" />
                  <h2 className="text-sm font-semibold text-text">Chronological Events</h2>
                  <span className="text-[10px] text-text-tertiary ml-auto">{events.length} events</span>
                </div>
                {events.length > 0 ? (
                  <div className="relative">
                    <div className="absolute left-[17px] top-2 bottom-2 w-px bg-border" />
                    <div className="space-y-3">
                      {events.map((ev, i) => (
                        <motion.div
                          key={`${ev.timestamp}-${i}`}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: i * 0.03 }}
                          className="relative flex items-start gap-4 pl-10"
                        >
                          <div                           className={cn(
                            'absolute left-2.5 w-[9px] h-[9px] rounded-full border-2 mt-1.5',
                            eventTypeColors[ev.type]?.includes('green') ? 'border-green bg-green-dim/20' :
                            eventTypeColors[ev.type]?.includes('yellow') ? 'border-yellow bg-yellow-dim/20' :
                            eventTypeColors[ev.type]?.includes('cyan') ? 'border-cyan bg-cyan-dim/20' :
                            'border-accent bg-accent-dim/20'
                          )} />
                          <div className="flex-1 min-w-0">
                            <div className={cn(
                              'p-3 rounded-xl border',
                              eventTypeColors[ev.type] ?? 'border-border bg-surface-2/50'
                            )}>
                              <div className="flex items-center gap-2 mb-1">
                                <Badge variant={eventTypeBadge[ev.type] ?? 'default'}>{ev.type}</Badge>
                                <span className="text-xs text-text-tertiary">
                                  {new Date(ev.timestamp).toLocaleDateString()} {new Date(ev.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                </span>
                              </div>
                              <p className="text-sm font-medium text-text">{ev.name}</p>
                              <p className="text-xs text-text-secondary mt-0.5">{ev.details}</p>
                            </div>
                          </div>
                        </motion.div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-3 py-8">
                    <History className="w-10 h-10 text-text-tertiary" />
                    <p className="text-sm text-text-secondary">No events recorded</p>
                  </div>
                )}
              </Card>
            </motion.div>
          )}

          {activeTab === 'health-scores' && (
            <motion.div variants={item}>
              <Card padding="lg">
                <div className="flex items-center gap-2 mb-4">
                  <TrendingUp className="w-4 h-4 text-accent" />
                  <h2 className="text-sm font-semibold text-text">Health Scores Over Time</h2>
                </div>
                {healthScores.length > 0 ? (
                  <div className="mt-1">
                    <StreamArea
                      series={healthScoreColors
                        .filter((h) => healthScores.some((d) => d[h.key] != null))
                        .map((h) => ({
                          key: h.key,
                          label: h.label,
                          color: h.color,
                          values: healthScores.map((d) => d[h.key] ?? 0),
                          /* Only the headline dimension fills; seven washes would
                             blend into one grey slab. */
                          fill: h.key === 'pc_health',
                        }))}
                      height={288}
                      yMax={100}
                      guides={[25, 50, 75]}
                      labels={healthScores.map((d) => formatTime(d.timestamp))}
                      ariaLabel="Health score dimensions over time"
                    />
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-3 py-8">
                    <TrendingUp className="w-10 h-10 text-text-tertiary" />
                    <p className="text-sm text-text-secondary">No health score data available</p>
                  </div>
                )}
              </Card>
            </motion.div>
          )}

          {activeTab === 'boot-times' && (
            <motion.div variants={item}>
              <Card padding="lg">
                <div className="flex items-center gap-2 mb-4">
                  <Clock className="w-4 h-4 text-accent" />
                  <h2 className="text-sm font-semibold text-text">Boot Times</h2>
                </div>
                {bootTimes.length > 0 ? (
                  <div className="mt-1">
                    <VBars
                      data={bootTimes.map((d) => ({ key: String(d.timestamp), label: formatTime(d.timestamp), value: d.seconds }))}
                      height={256}
                      color="var(--chart-1)"
                      format={(v) => `${Math.round(v)} s`}
                      ariaLabel={`Boot times across ${bootTimes.length} recorded boots`}
                    />
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-3 py-8">
                    <Clock className="w-10 h-10 text-text-tertiary" />
                    <p className="text-sm text-text-secondary">No boot time data available</p>
                  </div>
                )}
              </Card>
            </motion.div>
          )}

          {activeTab === 'optimization-impact' && (
            <motion.div variants={item}>
              <Card padding="lg">
                <div className="flex items-center gap-2 mb-4">
                  <Zap className="w-4 h-4 text-accent" />
                  <h2 className="text-sm font-semibold text-text">Optimization Impact</h2>
                </div>
                {optimizationImpact.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {optimizationImpact.map((opt, i) => {
                      const improvement = ((opt.after - opt.before) / opt.before) * 100
                      return (
                        <motion.div
                          key={i}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: i * 0.05 }}
                          className="p-4 rounded-xl border border-border bg-surface-2/50"
                        >
                          <div className="flex items-center justify-between mb-3">
                            <div>
                              <p className="text-sm font-medium text-text">{opt.name}</p>
                              <Badge variant={
                                opt.category === 'optimization' ? 'success' :
                                opt.category === 'rollback' ? 'warning' :
                                'info'
                              } className="mt-1">{opt.category}</Badge>
                            </div>
                            <div className={cn(
                              'px-2 py-1 rounded-lg text-xs font-semibold',
                              improvement > 0 ? 'bg-green-dim/20 text-green' : 'bg-red-dim/20 text-red'
                            )}>
                              {improvement > 0 ? '+' : ''}{improvement.toFixed(1)}%
                            </div>
                          </div>
                          <div className="space-y-2">
                            <div>
                              <div className="flex justify-between text-[11px] text-text-tertiary mb-1">
                                <span>Before</span>
                                <span>{opt.before.toFixed(1)}</span>
                              </div>
                              <div className="h-2 rounded-full bg-surface-3 overflow-hidden">
                                <div className="h-full rounded-full bg-red/60" style={{ width: `${Math.min(opt.before, 100)}%` }} />
                              </div>
                            </div>
                            <div>
                              <div className="flex justify-between text-[11px] text-text-tertiary mb-1">
                                <span>After</span>
                                <span>{opt.after.toFixed(1)}</span>
                              </div>
                              <div className="h-2 rounded-full bg-surface-3 overflow-hidden">
                                <div className="h-full rounded-full bg-green/60" style={{ width: `${Math.min(opt.after, 100)}%` }} />
                              </div>
                            </div>
                          </div>
                        </motion.div>
                      )
                    })}
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-3 py-8">
                    <Zap className="w-10 h-10 text-text-tertiary" />
                    <p className="text-sm text-text-secondary">No optimization impact data available</p>
                  </div>
                )}
              </Card>
            </motion.div>
          )}
        </>
      )}
    </motion.div>
  )
}
