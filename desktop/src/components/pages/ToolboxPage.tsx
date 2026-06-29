import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Globe,
  RefreshCw,
  Radio,
  Monitor,
  FileText,
  Menu,
  Wifi,
  Search,
} from 'lucide-react'
import { Card } from '../ui/Card'
import { ActionCard } from '../ui/ActionCard'
import { Skeleton } from '../ui/Skeleton'
import { cn } from '../../lib/utils'
import { api } from '../../lib/api'
import type { SystemInfo } from '../../types'

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.05 } },
}

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
}

const DNS_PROVIDERS = [
  { id: 'cloudflare', label: 'Cloudflare', ips: '1.1.1.1 / 1.0.0.1' },
  { id: 'google', label: 'Google', ips: '8.8.8.8 / 8.8.4.4' },
  { id: 'opendns', label: 'OpenDNS', ips: '208.67.222.222 / 208.67.220.220' },
  { id: 'quad9', label: 'Quad9', ips: '9.9.9.9 / 149.112.112.112' },
  { id: 'adguard', label: 'AdGuard', ips: '94.140.14.14 / 94.140.15.15' },
]

export function ToolboxPage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const [loadingAction, setLoadingAction] = useState<string | null>(null)
  const [result, setResult] = useState<{ key: string; message: string; success: boolean } | null>(null)
  const [pingOutput, setPingOutput] = useState<string | null>(null)

  const runAction = async (key: string, fn: () => Promise<unknown>, successMsg: string) => {
    setLoadingAction(key)
    setResult(null)
    setPingOutput(null)
    try {
      const res = await fn()
      if (key === 'ping') {
        setPingOutput((res as { output: string }).output)
      }
      setResult({ key, message: successMsg, success: true })
    } catch (e) {
      setResult({ key, message: e instanceof Error ? e.message : 'Operation failed', success: false })
    } finally {
      setLoadingAction(null)
    }
  }

  if (!systemInfo) {
    return (
      <div className="space-y-6">
        <div><Skeleton className="h-8 w-48 mb-1" /><Skeleton className="h-4 w-64" /></div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-36 rounded-xl" />)}
        </div>
      </div>
    )
  }

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-6">
      <motion.div variants={item}>
        <div className="flex items-center gap-3 mb-1">
          <Wifi className="w-6 h-6 text-accent" />
          <h1 className="text-2xl font-bold tracking-tight text-text">Toolbox</h1>
        </div>
        <p className="text-sm text-text-secondary ml-9">System utilities</p>
      </motion.div>

      <motion.div variants={item}>
        <Card padding="lg">
          <div className="flex items-center gap-2 mb-4">
            <Globe className="w-5 h-5 text-accent" />
            <h2 className="text-sm font-semibold text-text">DNS Provider</h2>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2">
            {DNS_PROVIDERS.map(p => (
              <button
                key={p.id}
                onClick={() => runAction(`dns-${p.id}`, () => api.dns(p.id), `DNS set to ${p.label}`)}
                disabled={loadingAction === `dns-${p.id}`}
                className={cn(
                  'flex flex-col items-start gap-1 p-3 rounded-xl border border-border bg-surface-2 hover:border-accent/50 hover:bg-surface-3 transition-colors text-left',
                  loadingAction === `dns-${p.id}` && 'opacity-50 cursor-not-allowed'
                )}
              >
                <span className="text-sm font-medium text-text">{p.label}</span>
                <span className="text-[10px] text-text-tertiary font-mono">{p.ips}</span>
              </button>
            ))}
          </div>
        </Card>
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <ActionCard
          icon={<RefreshCw size={20} />}
          title="Flush DNS"
          desc="Clear DNS resolver cache to resolve domain resolution issues"
          tags={['Network']}
          onClick={() => runAction('flushdns', () => api.flushDns(), 'DNS cache flushed')}
        />
        <ActionCard
          icon={<Radio size={20} />}
          title="Ping"
          desc="Test network latency to Google DNS (8.8.8.8)"
          tags={['Network', 'Diagnostic']}
          onClick={() => runAction('ping', () => api.ping(), 'Ping completed')}
        />
        <ActionCard
          icon={<Monitor size={20} />}
          title="Hardware Info"
          desc="View detailed system hardware specifications"
          tags={['System']}
          onClick={() => runAction('hardware', () => api.hardwareInfo(), 'Hardware info retrieved')}
        />
        <ActionCard
          icon={<FileText size={20} />}
          title="Office Telemetry"
          desc="Disable Microsoft Office telemetry and reporting"
          tags={['Privacy']}
          onClick={() => runAction('officetel', () => api.disableOfficeTelemetry(), 'Office telemetry disabled')}
        />
        <ActionCard
          icon={<Menu size={20} />}
          title="Classic Context Menu"
          desc="Restore Windows 10 style classic context menu"
          tags={['UI', 'Windows']}
          onClick={() => runAction('contextmenu', () => api.toggleContextMenu(true), 'Classic context menu restored')}
        />
        <ActionCard
          icon={<Search size={20} />}
          title="Network Diagnostics"
          desc="Run comprehensive network diagnostic checks"
          tags={['Diagnostic']}
          onClick={() => runAction('netdiag', () => api.optimize('network'), 'Network diagnostics completed')}
        />
      </motion.div>

      {pingOutput && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          <Card padding="lg">
            <div className="flex items-center gap-2 mb-2">
              <Radio className="w-4 h-4 text-accent" />
              <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">Ping Output</h3>
            </div>
            <pre className="text-xs text-text-secondary font-mono whitespace-pre-wrap leading-relaxed">{pingOutput}</pre>
          </Card>
        </motion.div>
      )}

      {result && !pingOutput && (
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
