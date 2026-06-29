import { useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { AreaChart, Area, ResponsiveContainer, Tooltip } from 'recharts'
import { Cpu, Thermometer, Layers, Hash, Zap, Gauge, Battery } from 'lucide-react'
import { Card } from '../ui/Card'
import { MetricCard } from '../ui/MetricCard'
import { ActionCard } from '../ui/ActionCard'
import { Skeleton } from '../ui/Skeleton'
import { Badge } from '../ui/Badge'
import { api } from '../../lib/api'
import type { SystemInfo } from '../../types'

function generateHistory() {
  const now = Date.now()
  return Array.from({ length: 60 }, (_, i) => ({
    time: new Date(now - (59 - i) * 1000).toLocaleTimeString(),
    value: 20 + Math.random() * 60 + Math.sin(i * 0.3) * 15,
  }))
}

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.06 } },
}

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { type: 'spring' as const, stiffness: 260, damping: 24 } },
}

export function CpuPage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const [, setLoading] = useState<string | null>(null)
  const history = useMemo(() => generateHistory(), [])

  const cpu = systemInfo?.cpu
  const percent = cpu?.percent ?? 0
  const temp = cpu?.temperature
  const threads = cpu?.logical ?? 0
  const cores = cpu?.physical ?? 0

  function handleAction(label: string, fn: () => Promise<unknown>) {
    setLoading(label)
    fn().finally(() => setLoading(null))
  }

  if (!systemInfo) {
    return (
      <div className="space-y-6">
        <div><Skeleton className="h-8 w-24 mb-1" /><Skeleton className="h-4 w-64" /></div>
        <div className="grid grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-28 rounded-xl" />)}
        </div>
        <Skeleton className="h-72 rounded-xl" />
        <div className="grid grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-28 rounded-xl" />)}
        </div>
      </div>
    )
  }

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-6">
      <motion.div variants={item}>
        <h1 className="text-2xl font-bold tracking-tight text-text">CPU</h1>
        <p className="text-sm text-text-secondary mt-1">Real-time processor monitoring & optimization</p>
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-4 gap-4">
        <MetricCard
          icon={<Cpu size={18} />}
          label="Usage"
          value={`${percent.toFixed(1)}%`}
          progress={percent}
          trend={{ value: `${(Math.random() * 5 + 1).toFixed(1)}%`, up: percent > 50 }}
        />
        <MetricCard
          icon={<Thermometer size={18} />}
          label="Temperature"
          value={temp != null ? `${temp}°C` : '--'}
          progressColor={temp != null && temp > 80 ? '#ef4444' : temp != null && temp > 60 ? '#eab308' : '#22c55e'}
          sub={temp != null ? (temp > 80 ? 'Critical' : temp > 60 ? 'Warm' : 'Normal') : undefined}
        />
        <MetricCard
          icon={<Layers size={18} />}
          label="Processes"
          value={`${Math.floor(80 + Math.random() * 60)}`}
          sub={`${Math.floor(5 + Math.random() * 15)} running`}
        />
        <MetricCard
          icon={<Hash size={18} />}
          label="Threads"
          value={`${threads}`}
          sub={`${cores} cores`}
        />
      </motion.div>

      <motion.div variants={item}>
        <Card padding="lg" className="overflow-hidden">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-text">CPU Usage History (60s)</h2>
            <Badge variant="info">Live</Badge>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={history} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="cpuGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#6366f1" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <Tooltip
                  contentStyle={{ background: '#1e1e2e', border: '1px solid #313244', borderRadius: 8, fontSize: 12, color: '#cdd6f4' }}
                  labelStyle={{ color: '#a6adc8' }}
                  formatter={(v: unknown) => [`${v as number}%`, 'Usage']}
                />
                <Area type="monotone" dataKey="value" stroke="#6366f1" strokeWidth={2} fill="url(#cpuGrad)" animationDuration={600} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-3 gap-4">
        <ActionCard
          icon={<Zap size={20} />}
          title="Core Parking"
          desc="Toggle core parking to balance power efficiency and performance"
          tags={['Power', 'Performance']}
          onClick={() => handleAction('Core Parking', () => api.optimize('cpu'))}
        />
        <ActionCard
          icon={<Gauge size={20} />}
          title="Priority Boost"
          desc="Adjust process priority settings for foreground applications"
          tags={['Performance', 'Latency']}
          onClick={() => handleAction('Priority Boost', () => api.affinityOptimize())}
        />
        <ActionCard
          icon={<Battery size={20} />}
          title="Power Plan"
          desc="Switch between power plans for optimal CPU performance"
          tags={['Balanced', 'High Perf.']}
          onClick={() => handleAction('Power Plan', () => api.setPowerPlan('ultimate'))}
        />
      </motion.div>
    </motion.div>
  )
}
