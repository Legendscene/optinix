import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  Server,
  RefreshCw,
  SlidersHorizontal,
  Zap,
} from 'lucide-react'
import { Card } from '../ui/Card'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { Skeleton } from '../ui/Skeleton'
import { cn } from '../../lib/utils'
import type { SystemInfo, Service } from '../../types'
import { api } from '../../lib/api'

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.03 } },
}

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
}

export function ServicesPage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const [services, setServices] = useState<Service[]>([])
  const [loading, setLoading] = useState(true)
  const [toggling, setToggling] = useState<string | null>(null)
  const [loadingAction, setLoadingAction] = useState<string | null>(null)
  const [result, setResult] = useState<{ message: string; success: boolean } | null>(null)

  const loadServices = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.services()
      setServices(res.services)
    } catch {
      setServices([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadServices() }, [loadServices])

  const toggleService = async (name: string, running: boolean) => {
    setToggling(name)
    try {
      await api.toggleService(name, !running)
      setServices((prev) => prev.map((s) => (s.name === name ? { ...s, running: !running } : s)))
    } catch (e) {
      setResult({ message: e instanceof Error ? e.message : `Failed to toggle ${name}`, success: false })
    } finally {
      setToggling(null)
    }
  }

  const runAction = async (key: string, fn: () => Promise<unknown>, successMsg: string) => {
    setLoadingAction(key)
    setResult(null)
    try {
      await fn()
      await loadServices()
      setResult({ message: successMsg, success: true })
    } catch (e) {
      setResult({ message: e instanceof Error ? e.message : 'Operation failed', success: false })
    } finally {
      setLoadingAction(null)
    }
  }

  const runningCount = services.filter((s) => s.running).length
  const safeCount = services.filter((s) => s.safe).length
  const criticalCount = services.filter((s) => !s.safe).length

  if (!systemInfo) {
    return (
      <div className="p-6 space-y-6">
        <div><Skeleton variant="text" width="200px" height="28px" /><Skeleton variant="text" width="300px" height="16px" className="mt-2" /></div>
        <div className="flex gap-2"><Skeleton variant="rectangular" width="100px" height="32px" /><Skeleton variant="rectangular" width="100px" height="32px" /></div>
        <Skeleton variant="rectangular" height="400px" />
      </div>
    )
  }

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="p-6 space-y-6">
      <motion.div variants={item}>
        <div className="flex items-center gap-3 mb-1">
          <Server className="w-6 h-6 text-accent" />
          <h1 className="text-2xl font-bold text-text">Services</h1>
        </div>
        <p className="text-sm text-text-secondary ml-9">Manage Windows services</p>
      </motion.div>

      <motion.div variants={item} className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs text-text-secondary">
            <span className="w-2 h-2 rounded-full bg-green" />
            {runningCount} running
          </div>
          <div className="flex items-center gap-1.5 text-xs text-text-secondary">
            <span className="w-2 h-2 rounded-full bg-green/50" />
            {safeCount} safe
          </div>
          <div className="flex items-center gap-1.5 text-xs text-text-secondary">
            <span className="w-2 h-2 rounded-full bg-red/50" />
            {criticalCount} critical
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" icon={<SlidersHorizontal className="w-4 h-4" />} loading={loadingAction === 'basic'} onClick={() => runAction('basic', () => api.debloat('basic'), 'Basic debloat applied')}>Basic Debloat</Button>
          <Button variant="danger" size="sm" icon={<Zap className="w-4 h-4" />} loading={loadingAction === 'advanced'} onClick={() => runAction('advanced', () => api.debloat('advanced'), 'Advanced debloat applied')}>Advanced Debloat</Button>
          <Button variant="ghost" size="sm" icon={<RefreshCw className="w-4 h-4" />} loading={loading} onClick={loadServices}>Refresh</Button>
        </div>
      </motion.div>

      <motion.div variants={item}>
        <Card padding="sm" className="max-h-[65vh] overflow-y-auto">
          {loading ? (
            <div className="space-y-2 p-2">
              {Array.from({ length: 10 }).map((_, i) => <Skeleton key={i} variant="rectangular" height="52px" />)}
            </div>
          ) : services.length === 0 ? (
            <p className="text-xs text-text-tertiary py-8 text-center">No services found</p>
          ) : (
            <div className="divide-y divide-border">
              {services.map((s) => (
                <motion.div
                  key={s.name}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex items-center justify-between py-2.5 px-2"
                >
                  <div className="flex-1 min-w-0 mr-4">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-text truncate">{s.name}</span>
                      <Badge variant={s.running ? 'success' : 'default'}>{s.running ? 'Running' : 'Stopped'}</Badge>
                      <Badge variant={s.safe ? 'info' : 'danger'}>{s.safe ? 'Safe' : 'Critical'}</Badge>
                    </div>
                    <p className="text-xs text-text-tertiary mt-0.5 truncate">{s.desc}</p>
                  </div>
                  <button
                    disabled={!s.safe || toggling === s.name}
                    onClick={() => toggleService(s.name, s.running)}
                    className={cn(
                      'relative w-10 h-5 rounded-full transition-colors duration-200 shrink-0',
                      s.running ? 'bg-accent' : 'bg-surface-3',
                      !s.safe && 'opacity-30 cursor-not-allowed'
                    )}
                  >
                    {toggling === s.name ? (
                      <svg className="absolute inset-0 m-auto animate-spin h-3 w-3 text-white" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
                    ) : (
                      <motion.div
                        animate={{ x: s.running ? 20 : 2 }}
                        transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                        className="absolute top-0.5 w-4 h-4 rounded-full bg-white shadow"
                      />
                    )}
                  </button>
                </motion.div>
              ))}
            </div>
          )}
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
    </motion.div>
  )
}
