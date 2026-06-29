import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  Cpu, Monitor, Info, CheckCircle2, AlertTriangle,
  RefreshCw, ChevronRight,
} from 'lucide-react'
import { Card } from '../ui/Card'
import { MetricCard } from '../ui/MetricCard'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { Skeleton } from '../ui/Skeleton'
import { cn } from '../../lib/utils'
import type { SystemInfo } from '../../types'
import { api } from '../../lib/api'

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.05 } } }
const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }

export function BiosPage(_props: { systemInfo: SystemInfo | null }) {
  const [info, setInfo] = useState<{ motherboard: Record<string, string>; bios_vendor: string } | null>(null)
  const [recommendations, setRecommendations] = useState<{ name: string; setting: string; description: string }[]>([])
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState<{ text: string; type: string } | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [inf, rec] = await Promise.all([api.biosInfo(), api.biosRecommendations()])
      setInfo(inf)
      setRecommendations(rec.recommendations || [])
    } catch {
      setMessage({ text: 'Failed to load BIOS info', type: 'error' })
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="p-6 space-y-6">
      <motion.div variants={item}>
        <div className="flex items-center gap-3 mb-1">
          <div className="p-2 rounded-xl bg-accent-dim text-accent"><Cpu className="w-6 h-6" /></div>
          <h1 className="text-2xl font-bold text-text">BIOS Optimization</h1>
        </div>
        <p className="text-sm text-text-secondary ml-11">Motherboard-specific BIOS/UEFI recommendations</p>
      </motion.div>

      {loading ? (
        <motion.div variants={item} className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} variant="rectangular" height="100px" />)}
        </motion.div>
      ) : (
        <>
          <motion.div variants={item} className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <MetricCard icon={<Cpu className="w-5 h-5" />} label="Motherboard" value={info?.motherboard?.manufacturer ?? 'Unknown'} sub={info?.motherboard?.model ?? ''} />
            <MetricCard icon={<Monitor className="w-5 h-5" />} label="BIOS Version" value={info?.bios_vendor ?? 'Unknown'} sub="System firmware" />
            <MetricCard icon={<Info className="w-5 h-5" />} label="Recommendations" value={String(recommendations.length)} sub="Optimization settings" />
          </motion.div>

          <motion.div variants={item}>
            <Card padding="lg">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-semibold text-text">{info?.motherboard?.manufacturer} BIOS Recommendations</h2>
                <Button variant="ghost" size="sm" icon={<RefreshCw className="w-3 h-3" />} onClick={load}>Refresh</Button>
              </div>
              <div className="space-y-2">
                {recommendations.map((rec, i) => (
                  <div key={i} className="flex items-center gap-3 p-3 rounded-xl bg-surface-2/60 hover:bg-surface-2 transition-colors">
                    <div className="p-2 rounded-lg bg-surface-3 text-accent shrink-0"><ChevronRight className="w-4 h-4" /></div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium text-text">{rec.name}</p>
                        <Badge variant="accent" className="text-[10px]">{rec.setting}</Badge>
                      </div>
                      <p className="text-xs text-text-secondary mt-0.5">{rec.description}</p>
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-4 p-4 rounded-xl bg-yellow-dim/20 border border-yellow/20">
                <div className="flex items-start gap-3">
                  <Info className="w-5 h-5 text-yellow shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-text">Manual Application Required</p>
                    <p className="text-xs text-text-secondary mt-1">BIOS settings cannot be applied from Windows. Restart your PC and enter BIOS/UEFI setup (usually F2, Del, or F12) to apply these settings manually.</p>
                  </div>
                </div>
              </div>
            </Card>
          </motion.div>

          <motion.div variants={item}>
            <Card padding="lg">
              <h2 className="text-sm font-semibold text-text mb-3">Application Steps</h2>
              <ol className="space-y-2">
                {[
                  'Restart PC and enter BIOS (F2, Del, or F12)',
                  'Navigate to Advanced / Overclocking section',
                  'Apply each recommended setting',
                  'Save and exit (F10)',
                  'Test stability with stress tests',
                ].map((step, i) => (
                  <li key={i} className="flex items-center gap-3 text-sm">
                    <span className="flex items-center justify-center w-6 h-6 rounded-full bg-accent-dim text-accent text-xs font-bold shrink-0">{i + 1}</span>
                    <span className="text-text-secondary">{step}</span>
                  </li>
                ))}
              </ol>
            </Card>
          </motion.div>
        </>
      )}

      {message && (
        <motion.div variants={item} className={cn('p-4 rounded-xl border', message.type === 'error' ? 'bg-red-dim/10 border-red' : 'bg-green-dim/10 border-green')}>
          <div className="flex items-center gap-3">
            {message.type === 'error' ? <AlertTriangle className="w-5 h-5 text-red" /> : <CheckCircle2 className="w-5 h-5 text-green" />}
            <span className="text-sm text-text">{message.text}</span>
          </div>
        </motion.div>
      )}
    </motion.div>
  )
}
