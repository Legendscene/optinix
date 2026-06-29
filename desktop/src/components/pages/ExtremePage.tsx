import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Flame,
  AlertTriangle,
  Cpu,
  CpuIcon,
  Network,
  Server,
  RotateCcw,
  CheckCircle2,
} from 'lucide-react'
import { Card } from '../ui/Card'
import { Button } from '../ui/Button'
import { Skeleton } from '../ui/Skeleton'
import { cn } from '../../lib/utils'
import type { SystemInfo } from '../../types'
import { api } from '../../lib/api'

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.06 } },
}

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
}

const tweaks = [
  { icon: <Cpu className="w-4 h-4 text-red" />, category: 'CPU', items: ['Set CPU to high-performance mode', 'Disable CPU throttling', 'Disable C-States', 'Set processor scheduling to background services'] },
  { icon: <CpuIcon className="w-4 h-4 text-red" />, category: 'GPU', items: ['Set GPU to maximum performance', 'Disable GPU power-saving features', 'Force GPU scheduling', 'Disable hardware acceleration GPU scheduling (HAGS)'] },
  { icon: <Network className="w-4 h-4 text-red" />, category: 'Network', items: ['Optimize TCP/IP parameters', 'Disable Nagle algorithm', 'Increase network buffer sizes', 'Disable QoS bandwidth limit'] },
  { icon: <Server className="w-4 h-4 text-red" />, category: 'Services', items: ['Disable non-essential Windows services', 'Stop SysMain (Superfetch)', 'Disable Windows Search', 'Disable Print Spooler if unused'] },
]

export function ExtremePage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const [loadingAction, setLoadingAction] = useState<string | null>(null)
  const [result, setResult] = useState<{ key: string; message: string; success: boolean } | null>(null)
  const [activated, setActivated] = useState(false)

  const activateExtreme = async () => {
    setLoadingAction('extreme')
    setResult(null)
    try {
      await api.extreme()
      setActivated(true)
      setResult({ key: 'extreme', message: 'Extreme mode activated — system tuned for maximum performance', success: true })
    } catch (e) {
      setResult({ key: 'extreme', message: e instanceof Error ? e.message : 'Extreme mode failed', success: false })
    } finally {
      setLoadingAction(null)
    }
  }

  if (!systemInfo) {
    return (
      <div className="p-6 space-y-6">
        <div><Skeleton variant="text" width="250px" height="28px" /><Skeleton variant="text" width="300px" height="16px" className="mt-2" /></div>
        <Skeleton variant="rectangular" height="140px" />
        <Skeleton variant="rectangular" height="60px" />
        <div className="grid grid-cols-2 gap-4"><Skeleton variant="rectangular" height="200px" /><Skeleton variant="rectangular" height="200px" /></div>
      </div>
    )
  }

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="p-6 space-y-6">
      <motion.div variants={item}>
        <div className="flex items-center gap-3 mb-1">
          <Flame className="w-6 h-6 text-red" />
          <h1 className="text-2xl font-bold text-text">
            Extreme <span className="text-red">Mode</span>
          </h1>
        </div>
        <p className="text-sm text-text-secondary ml-9">Force maximum performance — use at your own risk</p>
      </motion.div>

      <motion.div variants={item}>
        <div className="p-5 rounded-xl border border-red/30 bg-red-dim/30">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-red shrink-0 mt-0.5" />
            <div>
              <h3 className="text-sm font-semibold text-red mb-1">Warning</h3>
              <p className="text-xs text-text-secondary leading-relaxed">
                Extreme mode disables power-saving features, throttling, and non-essential services.
                This may increase power consumption, heat, and fan noise. System stability may be affected.
                Create a restore point before proceeding.
              </p>
            </div>
          </div>
        </div>
      </motion.div>

      <motion.div variants={item} className="flex justify-center">
        <Button
          variant="danger"
          size="lg"
          loading={loadingAction === 'extreme'}
          disabled={activated}
          icon={<Flame className="w-5 h-5" />}
          onClick={activateExtreme}
          className={cn(
            'text-lg font-bold px-10 py-4 rounded-2xl tracking-wider',
            activated && 'opacity-50 cursor-not-allowed'
          )}
        >
          {activated ? 'EXTREME MODE ACTIVE' : 'ACTIVATE EXTREME MODE'}
        </Button>
      </motion.div>

      {result && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className={cn('p-4 rounded-xl border', result.success ? 'bg-green-dim border-green/30' : 'bg-red-dim border-red/30')}>
          <div className="flex items-center gap-3">
            <div className={cn('w-2 h-2 rounded-full', result.success ? 'bg-green' : 'bg-red')} />
            <p className={cn('text-sm font-medium', result.success ? 'text-green' : 'text-red')}>{result.message}</p>
          </div>
        </motion.div>
      )}

      {activated && (
        <motion.div variants={item} initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="flex items-center gap-2 justify-center py-2">
          <CheckCircle2 className="w-5 h-5 text-green" />
          <span className="text-sm font-medium text-green">Extreme mode is active — all tweaks applied</span>
        </motion.div>
      )}

      <motion.div variants={item} className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {tweaks.map((t) => (
          <Card key={t.category}>
            <div className="flex items-center gap-2 mb-3">
              {t.icon}
              <h3 className="text-sm font-semibold text-text">{t.category} Tweaks</h3>
            </div>
            <ul className="space-y-1.5">
              {t.items.map((i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-text-secondary">
                  <span className="text-red mt-0.5">›</span>
                  {i}
                </li>
              ))}
            </ul>
          </Card>
        ))}
      </motion.div>

      <motion.div variants={item}>
        <Card className="border border-border">
          <div className="flex items-center gap-3">
            <RotateCcw className="w-5 h-5 text-accent" />
            <div>
              <p className="text-sm font-medium text-text">Restore Point</p>
              <p className="text-xs text-text-tertiary mt-0.5">
                {activated
                  ? 'A system restore point was created before applying extreme tweaks'
                  : 'No restore point created yet. Run Extreme Mode to create one automatically.'}
              </p>
            </div>
          </div>
        </Card>
      </motion.div>
    </motion.div>
  )
}
