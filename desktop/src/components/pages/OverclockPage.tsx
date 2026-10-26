import { useState } from 'react'
import { motion } from 'framer-motion'
import { Zap, Cpu, Thermometer, Gauge, Clock, Battery, SlidersHorizontal, Ban } from 'lucide-react'
import { Card } from '../ui/Card'
import { Button } from '../ui/Button'
import { MetricCard } from '../ui/MetricCard'
import { ActionCard } from '../ui/ActionCard'
import { Skeleton } from '../ui/Skeleton'
import { PageHero } from '../ui/PageHero'
import { cn } from '../../lib/utils'
import { api } from '../../lib/api'
import type { SystemInfo } from '../../types'

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.06 } },
}

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
}

const POWER_PLANS = [
  { id: 'balanced', label: 'Balanced' },
  { id: 'high-performance', label: 'High Perf.' },
  { id: 'ultimate', label: 'Ultimate' },
  { id: 'power-saver', label: 'Power Saver' },
]

export function OverclockPage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const [loadingAction, setLoadingAction] = useState<string | null>(null)
  const [powerPlan, setPowerPlan] = useState<string | null>(null)
  const [result, setResult] = useState<{ key: string; message: string; success: boolean } | null>(null)


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

  const handlePowerPlan = async (plan: string) => {
    setPowerPlan(plan)
    await runAction(`plan-${plan}`, () => api.setPowerPlan(plan), `Power plan set to ${plan}`)
  }

  if (!systemInfo) {
    return (
      <div className="space-y-6">
        <div><Skeleton className="h-8 w-56 mb-1" /><Skeleton className="h-4 w-64" /></div>
        <div className="grid grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-28 rounded-xl" />)}
        </div>
        <Skeleton className="h-40 rounded-xl" />
        <div className="grid grid-cols-2 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-32 rounded-xl" />)}
        </div>
      </div>
    )
  }

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="page space-y-6">
      <motion.div variants={item}>
        <PageHero
          title="Overclock & Tuning"
          subtitle="Push hardware to limits"
          icon={<Zap size={19} />}
        />
      </motion.div>

      {/* Only readings the backend actually exposes. The old tile row invented
          clock, BCLK, Vcore, TDP and memory timings with Math.random(). */}
      <motion.div variants={item} className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <MetricCard icon={<Gauge size={18} />} label="CPU load" value={`${systemInfo.cpu.percent}%`} sub="Current utilisation" />
        <MetricCard
          icon={<Thermometer size={18} />}
          label="CPU temp"
          value={systemInfo.cpu.temperature != null ? `${systemInfo.cpu.temperature}°C` : '—'}
          sub={systemInfo.cpu.temperature != null ? 'Processor' : 'No sensor exposed'}
        />
        <MetricCard icon={<Cpu size={18} />} label="Cores" value={`${systemInfo.cpu.physical}C / ${systemInfo.cpu.logical}T`} sub="Physical / logical" />
        <MetricCard
          icon={<Gauge size={18} />}
          label="GPU load"
          value={systemInfo.gpu?.usage != null ? `${systemInfo.gpu.usage}%` : '—'}
          sub={systemInfo.gpu?.name || 'Not detected'}
        />
        <MetricCard
          icon={<Thermometer size={18} />}
          label="GPU temp"
          value={systemInfo.gpu?.temperature != null ? `${systemInfo.gpu.temperature}°C` : '—'}
          sub={systemInfo.gpu?.temperature != null ? 'Graphics card' : 'No sensor exposed'}
        />
        <MetricCard icon={<Clock size={18} />} label="Memory" value={`${systemInfo.memory.used_gb.toFixed(1)} / ${systemInfo.memory.total_gb.toFixed(0)} GB`} sub="In use" />
      </motion.div>

      <p className="text-[11px] text-text-tertiary">
        Core clock, voltage, power limit and memory timings are not exposed by the backend, so this
        page shows no values for them.
      </p>

      <motion.div variants={item}>
        <Card padding="lg">
          <div className="flex items-center gap-2 mb-4">
            <Battery className="w-5 h-5 text-accent" />
            <h2 className="text-sm font-semibold text-text">Power Plan</h2>
          </div>
          <div className="flex flex-wrap gap-2">
            {POWER_PLANS.map(plan => (
              <Button
                key={plan.id}
                variant={powerPlan === plan.id ? 'primary' : 'secondary'}
                size="sm"
                loading={loadingAction === `plan-${plan.id}`}
                onClick={() => handlePowerPlan(plan.id)}
              >
                {plan.label}
              </Button>
            ))}
          </div>
        </Card>
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ActionCard
          icon={<SlidersHorizontal size={20} />}
          title="Full Hardware Tuning"
          desc="Auto-tune CPU, memory, and bus for peak performance"
          tags={['Overclock', 'Auto']}
          onClick={() => runAction('tuning', () => api.optimize('overclock'), 'Hardware tuning applied')}
        />
        <ActionCard
          icon={<Ban size={20} />}
          title="Disable HPET"
          desc="Disable High Precision Event Timer for lower latency"
          tags={['Timing', 'Latency']}
          onClick={() => runAction('hpet', () => api.disableHpet(), 'HPET disabled')}
        />
        <ActionCard
          icon={<Zap size={20} />}
          title="Ultimate Power Plan"
          desc="Enable the hidden ultimate performance power plan"
          tags={['Power']}
          onClick={() => runAction('ultimate', () => api.setPowerPlan('ultimate'), 'Ultimate power plan activated')}
        />
        <ActionCard
          icon={<Clock size={20} />}
          title="CPU Timing"
          desc="Adjust timing parameters for reduced latency"
          tags={['Timing', 'Advanced']}
          onClick={() => runAction('timing', () => api.affinityOptimize(), 'CPU timing optimized')}
        />
      </motion.div>

      {result && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className={cn('p-4 rounded-xl border', result.success ? 'bg-green-dim border-green/30' : 'bg-red-dim border-red/30')}>
          <div className="flex items-center gap-3">
            <div className={cn('w-2 h-2 rounded-full', result.success ? 'bg-green' : 'bg-red')} />
            <p className={cn('text-sm font-medium', result.success ? 'text-green' : 'text-red')}>{result.message}</p>
          </div>
        </motion.div>
      )}
    </motion.div>
  )
}
