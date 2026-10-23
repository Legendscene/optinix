import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  Battery, Zap, BatteryWarning, BatteryMedium,
  CheckCircle2, AlertTriangle, Settings2, Info,
  Moon, Cpu, Usb, Network, Plus, RefreshCw,
} from 'lucide-react'
import { Card } from '../ui/Card'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { PageHero } from '../ui/PageHero'
import { cn } from '../../lib/utils'
import { api } from '../../lib/api'

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.05 } } }
const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }

const plans = [
  { id: 'high', label: 'High Performance', desc: 'Maximum performance at cost of power usage', icon: <Zap className="w-5 h-5" />, color: 'text-green', bg: 'bg-green-dim', badge: 'Best for Gaming' },
  { id: 'balanced', label: 'Balanced', desc: 'Good balance of performance and efficiency', icon: <BatteryMedium className="w-5 h-5" />, color: 'text-cyan', bg: 'bg-cyan-dim', badge: 'Default' },
  { id: 'power-saver', label: 'Power Saver', desc: 'Minimize power usage for extended battery', icon: <BatteryWarning className="w-5 h-5" />, color: 'text-yellow', bg: 'bg-yellow-dim', badge: 'Laptop' },
  { id: 'ultimate', label: 'Ultimate Performance', desc: 'Removes all power saving for max throughput', icon: <Battery className="w-5 h-5" />, color: 'text-violet', bg: 'bg-accent-dim', badge: 'Extreme' },
]

const SLEEP_OPTIONS = [1, 5, 15, 30, 60, 0]

export default function PowerCenterPage() {
  const [activePlan, setActivePlan] = useState('balanced')
  const [applying, setApplying] = useState<string | null>(null)
  const [result, setResult] = useState<{ message: string; success: boolean } | null>(null)
  const [battery, setBattery] = useState<{ is_laptop: boolean; charge_percent?: number; status?: string; estimated_remaining?: string } | null>(null)
  const [settings, setSettings] = useState<{ sleep_timeout: number; hibernate_enabled: boolean; usb_suspend: boolean; pcie_link_state: string; processor_min: number; processor_max: number } | null>(null)
  const [, setLoadingSettings] = useState(true)

  const loadData = useCallback(async () => {
    setLoadingSettings(true)
    try {
      const [plansRes, bat, set] = await Promise.all([
        api.powerPlans(),
        api.powerBattery(),
        api.powerSettings(),
      ])
      const active = plansRes.plans.find(p => p.is_active)
      if (active) setActivePlan(active.guid)
      setBattery(bat)
      setSettings(set)
    } catch {
      // use defaults
    } finally {
      setLoadingSettings(false)
    }
  }, [])

  useEffect(() => { loadData() }, [loadData])

  const applyPlan = async (id: string) => {
    setApplying(id)
    setResult(null)
    try {
      await api.setPowerPlan(id)
      setActivePlan(id)
      setResult({ message: `Power plan set to ${plans.find(p => p.id === id)?.label}`, success: true })
    } catch {
      setResult({ message: 'Failed to apply power plan', success: false })
    } finally {
      setApplying(null)
    }
  }

  const createHighPerf = async () => {
    setApplying('create')
    setResult(null)
    try {
      const res = await api.powerCreateHighPerf()
      setResult({ message: `High performance plan created (${res.guid.slice(0, 8)}…)`, success: true })
    } catch {
      setResult({ message: 'Failed to create high performance plan', success: false })
    } finally {
      setApplying(null)
    }
  }

  const toggleHibernate = async () => {
    if (!settings) return
    const enable = !settings.hibernate_enabled
    setApplying('hibernate')
    try {
      await api.powerToggleHibernate(enable)
      setSettings({ ...settings, hibernate_enabled: enable })
      setResult({ message: `Hibernate ${enable ? 'enabled' : 'disabled'}`, success: true })
    } catch {
      setResult({ message: 'Failed to toggle hibernate', success: false })
    } finally {
      setApplying(null)
    }
  }

  const toggleUsbSuspend = async () => {
    if (!settings) return
    const disable = !settings.usb_suspend
    setApplying('usb')
    try {
      await api.powerToggleUsbSuspend(disable)
      setSettings({ ...settings, usb_suspend: disable })
      setResult({ message: `USB suspend ${disable ? 'disabled' : 'enabled'}`, success: true })
    } catch {
      setResult({ message: 'Failed to toggle USB suspend', success: false })
    } finally {
      setApplying(null)
    }
  }

  const setPcieLink = async (state: string) => {
    setApplying('pcie')
    try {
      await api.powerSetPcieLink(state)
      setSettings({ ...settings!, pcie_link_state: state })
      setResult({ message: `PCIe link state set to ${state}`, success: true })
    } catch {
      setResult({ message: 'Failed to set PCIe link state', success: false })
    } finally {
      setApplying(null)
    }
  }

  const setSleep = async (minutes: number) => {
    setApplying('sleep')
    try {
      await api.powerSetSleep(minutes)
      setSettings({ ...settings!, sleep_timeout: minutes })
      setResult({ message: `Sleep timeout set to ${minutes === 0 ? 'Never' : `${minutes}min`}`, success: true })
    } catch {
      setResult({ message: 'Failed to set sleep timeout', success: false })
    } finally {
      setApplying(null)
    }
  }

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="page space-y-6">
            <motion.div variants={item}>
        <PageHero
          title="Power Center"
          subtitle="Manage power plans, sleep settings, and power policies"
          icon={<Battery size={19} />}
        />
      </motion.div>

      {battery?.is_laptop && (
        <motion.div variants={item}>
          <Card padding="lg" className="border-accent/30">
            <div className="flex items-center gap-4">
              <div className={cn('p-3 rounded-xl', (battery.charge_percent ?? 0) > 50 ? 'bg-green-dim text-green' : 'bg-yellow-dim text-yellow')}>
                <Battery className="w-6 h-6" />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-lg font-semibold text-text">{battery.charge_percent ?? '--'}%</span>
                  <Badge variant={(battery.charge_percent ?? 0) > 50 ? 'success' : 'warning'}>{battery.status ?? 'Unknown'}</Badge>
                </div>
                <p className="text-xs text-text-secondary">Estimated remaining: {battery.estimated_remaining ?? '--'}</p>
              </div>
            </div>
          </Card>
        </motion.div>
      )}

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

      <motion.div variants={item} className="flex gap-3">
        <Button variant="secondary" icon={<Plus className="w-4 h-4" />} onClick={createHighPerf} loading={applying === 'create'}>Create High Performance Plan</Button>
        <Button variant="ghost" icon={<RefreshCw className="w-4 h-4" />} onClick={loadData}>Refresh</Button>
      </motion.div>

      <motion.div variants={item}>
        <Card padding="lg">
          <h2 className="text-sm font-semibold text-text mb-4 flex items-center gap-2"><Settings2 className="w-4 h-4 text-accent" />Sleep & Hibernate Settings</h2>
          <div className="space-y-4">
            <div>
              <p className="text-xs font-medium text-text-secondary mb-2">Sleep timeout</p>
              <div className="flex gap-2 flex-wrap">
                {SLEEP_OPTIONS.map(m => (
                  <button key={m} onClick={() => setSleep(m)}
                    className={cn('px-3 py-1.5 rounded-lg text-xs font-medium transition-all', settings?.sleep_timeout === m ? 'bg-accent text-surface-0' : 'bg-surface-2 text-text-secondary hover:bg-surface-3')}
                  >
                    {m === 0 ? 'Never' : `${m}min`}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex items-center justify-between p-3 rounded-xl bg-surface-2/60">
              <div className="flex items-center gap-3">
                <Moon className="w-4 h-4 text-text-secondary" />
                <div>
                  <p className="text-sm font-medium text-text">Hibernate</p>
                  <p className="text-xs text-text-secondary">Allow system to hibernate after sleep</p>
                </div>
              </div>
              <Button variant="ghost" size="sm" onClick={toggleHibernate} loading={applying === 'hibernate'}>
                {settings?.hibernate_enabled ? 'Enabled' : 'Disabled'}
              </Button>
            </div>
          </div>
        </Card>
      </motion.div>

      <motion.div variants={item}>
        <Card padding="lg">
          <h2 className="text-sm font-semibold text-text mb-4 flex items-center gap-2"><Cpu className="w-4 h-4 text-accent" />Power Management Tweaks</h2>
          <div className="space-y-2">
            <div className="flex items-center justify-between p-3 rounded-xl bg-surface-2/60 hover:bg-surface-2 transition-colors">
              <div className="flex items-center gap-3">
                <Usb className="w-4 h-4 text-text-secondary" />
                <div>
                  <p className="text-sm font-medium text-text">USB Selective Suspend</p>
                  <p className="text-xs text-text-secondary">Prevent USB devices from entering suspend state</p>
                </div>
              </div>
              <Button variant="ghost" size="sm" onClick={toggleUsbSuspend} loading={applying === 'usb'}>
                {settings?.usb_suspend ? 'Disabled' : 'Enabled'}
              </Button>
            </div>
            <div className="flex items-center justify-between p-3 rounded-xl bg-surface-2/60 hover:bg-surface-2 transition-colors">
              <div className="flex items-center gap-3">
                <Network className="w-4 h-4 text-text-secondary" />
                <div>
                  <p className="text-sm font-medium text-text">PCIe Link State Power Management</p>
                  <p className="text-xs text-text-secondary">Control PCIe power saving for GPU throughput</p>
                </div>
              </div>
              <div className="flex gap-1">
                {['Off', 'Moderate', 'Maximum'].map(s => (
                  <button key={s} onClick={() => setPcieLink(s.toLowerCase())}
                    className={cn('px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all', settings?.pcie_link_state === s.toLowerCase() ? 'bg-accent text-surface-0' : 'bg-surface-2 text-text-secondary hover:bg-surface-3')}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
            <div className="p-3 rounded-xl bg-surface-2/60">
              <div className="flex items-center gap-3 mb-3">
                <Cpu className="w-4 h-4 text-text-secondary" />
                <div>
                  <p className="text-sm font-medium text-text">Processor Power Management</p>
                  <p className="text-xs text-text-secondary">Set min/max processor state (5% – 100%)</p>
                </div>
              </div>
              {settings && (
                <div className="flex items-center gap-4">
                  <div className="flex-1">
                    <p className="text-[10px] text-text-tertiary mb-1">Min: {settings.processor_min}%</p>
                    <input type="range" min={5} max={100} value={settings.processor_min} readOnly className="w-full accent-accent" />
                  </div>
                  <div className="flex-1">
                    <p className="text-[10px] text-text-tertiary mb-1">Max: {settings.processor_max}%</p>
                    <input type="range" min={5} max={100} value={settings.processor_max} readOnly className="w-full accent-accent" />
                  </div>
                </div>
              )}
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

      <motion.div variants={item} className="p-4 rounded-xl bg-yellow-dim/10 border border-yellow/20">
        <div className="flex items-start gap-2">
          <Info className="w-4 h-4 text-yellow shrink-0 mt-0.5" />
          <p className="text-xs text-text-secondary">Some power settings may require administrative privileges and a system restart to take effect.</p>
        </div>
      </motion.div>
    </motion.div>
  )
}
