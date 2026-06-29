import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Gamepad2,
  Zap,
  MousePointer2,
  Monitor,
  Cpu,
  Gauge,
} from 'lucide-react'
import { Card } from '../ui/Card'
import { MetricCard } from '../ui/MetricCard'
import { ActionCard } from '../ui/ActionCard'
import { Skeleton } from '../ui/Skeleton'
import { cn } from '../../lib/utils'
import type { SystemInfo } from '../../types'
import { api } from '../../lib/api'

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.05 } },
}

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
}

export function GamingPage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const [loadingAction, setLoadingAction] = useState<string | null>(null)
  const [result, setResult] = useState<{ key: string; message: string; success: boolean } | null>(null)
  const [toggles, setToggles] = useState({ gameDvr: false, gpuPriority: false, visualEffects: false })

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

  const toggleApiMap = { gameDvr: 'game_dvr', gpuPriority: 'gpu_priority', visualEffects: 'visual_effects' } as const

  const toggleSwitch = async (key: keyof typeof toggles) => {
    const next = !toggles[key]
    setToggles((prev) => ({ ...prev, [key]: next }))
    try {
      await api.tweakStateSet({ [toggleApiMap[key]]: next })
    } catch {
      setToggles((prev) => ({ ...prev, [key]: !next }))
    }
  }

  if (!systemInfo) {
    return (
      <div className="p-6 space-y-6">
        <div><Skeleton variant="text" width="200px" height="28px" /><Skeleton variant="text" width="300px" height="16px" className="mt-2" /></div>
        <div className="grid grid-cols-3 gap-4"><Skeleton variant="rectangular" height="120px" /><Skeleton variant="rectangular" height="120px" /><Skeleton variant="rectangular" height="120px" /></div>
        <div className="grid grid-cols-2 gap-4"><Skeleton variant="rectangular" height="160px" /><Skeleton variant="rectangular" height="160px" /></div>
        <Skeleton variant="rectangular" height="200px" />
      </div>
    )
  }

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="p-6 space-y-6">
      <motion.div variants={item}>
        <div className="flex items-center gap-3 mb-1">
          <Gamepad2 className="w-6 h-6 text-accent" />
          <h1 className="text-2xl font-bold text-text">Gaming</h1>
        </div>
        <p className="text-sm text-text-secondary ml-9">Optimize system for maximum FPS</p>
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-3 gap-4">
        <MetricCard icon={<Zap className="w-5 h-5" />} label="FPS Boost Ready" value="Ready" trend={{ value: 'optimized', up: true }} sub="All tweaks available" />
        <MetricCard icon={<Gauge className="w-5 h-5" />} label="Input Latency" value="Low" trend={{ value: '--', up: true }} sub="Current profile" />
        <MetricCard icon={<Cpu className="w-5 h-5" />} label="GPU Priority" value={toggles.gpuPriority ? 'High' : 'Normal'} sub="Toggle below to change" />
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-4">
        <ActionCard
          icon={<Zap className="w-5 h-5" />}
          title="Full Gaming Optimization"
          desc="Apply all gaming tweaks for maximum performance"
          tags={['Recommended']}
          onClick={() => runAction('gaming', () => api.optimize('gaming'), 'Gaming optimization applied')}
        />
        <ActionCard
          icon={<Monitor className="w-5 h-5" />}
          title="Disable DVR"
          desc="Turn off Windows Game DVR and background recording"
          tags={['FPS']}
          onClick={() => runAction('dvr', () => api.tweakStateSet({ 'game_dvr': false }), 'DVR disabled')}
        />
        <ActionCard
          icon={<MousePointer2 className="w-5 h-5" />}
          title="Disable Mouse Acceleration"
          desc="Remove pointer precision for raw input"
          tags={['Precision']}
          onClick={() => runAction('mouse', () => api.peripheralOptimize(), 'Mouse acceleration disabled')}
        />
        <ActionCard
          icon={<Gamepad2 className="w-5 h-5" />}
          title="Extreme Gaming Mode"
          desc="Maximum performance tuning — may affect stability"
          variant="danger"
          tags={['Extreme']}
          onClick={() => runAction('extreme', () => api.extreme(), 'Extreme gaming mode activated')}
        />
      </motion.div>

      <motion.div variants={item}>
        <Card>
          <h2 className="text-sm font-semibold text-text mb-4">Toggles</h2>
          <div className="divide-y divide-border">
            {[
              { key: 'gameDvr' as const, label: 'Game DVR', desc: 'Disable background recording and capture' },
              { key: 'gpuPriority' as const, label: 'GPU Priority', desc: 'Set GPU scheduling to high priority' },
              { key: 'visualEffects' as const, label: 'Visual Effects', desc: 'Disable animations and transparency' },
            ].map((t) => (
              <div key={t.key} className="flex items-center justify-between py-3 first:pt-0 last:pb-0">
                <div>
                  <p className="text-sm font-medium text-text">{t.label}</p>
                  <p className="text-xs text-text-tertiary">{t.desc}</p>
                </div>
                <button
                  onClick={() => toggleSwitch(t.key)}
                  className={cn(
                    'relative w-10 h-5 rounded-full transition-colors duration-200',
                    toggles[t.key] ? 'bg-accent' : 'bg-surface-3'
                  )}
                >
                  <motion.div
                    animate={{ x: toggles[t.key] ? 20 : 2 }}
                    transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                    className="absolute top-0.5 w-4 h-4 rounded-full bg-white shadow"
                  />
                </button>
              </div>
            ))}
          </div>
        </Card>
      </motion.div>

      {result && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className={cn('p-4 rounded-xl border', result.success ? 'bg-green-dim border-green/30' : 'bg-red-dim border-red/30')}>
          <div className="flex items-center gap-3">
            <div className={cn('w-2 h-2 rounded-full', result.success ? 'bg-green' : 'bg-red')} />
            <p className={cn('text-sm font-medium', result.success ? 'text-green' : 'text-red')}>{result.message}</p>
          </div>
        </motion.div>
      )}

      {loadingAction && (
        <div className="flex items-center gap-2 text-xs text-text-secondary">
          <svg className="animate-spin h-3 w-3 text-accent" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
          Applying tweaks...
        </div>
      )}
    </motion.div>
  )
}
