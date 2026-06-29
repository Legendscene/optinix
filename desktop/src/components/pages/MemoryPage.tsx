import { useState, useMemo } from 'react'
import { motion } from 'framer-motion'
import { MemoryStick, HardDrive, Trash2, Zap, RefreshCw } from 'lucide-react'
import { Card } from '../ui/Card'
import { MetricCard } from '../ui/MetricCard'
import { ActionCard } from '../ui/ActionCard'
import { ProgressBar } from '../ui/ProgressBar'
import { Skeleton } from '../ui/Skeleton'
import { Badge } from '../ui/Badge'
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

export function MemoryPage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const [, setLoading] = useState<string | null>(null)
  const [result, setResult] = useState<string | null>(null)

  const mem = systemInfo?.memory
  const total = mem?.total_gb ?? 0
  const used = mem?.used_gb ?? 0
  const available = mem?.available_gb ?? 0
  const percent = mem?.percent ?? 0

  const memSegments = useMemo(() => [
    { label: 'Used', value: used, pct: percent, color: '#6366f1' },
    { label: 'Available', value: available, pct: 100 - percent, color: '#22c55e' },
  ], [used, available, percent])

  async function handleFreeRam() {
    setLoading('free')
    setResult(null)
    try {
      const res = await api.ramBoost()
      setResult(res.message ?? 'RAM freed successfully')
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
      await api.tweakStateSet({ 'clear_cache': true })
      setResult('Cache cleared successfully')
    } catch {
      setResult('Failed to clear cache')
    } finally {
      setLoading(null)
    }
  }

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
        </Card>
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-3 gap-4">
        <ActionCard
          icon={<Trash2 size={20} />}
          title="Free RAM"
          desc="Release unused memory pages and cached data immediately"
          tags={['Quick', 'Safe']}
          onClick={handleFreeRam}
        />
        <ActionCard
          icon={<Zap size={20} />}
          title="Memory Optimization"
          desc="Reclaim standby memory and optimize page file settings"
          tags={['Deep Clean']}
          onClick={handleOptimize}
        />
        <ActionCard
          icon={<RefreshCw size={20} />}
          title="Clear Cache"
          desc="Flush system cache and temporary memory buffers"
          tags={['Cache', 'Maintenance']}
          onClick={handleClearCache}
        />
      </motion.div>

      {result && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <Card className="text-center py-3">
            <span className={cn('text-sm font-medium', result.includes('success') || result.includes('complete') || result.includes('freed') ? 'text-green' : 'text-red')}>
              {result}
            </span>
          </Card>
        </motion.div>
      )}
    </motion.div>
  )
}
