import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Shield,
  ShieldCheck,
  ShieldAlert,
  Eye,
  Wifi,
  Settings,
  ToggleLeft,
  FileText,
} from 'lucide-react'
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

export function SecurityPage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const [loadingAction, setLoadingAction] = useState<string | null>(null)
  const [result, setResult] = useState<{ key: string; message: string; success: boolean } | null>(null)
  const [defenderOn, setDefenderOn] = useState(true)
  const [windowsUpdateOn, setWindowsUpdateOn] = useState(true)

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

  if (!systemInfo) {
    return (
      <div className="p-6 space-y-6">
        <div><Skeleton variant="text" width="200px" height="28px" /><Skeleton variant="text" width="300px" height="16px" className="mt-2" /></div>
        <div className="grid grid-cols-3 gap-4"><Skeleton variant="rectangular" height="120px" /><Skeleton variant="rectangular" height="120px" /><Skeleton variant="rectangular" height="120px" /></div>
        <div className="grid grid-cols-2 gap-4"><Skeleton variant="rectangular" height="160px" /><Skeleton variant="rectangular" height="160px" /></div>
      </div>
    )
  }

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="p-6 space-y-6">
      <motion.div variants={item}>
        <div className="flex items-center gap-3 mb-1">
          <Shield className="w-6 h-6 text-accent" />
          <h1 className="text-2xl font-bold text-text">Security</h1>
        </div>
        <p className="text-sm text-text-secondary ml-9">Harden your system and protect privacy</p>
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-3 gap-4">
        <MetricCard icon={<ShieldCheck className="w-5 h-5" />} label="Defender Status" value={defenderOn ? 'Active' : 'Disabled'} trend={{ value: defenderOn ? 'protected' : 'inactive', up: defenderOn }} sub="Real-time protection" />
        <MetricCard icon={<Wifi className="w-5 h-5" />} label="Firewall" value="Active" trend={{ value: 'secure', up: true }} sub="Inbound/outbound filtering" />
        <MetricCard icon={<Eye className="w-5 h-5" />} label="Privacy Score" value="82%" progress={82} progressColor="#22c55e" sub="Based on telemetry settings" />
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <ActionCard
          icon={<ShieldAlert className="w-5 h-5" />}
          title="Full Security Hardening"
          desc="Apply all security hardening measures"
          tags={['Recommended']}
          onClick={() => runAction('security', () => api.optimize('security'), 'Security hardening applied')}
        />
        <ActionCard
          icon={<ToggleLeft className="w-5 h-5" />}
          title="Toggle Windows Defender"
          desc={defenderOn ? 'Disable real-time protection' : 'Enable real-time protection'}
          tags={['Defender']}
          onClick={() => runAction('defender', () => api.toggleDefender(!defenderOn).then(() => setDefenderOn(!defenderOn)), `${defenderOn ? 'Disabled' : 'Enabled'} Defender`)}
        />
        <ActionCard
          icon={<Settings className="w-5 h-5" />}
          title="Toggle Windows Update"
          desc={windowsUpdateOn ? 'Pause updates and defer upgrades' : 'Re-enable Windows Update'}
          tags={['Updates']}
          onClick={() => runAction('wu', () => api.toggleWindowsUpdate(!windowsUpdateOn).then(() => setWindowsUpdateOn(!windowsUpdateOn)), `${windowsUpdateOn ? 'Paused' : 'Enabled'} Windows Update`)}
        />
        <ActionCard
          icon={<Eye className="w-5 h-5" />}
          title="Disable Telemetry"
          desc="Block data collection and diagnostic tracking"
          tags={['Privacy']}
          onClick={() => runAction('telemetry', () => api.optimize('security'), 'Telemetry disabled')}
        />
        <ActionCard
          icon={<FileText className="w-5 h-5" />}
          title="Office Telemetry"
          desc="Disable Microsoft Office telemetry services"
          tags={['Office', 'Privacy']}
          onClick={() => runAction('office', () => api.disableOfficeTelemetry(), 'Office telemetry disabled')}
        />
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
          Applying security changes...
        </div>
      )}
    </motion.div>
  )
}
