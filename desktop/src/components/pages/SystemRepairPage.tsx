import { useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  Wrench, Shield, HardDrive, Clock,
  Power, Cpu, ToggleRight, Search, Activity
} from 'lucide-react'
import { Card } from '../ui/Card'
import { Button } from '../ui/Button'
import { Skeleton } from '../ui/Skeleton'
import { cn, formatUptime } from '../../lib/utils'
import { api } from '../../lib/api'

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.05 } }}

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 }}

export function SystemRepairPage() {
  const [loading, setLoading] = useState<string | null>(null)
  const [result, setResult] = useState<{ key: string; message: string; success: boolean } | null>(null)
  const [checkDiskDrive, setCheckDiskDrive] = useState('C:')

  // Startup timer
  const [startupData, setStartupData] = useState<{
    uptime_seconds: number
    uptime_formatted: string
    boot_time: string
    startup_processes: { name: string; pid: number; start_time: string; cpu: number }[]
    total_startup_processes: number
  } | null>(null)

  // Context menu
  const [contextItems, setContextItems] = useState<{ key: string; name: string; command: string; location: string; disabled?: boolean }[]>([])
  const [contextLoading, setContextLoading] = useState(false)

  const runAction = async (key: string, fn: () => Promise<unknown>, successMsg: string) => {
    setLoading(key)
    setResult(null)
    try {
      await fn()
      setResult({ key, message: successMsg, success: true })
    } catch (e) {
      setResult({ key, message: e instanceof Error ? e.message : 'Operation failed', success: false })
    } finally {
      setLoading(null)
    }
  }

  const loadStartupTimer = useCallback(async () => {
    setLoading('startup-timer')
    try {
      const res = await api.startupTimer()
      setStartupData(res)
    } catch { /* ignore */ }
    setLoading(null)
  }, [])

  const loadContextMenu = useCallback(async () => {
    setContextLoading(true)
    try {
      const res = await api.contextMenu()
      setContextItems(res.items.map(i => ({ ...i, disabled: false })))
    } catch { /* ignore */ }
    setContextLoading(false)
  }, [])

  const toggleContextItem = async (key: string, enable: boolean) => {
    setContextItems(prev => prev.map(i => i.key === key ? { ...i, disabled: true } : i))
    try {
      if (enable) await api.contextMenuEnable(key)
      else await api.contextMenuDisable(key)
      setContextItems(prev => prev.map(i => i.key === key ? { ...i, disabled: false } : i))
    } catch {
      setContextItems(prev => prev.map(i => i.key === key ? { ...i, disabled: false } : i))
    }
  }

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-6">
      <motion.div variants={item}>
        <div className="flex items-center gap-3 mb-1">
          <Wrench className="w-6 h-6 text-accent" />
          <h1 className="text-2xl font-bold tracking-tight text-text">System Repair</h1>
        </div>
        <p className="text-sm text-text-secondary ml-9">Repair tools, startup analyzer, and context menu manager</p>
      </motion.div>

      {/* Windows Repair */}
      <motion.div variants={item}>
        <Card padding="lg">
          <div className="flex items-center gap-2 mb-4">
            <Shield className="w-5 h-5 text-accent" />
            <h2 className="text-sm font-semibold text-text">Windows Repair</h2>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="primary"
              icon={<Activity className="w-4 h-4" />}
              loading={loading === 'sfc'}
              onClick={() => runAction('sfc', () => api.repairSfc(), 'SFC scan completed')}
            >
              SFC Scan Now
            </Button>
            <Button
              variant="secondary"
              icon={<Wrench className="w-4 h-4" />}
              loading={loading === 'dism'}
              onClick={() => runAction('dism', () => api.repairDism(), 'DISM restore health completed')}
            >
              DISM Restore Health
            </Button>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={checkDiskDrive}
                onChange={e => setCheckDiskDrive(e.target.value)}
                className="w-16 px-2 py-1.5 rounded-lg bg-surface-2 border border-border text-sm text-text text-center focus:outline-none focus:border-accent"
              />
              <Button
                variant="secondary"
                icon={<HardDrive className="w-4 h-4" />}
                loading={loading === 'chkdsk'}
                onClick={() => runAction('chkdsk', () => api.repairCheckDisk(checkDiskDrive), `Check disk on ${checkDiskDrive} completed`)}
              >
                Check Disk
              </Button>
            </div>
          </div>
        </Card>
      </motion.div>

      {/* Startup Timer */}
      <motion.div variants={item}>
        <Card padding="lg">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-accent" />
              <h2 className="text-sm font-semibold text-text">Startup Timer</h2>
            </div>
            <Button
              size="sm"
              variant="secondary"
              icon={<Search className="w-4 h-4" />}
              loading={loading === 'startup-timer'}
              onClick={loadStartupTimer}
            >
              Load Timer Data
            </Button>
          </div>
          {startupData ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-xl bg-surface-2">
                  <p className="text-[11px] text-text-tertiary">Uptime</p>
                  <p className="text-sm font-medium text-text">{formatUptime(startupData.uptime_seconds)}</p>
                </div>
                <div className="p-3 rounded-xl bg-surface-2">
                  <p className="text-[11px] text-text-tertiary">Boot Time</p>
                  <p className="text-sm font-medium text-text">{startupData.boot_time}</p>
                </div>
              </div>
              <div>
                <p className="text-xs text-text-secondary mb-2">Startup Processes ({startupData.total_startup_processes})</p>
                <div className="divide-y divide-border max-h-[240px] overflow-y-auto">
                  {startupData.startup_processes.map((p) => (
                    <div key={p.pid || p.name} className="flex items-center justify-between py-2">
                      <div className="flex items-center gap-2 min-w-0 flex-1">
                        <Power className="w-3 h-3 text-text-tertiary shrink-0" />
                        <span className="text-sm text-text truncate">{p.name}</span>
                      </div>
                      <div className="flex items-center gap-3 shrink-0 text-xs text-text-secondary">
                        <span>{p.start_time}</span>
                        <span>{p.cpu.toFixed(1)}% CPU</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <p className="text-xs text-text-tertiary py-4 text-center">Click "Load Timer Data" to view startup timing info.</p>
          )}
        </Card>
      </motion.div>

      {/* Context Menu Manager */}
      <motion.div variants={item}>
        <Card padding="lg">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Cpu className="w-5 h-5 text-accent" />
              <h2 className="text-sm font-semibold text-text">Context Menu Manager</h2>
            </div>
            <Button
              size="sm"
              variant="secondary"
              icon={<Search className="w-4 h-4" />}
              loading={contextLoading}
              onClick={loadContextMenu}
            >
              Load Context Menu Items
            </Button>
          </div>
          {contextItems.length > 0 ? (
            <div className="divide-y divide-border max-h-[320px] overflow-y-auto">
              {contextItems.map((item, _) => (
                <div key={item.key} className="flex items-center justify-between py-3 first:pt-0 last:pb-0">
                  <div className="min-w-0 flex-1 mr-4">
                    <p className="text-sm font-medium text-text truncate">{item.name}</p>
                    <p className="text-[11px] text-text-tertiary truncate">{item.location}</p>
                  </div>
                  <button
                    onClick={() => toggleContextItem(item.key, false)}
                    className="text-text-secondary hover:text-text transition-colors shrink-0"
                    title="Disable"
                  >
                    <ToggleRight className="w-5 h-5 text-green" />
                  </button>
                </div>
              ))}
            </div>
          ) : !contextLoading ? (
            <p className="text-xs text-text-tertiary py-4 text-center">Click "Load Context Menu Items" to manage right-click entries.</p>
          ) : (
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-12 rounded-xl" />)}
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
