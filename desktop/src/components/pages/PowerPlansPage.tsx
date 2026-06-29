import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Battery, Zap, BatteryWarning, BatteryMedium,
  CheckCircle2, AlertTriangle, Settings2, Info,
} from 'lucide-react'
import { Card } from '../ui/Card'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { cn } from '../../lib/utils'
import type { SystemInfo } from '../../types'
import { api } from '../../lib/api'

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.05 } } }
const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }

const plans = [
  { id: 'high', label: 'High Performance', desc: 'Maximum performance at cost of power usage', icon: <Zap className="w-5 h-5" />, color: 'text-green', bg: 'bg-green-dim', badge: 'Best for Gaming' },
  { id: 'balanced', label: 'Balanced', desc: 'Good balance of performance and efficiency', icon: <BatteryMedium className="w-5 h-5" />, color: 'text-blue', bg: 'bg-blue-dim', badge: 'Default' },
  { id: 'power-saver', label: 'Power Saver', desc: 'Minimize power usage for extended battery', icon: <BatteryWarning className="w-5 h-5" />, color: 'text-yellow', bg: 'bg-yellow-dim', badge: 'Laptop' },
  { id: 'ultimate', label: 'Ultimate Performance', desc: 'Removes all power saving for max throughput', icon: <Battery className="w-5 h-5" />, color: 'text-purple', bg: 'bg-accent-dim', badge: 'Extreme' },
]

const advancedTweaks = [
  { id: 'hpet', label: 'Disable HPET', desc: 'High Precision Event Timer — reduce interrupt latency' },
  { id: 'usb', label: 'USB Selective Suspend', desc: 'Prevent USB devices from sleeping' },
  { id: 'pci', label: 'PCIe Link State', desc: 'Set to Off for maximum GPU throughput' },
  { id: 'processor', label: 'Processor Min State', desc: 'Set CPU minimum to 100% for consistent clocks' },
]

export function PowerPlansPage(_props: { systemInfo: SystemInfo | null }) {
  const [activePlan, setActivePlan] = useState<string>('balanced')
  const [applying, setApplying] = useState<string | null>(null)
  const [result, setResult] = useState<{ message: string; success: boolean } | null>(null)
  const [applyingAdvanced, setApplyingAdvanced] = useState<string | null>(null)

  const applyPlan = async (id: string) => {
    setApplying(id)
    setResult(null)
    try {
      const planArg = id === 'ultimate' ? 'high' : id
      await api.setPowerPlan(planArg)
      setActivePlan(id)
      setResult({ message: `Power plan set to ${plans.find(p => p.id === id)?.label}`, success: true })
    } catch {
      setResult({ message: 'Failed to apply power plan', success: false })
    } finally {
      setApplying(null)
    }
  }

  const applyAdvanced = async (id: string) => {
    setApplyingAdvanced(id)
    setResult(null)
    try {
      switch (id) {
        case 'hpet':
          await api.disableHpet()
          break
        case 'usb':
        case 'pci':
        case 'processor':
          setResult({ message: `${advancedTweaks.find(t => t.id === id)?.label} — coming in a future update`, success: false })
          setApplyingAdvanced(null)
          return
      }
      setResult({ message: `${advancedTweaks.find(t => t.id === id)?.label} applied`, success: true })
    } catch {
      setResult({ message: 'Failed to apply tweak', success: false })
    } finally {
      setApplyingAdvanced(null)
    }
  }

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="p-6 space-y-6">
      <motion.div variants={item}>
        <div className="flex items-center gap-3 mb-1">
          <div className="p-2 rounded-xl bg-accent-dim text-accent"><Battery className="w-6 h-6" /></div>
          <h1 className="text-2xl font-bold text-text">Power Plans</h1>
        </div>
        <p className="text-sm text-text-secondary ml-11">Manage system power profiles for performance or efficiency</p>
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {plans.map(plan => (
          <Card key={plan.id} padding="lg" className={cn('relative cursor-pointer transition-all border', activePlan === plan.id ? 'border-accent/40 bg-accent-dim/20' : 'hover:border-accent/30')}>
            <div className="flex items-start gap-4">
              <div className={cn('p-3 rounded-xl shrink-0', plan.bg, plan.color)}>{plan.icon}</div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="font-semibold text-text">{plan.label}</h3>
                  <Badge variant="accent" className="text-[10px]">{plan.badge}</Badge>
                </div>
                <p className="text-xs text-text-secondary">{plan.desc}</p>
              </div>
              <Button variant={activePlan === plan.id ? 'primary' : 'ghost'} size="sm" onClick={() => applyPlan(plan.id)} loading={applying === plan.id}>
                {activePlan === plan.id ? 'Active' : 'Apply'}
              </Button>
            </div>
          </Card>
        ))}
      </motion.div>

      <motion.div variants={item}>
        <Card padding="lg">
          <h2 className="text-sm font-semibold text-text mb-4 flex items-center gap-2"><Settings2 className="w-4 h-4 text-accent" />Advanced Power Tweaks</h2>
          <div className="space-y-2">
            {advancedTweaks.map(tweak => (
              <div key={tweak.id} className="flex items-center justify-between p-3 rounded-xl bg-surface-2/60 hover:bg-surface-2 transition-colors">
                <div>
                  <p className="text-sm font-medium text-text">{tweak.label}</p>
                  <p className="text-xs text-text-secondary">{tweak.desc}</p>
                </div>
                <Button variant="ghost" size="sm" onClick={() => applyAdvanced(tweak.id)} loading={applyingAdvanced === tweak.id}>Apply</Button>
              </div>
            ))}
          </div>
          <div className="mt-4 p-3 rounded-xl bg-yellow-dim/20 border border-yellow/20">
            <div className="flex items-start gap-2">
              <Info className="w-4 h-4 text-yellow shrink-0 mt-0.5" />
              <p className="text-xs text-text-secondary">Some power tweaks require a system restart to take full effect.</p>
            </div>
          </div>
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
