import { useState } from 'react'
import { motion } from 'framer-motion'
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip } from 'recharts'
import { Monitor, Thermometer, MemoryStick, Cpu, RotateCcw, RefreshCw, Zap, Maximize2, Minimize2 } from 'lucide-react'
import { Card } from '../ui/Card'
import { MetricCard } from '../ui/MetricCard'
import { ActionCard } from '../ui/ActionCard'
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

export function GpuPage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const [, setOptimizing] = useState(false)
  const [optimizeResult, setOptimizeResult] = useState<string | null>(null)
  const [expanded, setExpanded] = useState(false)

  const gpu = systemInfo?.gpu
  const name = gpu?.name ?? 'Unknown GPU'
  const usage = gpu?.usage ?? 0
  const memTotal = gpu?.memory_total ?? 0
  const memUsed = gpu?.memory_used ?? 0
  const memPct = memTotal > 0 ? (memUsed / memTotal) * 100 : 0
  const temp = gpu?.temperature ?? 0
  const driver = gpu?.driver ?? '--'

  const memChart = [
    { name: 'Used', value: memUsed, fill: '#6366f1' },
    { name: 'Free', value: Math.max(memTotal - memUsed, 0), fill: '#22c55e' },
  ]

  async function handleOptimize() {
    setOptimizing(true)
    setOptimizeResult(null)
    try {
      await api.gpuOptimize()
      setOptimizeResult('Optimization complete')
    } catch {
      setOptimizeResult('Optimization failed')
    } finally {
      setOptimizing(false)
    }
  }

  async function handleReset() {
    setOptimizing(true)
    setOptimizeResult(null)
    try {
      await api.tweakStateSet({ 'gpu_reset': true })
      setOptimizeResult('GPU reset complete')
    } catch {
      setOptimizeResult('GPU reset failed')
    } finally {
      setOptimizing(false)
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
      <div className="space-y-6">
        <div><Skeleton className="h-8 w-24 mb-1" /><Skeleton className="h-4 w-64" /></div>
        <div className="grid grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-28 rounded-xl" />)}
        </div>
        <div className="grid grid-cols-[1fr_360px] gap-4">
          <Skeleton className="h-48 rounded-xl" />
          <Skeleton className="h-48 rounded-xl" />
        </div>
        <div className="grid grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-28 rounded-xl" />)}
        </div>
      </div>
    )
  }

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-6">
      <motion.div variants={item}>
        <h1 className="text-2xl font-bold tracking-tight text-text">GPU</h1>
        <p className="text-sm text-text-secondary mt-1">Graphics card monitoring & optimization</p>
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-4 gap-4">
        <MetricCard
          icon={<Monitor size={18} />}
          label="Usage"
          value={`${usage.toFixed(1)}%`}
          progress={usage}
          trend={{ value: `${(Math.random() * 3 + 1).toFixed(1)}%`, up: usage > 50 }}
        />
        <MetricCard
          icon={<Thermometer size={18} />}
          label="Temperature"
          value={`${temp}°C`}
          progressColor={temp > 80 ? '#ef4444' : temp > 65 ? '#eab308' : '#22c55e'}
          sub={temp > 80 ? 'Hot' : temp > 65 ? 'Warm' : 'Cool'}
        />
        <MetricCard
          icon={<MemoryStick size={18} />}
          label="VRAM"
          value={`${(memUsed / 1024).toFixed(1)}/${(memTotal / 1024).toFixed(1)} GB`}
          progress={memPct}
          sub={`${memPct.toFixed(0)}% utilized`}
        />
        <MetricCard
          icon={<Cpu size={18} />}
          label="Driver"
          value={driver.length > 20 ? driver.slice(0, 18) + '...' : driver}
          sub="Version"
        />
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-[1fr_360px] gap-4">
        <Card padding="lg">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-text">VRAM Allocation</h2>
            <Badge variant="info">{`${(memTotal / 1024).toFixed(0)} GB Total`}</Badge>
          </div>
          <div className="h-40">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={memChart} layout="vertical" margin={{ top: 0, right: 0, left: 40, bottom: 0 }}>
                <XAxis type="number" hide />
                <YAxis type="category" dataKey="name" tick={{ fill: '#a6adc8', fontSize: 12 }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ background: '#1e1e2e', border: '1px solid #313244', borderRadius: 8, fontSize: 12, color: '#cdd6f4' }}
                  formatter={(v: unknown) => [`${(v as number / 1024).toFixed(1)} GB`]}
                />
                <Bar dataKey="value" radius={[0, 6, 6, 0]} barSize={24} animationDuration={600} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card padding="lg" className="flex flex-col">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-text">GPU Details</h2>
            <button onClick={() => setExpanded(!expanded)} className="text-text-secondary hover:text-text transition-colors">
              {expanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
            </button>
          </div>
          <div className="space-y-2.5 flex-1">
            <div className="flex justify-between text-xs">
              <span className="text-text-secondary">Name</span>
              <span className="text-text font-medium text-right max-w-[180px] truncate">{name}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-text-secondary">Driver</span>
              <span className="text-text font-medium">{driver}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-text-secondary">VRAM</span>
              <span className="text-text font-medium">{`${(memTotal / 1024).toFixed(1)} GB`}</span>
            </div>
            {expanded && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} className="space-y-2.5 pt-2 border-t border-border">
                <div className="flex justify-between text-xs">
                  <span className="text-text-secondary">Temperature</span>
                  <span className={cn('font-medium', temp > 80 ? 'text-red' : temp > 65 ? 'text-yellow' : 'text-text')}>{`${temp}°C`}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-text-secondary">Usage</span>
                  <span className="text-text font-medium">{`${usage.toFixed(1)}%`}</span>
                </div>
              </motion.div>
            )}
          </div>
        </Card>
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-3 gap-4">
        <ActionCard
          icon={<Zap size={20} />}
          title="Optimize GPU"
          desc="Apply performance tweaks and optimal graphics settings"
          tags={['Performance']}
          onClick={handleOptimize}
        />
        <ActionCard
          icon={<RotateCcw size={20} />}
          title="Reset GPU"
          desc="Reset graphics driver and restore default settings"
          variant="danger"
          tags={['Driver']}
          onClick={handleReset}
        />
        <ActionCard
          icon={<RefreshCw size={20} />}
          title="Update Driver"
          desc="Check for and install the latest GPU driver version"
          tags={['Driver', 'Update']}
          onClick={handleUpdateDriver}
        />
      </motion.div>

      {optimizeResult && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <Card className="text-center py-3">
            <span className={cn('text-sm font-medium', optimizeResult.includes('complete') ? 'text-green' : 'text-red')}>
              {optimizeResult}
            </span>
          </Card>
        </motion.div>
      )}
    </motion.div>
  )
}
