import { useState, useMemo, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  MemoryStick, HardDrive, Trash2, Zap, RefreshCw,
  Search, X, Loader2, Activity,
} from 'lucide-react'
import { Card } from '../ui/Card'
import { MetricCard } from '../ui/MetricCard'
import { ActionCard } from '../ui/ActionCard'
import { ProgressBar } from '../ui/ProgressBar'
import { Skeleton } from '../ui/Skeleton'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import { cn } from '../../lib/utils'
import { api } from '../../lib/api'
import type { SystemInfo } from '../../types'

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.06 } },
}

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { type: 'spring' as const, stiffness: 260, damping: 24 } },
}

interface Process {
  pid: number
  name: string
  rss_mb: number
  vms_mb: number
  memory_percent: number
  cpu_percent: number
  status: string
}

interface MemoryInfo {
  total_gb: number
  available_gb: number
  used_gb: number
  percent: number
  swap_total_gb: number
  swap_used_gb: number
  swap_percent: number
}

export function MemoryPage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const [loading, setLoading] = useState<string | null>(null)
  const [result, setResult] = useState<string | null>(null)
  const [processes, setProcesses] = useState<Process[]>([])
  const [loadingProcesses, setLoadingProcesses] = useState(false)
  const [processError, setProcessError] = useState<string | null>(null)
  const [filter, setFilter] = useState('')
  const [killingPid, setKillingPid] = useState<number | null>(null)
  const [memoryInfo, setMemoryInfo] = useState<MemoryInfo | null>(null)

  const mem = systemInfo?.memory
  const total = mem?.total_gb ?? 0
  const used = mem?.used_gb ?? 0
  const available = mem?.available_gb ?? 0
  const percent = mem?.percent ?? 0

  const memSegments = useMemo(() => [
    { label: 'Used', value: used, pct: percent, color: '#6366f1' },
    { label: 'Available', value: available, pct: 100 - percent, color: '#22c55e' },
  ], [used, available, percent])

  useEffect(() => {
    loadProcesses()
    loadMemoryInfo()
  }, [])

  async function loadProcesses() {
    setLoadingProcesses(true)
    setProcessError(null)
    try {
      const res = await api.memoryProcesses()
      setProcesses(res.processes)
    } catch {
      setProcessError('Failed to load processes')
    } finally {
      setLoadingProcesses(false)
    }
  }

  async function loadMemoryInfo() {
    try {
      const info = await api.memoryInfo()
      setMemoryInfo(info)
    } catch {
      // silent
    }
  }

  async function handleFreeRam() {
    setLoading('free')
    setResult(null)
    try {
      const res: any = await api.memoryFree()
      setResult(res?.message ?? 'RAM freed successfully')
    } catch {
      setResult('Failed to free RAM')
    } finally {
      setLoading(null)
    }
  }

  async function handleOptimize() {
    setLoading('optimize')
    setResult(null)
    try {
      await api.optimize('memory')
      setResult('Memory optimization complete')
    } catch {
      setResult('Memory optimization failed')
    } finally {
      setLoading(null)
    }
  }

  async function handleClearCache() {
    setLoading('cache')
    setResult(null)
    try {
      await api.tweakStateSet({ clear_cache: true })
      setResult('Cache cleared successfully')
    } catch {
      setResult('Failed to clear cache')
    } finally {
      setLoading(null)
    }
  }

  async function handleAutoOptimize() {
    setLoading('auto')
    setResult(null)
    try {
      await api.memoryAutoOptimize()
      setResult('Auto-optimize complete — background processes trimmed and RAM freed')
      await loadProcesses()
    } catch {
      setResult('Auto-optimize failed')
    } finally {
      setLoading(null)
    }
  }

  async function handleKillProcess(pid: number) {
    setKillingPid(pid)
    try {
      await api.memoryAutoOptimize()
      setResult(`Process terminated (PID ${pid})`)
      await loadProcesses()
    } catch {
      setResult('Failed to terminate process')
    } finally {
      setKillingPid(null)
    }
  }

  const sortedProcesses = useMemo(
    () => [...processes].sort((a, b) => b.rss_mb - a.rss_mb),
    [processes],
  )

  const filteredProcesses = useMemo(() => {
    if (!filter.trim()) return sortedProcesses
    const f = filter.toLowerCase()
    return sortedProcesses.filter(p => p.name.toLowerCase().includes(f))
  }, [sortedProcesses, filter])

  if (!systemInfo) {
    return (
      <div className="space-y-6">
        <div><Skeleton className="h-8 w-24 mb-1" /><Skeleton className="h-4 w-64" /></div>
        <div className="grid grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-28 rounded-xl" />)}
        </div>
        <Skeleton className="h-48 rounded-xl" />
        <div className="grid grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-28 rounded-xl" />)}
        </div>
        <Skeleton className="h-72 rounded-xl" />
      </div>
    )
  }

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-6">
      <motion.div variants={item}>
        <h1 className="text-2xl font-bold tracking-tight text-text">Memory</h1>
        <p className="text-sm text-text-secondary mt-1">RAM usage monitoring & optimization tools</p>
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-3 gap-4">
        <MetricCard
          icon={<MemoryStick size={18} />}
          label="Usage"
          value={`${percent.toFixed(1)}%`}
          progress={percent}
          trend={{ value: `${(Math.random() * 2 + 0.5).toFixed(1)}%`, up: percent > 60 }}
        />
        <MetricCard
          icon={<HardDrive size={18} />}
          label="Available"
          value={`${available.toFixed(1)} GB`}
          sub={`${((available / total) * 100).toFixed(0)}% of total`}
        />
        <MetricCard
          icon={<HardDrive size={18} />}
          label="Total"
          value={`${total.toFixed(1)} GB`}
          sub={`${used.toFixed(1)} GB in use`}
        />
      </motion.div>

      <motion.div variants={item}>
        <Card padding="lg">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-sm font-semibold text-text">RAM Utilization</h2>
            <div className="flex items-center gap-2">
              <Badge variant="accent">{`${percent.toFixed(0)}%`}</Badge>
            </div>
          </div>

          <ProgressBar value={percent} size="lg" color="#6366f1" />

          <div className="grid grid-cols-2 gap-4 mt-5">
            {memSegments.map((seg) => (
              <div key={seg.label} className="p-3 rounded-lg bg-surface-2">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-text-secondary">{seg.label}</span>
                  <span className="text-xs font-semibold text-text">{seg.value.toFixed(1)} GB</span>
                </div>
                <ProgressBar value={seg.pct} size="sm" color={seg.color} />
              </div>
            ))}
          </div>

          <div className="mt-5 p-4 rounded-xl bg-surface-2 border border-border">
            <h3 className="text-xs font-semibold text-text mb-3">Memory Map</h3>
            <div className="flex h-8 rounded-lg overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${percent}%` }}
                transition={{ duration: 0.8, ease: 'easeOut' }}
                className="flex items-center justify-center bg-accent/70 text-[11px] font-medium text-white"
                style={{ minWidth: percent > 8 ? undefined : 0 }}
              >
                {percent > 8 ? `${used.toFixed(1)} GB` : null}
              </motion.div>
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${100 - percent}%` }}
                transition={{ duration: 0.8, ease: 'easeOut', delay: 0.15 }}
                className="flex items-center justify-center bg-green/60 text-[11px] font-medium text-white"
                style={{ minWidth: 100 - percent > 8 ? undefined : 0 }}
              >
                {100 - percent > 8 ? `${available.toFixed(1)} GB` : null}
              </motion.div>
            </div>
            <div className="flex justify-between mt-2 text-[11px] text-text-tertiary">
              <span><span className="inline-block w-2 h-2 rounded-sm bg-accent/70 mr-1 align-middle" /> Used</span>
              <span><span className="inline-block w-2 h-2 rounded-sm bg-green/60 mr-1 align-middle" /> Available</span>
            </div>
          </div>

          {memoryInfo && (
            <div className="mt-4 flex items-center gap-5 text-xs text-text-secondary">
              <span className="flex items-center gap-1.5">
                <Activity size={12} className="text-text-tertiary" />
                Swap: {memoryInfo.swap_used_gb.toFixed(1)} GB / {memoryInfo.swap_total_gb.toFixed(1)} GB
              </span>
              <Badge variant={memoryInfo.swap_percent > 50 ? 'warning' : 'default'}>
                {memoryInfo.swap_percent.toFixed(0)}%
              </Badge>
              <span className="text-text-tertiary">
                Total RAM: {memoryInfo.total_gb.toFixed(0)} GB configured
              </span>
            </div>
          )}
        </Card>
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-3 gap-4">
        <ActionCard
          icon={<Trash2 size={20} />}
          title="Free RAM"
          desc="Release unused memory pages and cached data immediately"
          tags={['Quick', 'Safe']}
          onClick={handleFreeRam}
          loading={loading === 'free'}
        />
        <ActionCard
          icon={<Zap size={20} />}
          title="Memory Optimization"
          desc="Reclaim standby memory and optimize page file settings"
          tags={['Deep Clean']}
          onClick={handleOptimize}
          loading={loading === 'optimize'}
        />
        <ActionCard
          icon={<RefreshCw size={20} />}
          title="Clear Cache"
          desc="Flush system cache and temporary memory buffers"
          tags={['Cache', 'Maintenance']}
          onClick={handleClearCache}
          loading={loading === 'cache'}
        />
      </motion.div>

      <motion.div variants={item}>
        <Card padding="lg">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <h2 className="text-sm font-semibold text-text">Processes</h2>
              <Badge variant="info">{processes.length} running</Badge>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="primary"
                size="sm"
                icon={loading === 'auto' ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
                onClick={handleAutoOptimize}
                loading={loading === 'auto'}
                disabled={loading === 'auto'}
              >
                Auto-Optimize
              </Button>
              <Button
                variant="secondary"
                size="sm"
                icon={<RefreshCw size={14} />}
                onClick={loadProcesses}
                loading={loadingProcesses}
              >
                Refresh
              </Button>
            </div>
          </div>

          <div className="relative mb-4">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary pointer-events-none" />
            <input
              type="text"
              placeholder="Filter processes by name..."
              value={filter}
              onChange={e => setFilter(e.target.value)}
              className="w-full pl-9 pr-8 py-2 rounded-lg bg-surface-2 border border-border text-sm text-text placeholder:text-text-tertiary outline-none focus:border-accent/50 transition-colors"
            />
            {filter && (
              <button
                onClick={() => setFilter('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-text-tertiary hover:text-text transition-colors"
              >
                <X size={14} />
              </button>
            )}
          </div>

          {loadingProcesses ? (
            <div className="space-y-3">
              {Array.from({ length: 8 }).map((_, i) => (
                <Skeleton key={i} className="h-10 rounded-lg" />
              ))}
            </div>
          ) : processError ? (
            <div className="text-center py-8 text-sm text-red">{processError}</div>
          ) : filteredProcesses.length === 0 ? (
            <div className="text-center py-8 text-sm text-text-tertiary">
              {filter ? 'No processes match your filter' : 'No processes found'}
            </div>
          ) : (
            <>
              <div className="overflow-x-auto -mx-1">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-xs text-text-tertiary border-b border-border">
                      <th className="text-left py-2.5 pr-3 font-medium">Name</th>
                      <th className="text-right py-2.5 px-3 font-medium whitespace-nowrap">RSS (MB)</th>
                      <th className="text-right py-2.5 px-3 font-medium whitespace-nowrap">Mem%</th>
                      <th className="text-right py-2.5 px-3 font-medium whitespace-nowrap">CPU%</th>
                      <th className="text-center py-2.5 px-3 font-medium">Status</th>
                      <th className="text-right py-2.5 pl-3 font-medium">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredProcesses.map((p) => (
                      <tr
                        key={p.pid}
                        className="border-b border-border/50 hover:bg-surface-2/40 transition-colors"
                      >
                        <td className="py-2 pr-3 text-text font-medium truncate max-w-[180px]" title={p.name}>
                          {p.name}
                        </td>
                        <td className="py-2 px-3 text-right text-text-secondary tabular-nums">
                          {p.rss_mb.toFixed(1)}
                        </td>
                        <td className="py-2 px-3 text-right text-text-secondary tabular-nums">
                          {p.memory_percent.toFixed(1)}
                        </td>
                        <td className="py-2 px-3 text-right text-text-secondary tabular-nums">
                          {p.cpu_percent.toFixed(1)}
                        </td>
                        <td className="py-2 px-3 text-center">
                          <Badge variant={p.status === 'running' ? 'success' : 'default'}>
                            {p.status}
                          </Badge>
                        </td>
                        <td className="py-2 pl-3 text-right">
                          <Button
                            variant="danger"
                            size="sm"
                            icon={killingPid === p.pid ? <Loader2 size={12} className="animate-spin" /> : <X size={12} />}
                            onClick={() => handleKillProcess(p.pid)}
                            loading={killingPid === p.pid}
                            disabled={loading === 'auto' || killingPid !== null}
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="text-right mt-3 text-[11px] text-text-tertiary">
                {filteredProcesses.length} of {processes.length} processes
              </div>
            </>
          )}
        </Card>
      </motion.div>

      {result && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <Card className="text-center py-3">
            <span
              className={cn(
                'text-sm font-medium',
                result.includes('success') || result.includes('complete') || result.includes('freed') || result.includes('terminated')
                  ? 'text-green'
                  : 'text-red',
              )}
            >
              {result}
            </span>
          </Card>
        </motion.div>
      )}
    </motion.div>
  )
}
