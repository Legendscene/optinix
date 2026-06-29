import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  Gamepad2, Play, Square, Cpu, Activity, Clock,
  CheckCircle2, AlertTriangle,
  Zap, RefreshCw, Target,
} from 'lucide-react'
import { Card } from '../ui/Card'
import { MetricCard } from '../ui/MetricCard'
import { ActionCard } from '../ui/ActionCard'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { cn } from '../../lib/utils'
import type { SystemInfo } from '../../types'
import { api } from '../../lib/api'

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.05 } } }
const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }

export function GameModePage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const [active, setActive] = useState(false)
  const [games, setGames] = useState<{ pid: number; name: string; cpu_percent: number }[]>([])
  const [gameCount, setGameCount] = useState(0)
  const [loading, setLoading] = useState(false)
  const [toggling, setToggling] = useState(false)
  const [result, setResult] = useState<{ message: string; success: boolean } | null>(null)

  const loadStatus = useCallback(async () => {
    setLoading(true)
    try {
      const [st, gr] = await Promise.all([api.gameModeStatus(), api.gameModeGames()])
      setActive(st.active)
      setGameCount(st.game_count)
      setGames(gr.games)
    } catch {
      setActive(false)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadStatus() }, [loadStatus])

  const toggle = async () => {
    setToggling(true)
    setResult(null)
    try {
      if (active) {
        const r = await api.gameModeDisable() as { success: boolean }
        setActive(false)
        setResult({ message: 'Game Mode disabled', success: r.success })
      } else {
        const r = await api.gameModeEnable() as { success: boolean }
        setActive(true)
        setResult({ message: 'Game Mode enabled', success: r.success })
      }
      loadStatus()
    } catch {
      setResult({ message: 'Toggle failed', success: false })
    } finally {
      setToggling(false)
    }
  }

  const refresh = () => { loadStatus() }

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="p-6 space-y-6">
      <motion.div variants={item} className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className={cn('p-2 rounded-xl', active ? 'bg-green-dim text-green' : 'bg-accent-dim text-accent')}>
              <Gamepad2 className="w-6 h-6" />
            </div>
            <h1 className="text-2xl font-bold text-text">Game Mode</h1>
            {active && <Badge variant="success">ACTIVE</Badge>}
          </div>
          <p className="text-sm text-text-secondary ml-11">Real-time game detection and performance optimization</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" icon={<RefreshCw className="w-4 h-4" />} onClick={refresh} loading={loading} size="sm" title="Refresh" />
          <Button variant={active ? 'danger' : 'primary'} icon={active ? <Square className="w-4 h-4" /> : <Play className="w-4 h-4" />} onClick={toggle} loading={toggling}>
            {active ? 'Disable' : 'Enable'}
          </Button>
        </div>
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard icon={<Gamepad2 className="w-5 h-5" />} label="Status" value={active ? 'Active' : 'Inactive'} sub={active ? 'Optimizing games' : 'Not running'} />
        <MetricCard icon={<Activity className="w-5 h-5" />} label="Games Detected" value={String(gameCount)} sub="Active game processes" />
        <MetricCard icon={<Cpu className="w-5 h-5" />} label="CPU Cores" value={String(systemInfo?.cpu.logical ?? 0)} sub="Available for affinity" />
        <MetricCard icon={<Clock className="w-5 h-5" />} label="Timer Resolution" value="1.0ms" sub="Target for gaming" />
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <ActionCard icon={<Target className="w-5 h-5" />} title="CPU Affinity" desc="Set game process to performance cores" tags={['Affinity']} variant="default" onClick={async () => { try { const r = await api.gameModeAffinity() as { success: boolean }; setResult({ message: 'Affinity optimized', success: r.success }) } catch { setResult({ message: 'Affinity failed', success: false }) } }} />
              <ActionCard icon={<Zap className="w-5 h-5" />} title="Core Parking" desc="Disable core parking for max throughput" tags={['Parking']} variant="default" onClick={async () => { try { const r = await api.gameModeCoreParking() as { success: boolean }; setResult({ message: 'Core parking disabled', success: r.success }) } catch { setResult({ message: 'Failed', success: false }) } }} />
              <ActionCard icon={<Clock className="w-5 h-5" />} title="Timer Resolution" desc="Set 1ms timer for low latency" tags={['Timer', 'HPET']} variant="default" onClick={async () => { try { const r = await api.gameModeTimerResolution(1.0) as { success: boolean }; setResult({ message: 'Timer resolution set', success: r.success }) } catch { setResult({ message: 'Failed', success: false }) } }} />
      </motion.div>

      <motion.div variants={item}>
        <Card padding="lg">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-text flex items-center gap-2"><Activity className="w-4 h-4 text-accent" />Detected Game Processes</h2>
            <Button variant="ghost" size="sm" icon={<RefreshCw className="w-3 h-3" />} onClick={refresh} loading={loading}>Refresh</Button>
          </div>
          {games.length > 0 ? (
            <div className="space-y-2">
              {games.map(g => (
                <div key={g.pid} className="flex items-center justify-between p-3 rounded-xl bg-surface-2/60">
                  <div className="flex items-center gap-3">
                    <Gamepad2 className="w-4 h-4 text-accent" />
                    <span className="text-sm font-medium text-text">{g.name}</span>
                    <Badge variant="accent">PID {g.pid}</Badge>
                  </div>
                  <span className="text-xs text-text-secondary">{g.cpu_percent.toFixed(1)}% CPU</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-8 text-center">
              <Gamepad2 className="w-10 h-10 text-text-tertiary mx-auto mb-3" />
              <p className="text-sm text-text-secondary">No game processes detected</p>
              <p className="text-xs text-text-tertiary mt-1">Launch a game and it will appear here</p>
            </div>
          )}
        </Card>
      </motion.div>

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
