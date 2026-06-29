import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  Clock, Calendar, CheckCircle2, AlertTriangle, Power,
  RefreshCw, Settings2, Save,
} from 'lucide-react'
import { Card } from '../ui/Card'
import { Button } from '../ui/Button'
import { cn } from '../../lib/utils'
import type { SystemInfo } from '../../types'
import { api } from '../../lib/api'

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.05 } } }
const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }

export function SchedulerPage(_props: { systemInfo: SystemInfo | null }) {
  const [enabled, setEnabled] = useState(false)
  const [interval, setInterval] = useState(6)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [result, setResult] = useState<{ message: string; success: boolean } | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const st = await api.schedulerStatus()
      setEnabled(st.enabled)
      setInterval(st.interval_hours || 6)
    } catch {
      setEnabled(false)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const save = async () => {
    setSaving(true)
    setResult(null)
    try {
      await api.optimize('scheduler')
      setResult({ message: `Scheduler ${enabled ? 'enabled' : 'disabled'} (every ${interval}h)`, success: true })
    } catch {
      setResult({ message: 'Failed to update scheduler', success: false })
    } finally {
      setSaving(false)
    }
  }

  const runNow = async () => {
    setSaving(true)
    setResult(null)
    try {
      await api.optimize('all')
      setResult({ message: 'Scheduled optimization run complete', success: true })
    } catch {
      setResult({ message: 'Run failed', success: false })
    } finally {
      setSaving(false)
    }
  }

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="p-6 space-y-6">
      <motion.div variants={item}>
        <div className="flex items-center gap-3 mb-1">
          <div className="p-2 rounded-xl bg-accent-dim text-accent"><Clock className="w-6 h-6" /></div>
          <h1 className="text-2xl font-bold text-text">Maintenance Scheduler</h1>
        </div>
        <p className="text-sm text-text-secondary ml-11">Schedule automatic optimization tasks</p>
      </motion.div>

      {loading ? (
        <motion.div variants={item} className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => <div key={i} className="h-20 rounded-xl bg-surface-2 animate-pulse" />)}
        </motion.div>
      ) : (
        <>
          <motion.div variants={item}>
            <Card padding="lg">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                  <div className={cn('p-2.5 rounded-lg', enabled ? 'bg-green-dim text-green' : 'bg-surface-2 text-text-tertiary')}>
                    <Power className="w-5 h-5" />
                  </div>
                  <div>
                    <p className="font-semibold text-text">Scheduled Maintenance</p>
                    <p className="text-xs text-text-secondary">Run optimizations automatically on a schedule</p>
                  </div>
                </div>
                <button onClick={() => setEnabled(!enabled)}
                  className={cn('relative w-11 h-6 rounded-full transition-colors', enabled ? 'bg-accent' : 'bg-surface-3')}
                >
                  <div className={cn('absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform', enabled ? 'translate-x-[22px]' : 'translate-x-0.5')} />
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <p className="text-xs font-medium text-text-secondary mb-2">Interval (hours)</p>
                  <div className="flex gap-2">
                    {[2, 4, 6, 12, 24].map(h => (
                      <button key={h} onClick={() => setInterval(h)}
                        className={cn('px-4 py-2 rounded-lg text-sm font-medium transition-all', interval === h ? 'bg-accent text-white' : 'bg-surface-2 text-text-secondary hover:bg-surface-3')}
                      >
                        {h}h
                      </button>
                    ))}
                  </div>
                </div>

                <div className="flex gap-3">
                  <Button icon={<Save className="w-4 h-4" />} onClick={save} loading={saving}>Save Schedule</Button>
                  <Button variant="ghost" icon={<RefreshCw className="w-4 h-4" />} onClick={runNow} loading={saving}>Run Now</Button>
                </div>
              </div>
            </Card>
          </motion.div>

          <motion.div variants={item} className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              { title: 'Daily Quick Clean', desc: 'Temp files, cache, logs', icon: <RefreshCw className="w-5 h-5" />, time: '~30s' },
              { title: 'Performance Tune', desc: 'Services, startup, network', icon: <Settings2 className="w-5 h-5" />, time: '~2min' },
              { title: 'Full Optimization', desc: 'All categories + deep clean', icon: <Calendar className="w-5 h-5" />, time: '~5min' },
            ].map((s, i) => (
              <Card key={i} padding="lg" className="hover:border-accent/30 transition-colors">
                <div className="p-2 rounded-lg bg-surface-2 text-accent mb-3 w-fit">{s.icon}</div>
                <p className="font-semibold text-text">{s.title}</p>
                <p className="text-xs text-text-secondary mt-1">{s.desc}</p>
                <div className="flex items-center gap-2 mt-3">
                  <Clock className="w-3 h-3 text-text-tertiary" />
                  <span className="text-[10px] text-text-tertiary">{s.time}</span>
                </div>
              </Card>
            ))}
          </motion.div>
        </>
      )}

      {result && (
        <motion.div variants={item} className={cn('p-4 rounded-xl border', result.success ? 'bg-green-dim/10 border-green' : 'bg-red-dim/10 border-red')}>
          <div className="flex items-center gap-3">
            {result.success ? <CheckCircle2 className="w-5 h-5 text-green" /> : <AlertTriangle className="w-5 h-5 text-red" />}
            <span className="text-sm text-text">{result.message}</span>
          </div>
        </motion.div>
      )}
    </motion.div>
  )
}
