import { useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  Zap, Sparkles, Cpu, MemoryStick, HardDrive, Wifi,
  Shield, Gamepad2, RefreshCw, CheckCircle2, AlertTriangle,
  Loader2, Eraser, Settings2,
} from 'lucide-react'
import { Card } from '../ui/Card'
import { MetricCard } from '../ui/MetricCard'
import { Button } from '../ui/Button'
import { cn } from '../../lib/utils'
import type { SystemInfo } from '../../types'
import { api } from '../../lib/api'

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.04 } } }
const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }

const optimizations = [
  { id: 'cleanup', label: 'Cleanup', desc: 'Temp files, cache, Recycle Bin', icon: <Eraser className="w-5 h-5" />, color: 'text-green', bg: 'bg-green-dim' },
  { id: 'network', label: 'Network', desc: 'TCP/IP, DNS, latency optimization', icon: <Wifi className="w-5 h-5" />, color: 'text-blue', bg: 'bg-blue-dim' },
  { id: 'disk', label: 'Storage', desc: 'Disk cleanup, SSD trim, defrag', icon: <HardDrive className="w-5 h-5" />, color: 'text-yellow', bg: 'bg-yellow-dim' },
  { id: 'performance', label: 'Performance', desc: 'CPU, memory, power settings', icon: <Cpu className="w-5 h-5" />, color: 'text-purple', bg: 'bg-accent-dim' },
  { id: 'gaming', label: 'Gaming', desc: 'Game mode, GPU priority, DVR', icon: <Gamepad2 className="w-5 h-5" />, color: 'text-red', bg: 'bg-red-dim' },
  { id: 'security', label: 'Security', desc: 'Defender tuning, privacy settings', icon: <Shield className="w-5 h-5" />, color: 'text-cyan', bg: 'bg-cyan-dim' },
  { id: 'services', label: 'Services', desc: 'Disable non-essential services', icon: <Settings2 className="w-5 h-5" />, color: 'text-orange', bg: 'bg-orange-dim' },
  { id: 'startup', label: 'Startup', desc: 'Manage startup applications', icon: <RefreshCw className="w-5 h-5" />, color: 'text-pink', bg: 'bg-pink-dim' },
]

export function OneClickPage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const [selected, setSelected] = useState<Set<string>>(new Set(optimizations.map(o => o.id)))
  const [running, setRunning] = useState(false)
  const [results, setResults] = useState<{ cat: string; success: boolean; message: string }[]>([])
  const [progress, setProgress] = useState(0)

  const toggle = (id: string) => {
    const next = new Set(selected)
    if (next.has(id)) next.delete(id); else next.add(id)
    setSelected(next)
  }

  const runAll = useCallback(async () => {
    setRunning(true)
    setResults([])
    setProgress(0)
    const cats = optimizations.filter(o => selected.has(o.id))
    const res: { cat: string; success: boolean; message: string }[] = []

    for (let i = 0; i < cats.length; i++) {
      const cat = cats[i]
      try {
        await api.optimize(cat.id)
        res.push({ cat: cat.id, success: true, message: `${cat.label}: optimized` })
      } catch {
        res.push({ cat: cat.id, success: false, message: `${cat.label}: failed` })
      }
      setResults([...res])
      setProgress(Math.round(((i + 1) / cats.length) * 100))
    }
    setRunning(false)
  }, [selected])

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="p-6 space-y-6">
      <motion.div variants={item} className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="p-2 rounded-xl bg-accent-dim text-accent"><Zap className="w-6 h-6" /></div>
            <h1 className="text-2xl font-bold text-text">One Click Optimize</h1>
          </div>
          <p className="text-sm text-text-secondary ml-11">Apply all optimizations with a single click</p>
        </div>
        <Button
          variant="primary"
          size="lg"
          icon={running ? <Loader2 className="w-5 h-5 animate-spin" /> : <Sparkles className="w-5 h-5" />}
          onClick={runAll}
          disabled={selected.size === 0 || running}
        >
          {running ? `Optimizing... ${progress}%` : 'Optimize All'}
        </Button>
      </motion.div>

      {running && (
        <motion.div variants={item}>
          <div className="w-full h-2 rounded-full bg-surface-2 overflow-hidden">
            <motion.div className="h-full bg-accent rounded-full" initial={{ width: 0 }} animate={{ width: `${progress}%` }} transition={{ duration: 0.3 }} />
          </div>
        </motion.div>
      )}

      <motion.div variants={item} className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard icon={<Zap className="w-5 h-5" />} label="Selected" value={`${selected.size}/${optimizations.length}`} sub="Categories to optimize" />
        <MetricCard icon={<Cpu className="w-5 h-5" />} label="CPU" value={systemInfo ? `${systemInfo.cpu.percent}%` : '--'} sub="Current usage" />
        <MetricCard icon={<MemoryStick className="w-5 h-5" />} label="Memory" value={systemInfo ? `${systemInfo.memory.percent}%` : '--'} sub="Current usage" />
        <MetricCard icon={<HardDrive className="w-5 h-5" />} label="Storage" value={systemInfo ? `${systemInfo.disk[0]?.percent ?? 0}%` : '--'} sub="System drive" />
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {optimizations.map(opt => {
          const isSelected = selected.has(opt.id)
          const result = results.find(r => r.cat === opt.id)
          return (
            <button key={opt.id} onClick={() => !running && toggle(opt.id)}
              className={cn(
                'relative p-4 rounded-xl border text-left transition-all',
                isSelected ? 'border-accent/40 bg-accent-dim/40' : 'border-border bg-surface-1 hover:bg-surface-2',
                result?.success === false && 'border-red/40 bg-red-dim/10',
              )}
            >
              <div className="flex items-start justify-between mb-3">
                <div className={cn('p-2.5 rounded-lg', opt.bg, opt.color)}>{opt.icon}</div>
                {result?.success && <CheckCircle2 className="w-4 h-4 text-green shrink-0" />}
                {result?.success === false && <AlertTriangle className="w-4 h-4 text-red shrink-0" />}
                {!result && (
                  <div className={cn('w-4 h-4 rounded border-2', isSelected ? 'bg-accent border-accent' : 'border-text-tertiary')}>
                    {isSelected && <div className="w-full h-full flex items-center justify-center text-white text-[10px] font-bold">✓</div>}
                  </div>
                )}
              </div>
              <p className="text-sm font-semibold text-text">{opt.label}</p>
              <p className="text-xs text-text-secondary mt-0.5">{opt.desc}</p>
            </button>
          )
        })}
      </motion.div>

      {results.length > 0 && (
        <motion.div variants={item}>
          <Card padding="lg">
            <h2 className="text-sm font-semibold text-text mb-3 flex items-center gap-2"><CheckCircle2 className="w-4 h-4 text-green" />Results</h2>
            <div className="space-y-1">
              {results.map((r, i) => (
                <div key={i} className={cn('flex items-center gap-2 p-2 rounded-lg text-xs', r.success ? 'bg-green-dim/20 text-green' : 'bg-red-dim/20 text-red')}>
                  {r.success ? <CheckCircle2 className="w-3.5 h-3.5" /> : <AlertTriangle className="w-3.5 h-3.5" />}
                  {r.message}
                </div>
              ))}
            </div>
          </Card>
        </motion.div>
      )}
    </motion.div>
  )
}
