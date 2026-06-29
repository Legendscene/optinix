import { useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  Puzzle,
  Cpu,
  Wifi,
  HardDrive,
  Zap,
  Battery,
  Palette,
  Settings,
  Download,
  RefreshCw,
  Code,
  Plus,
  Trash2,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Info,
} from 'lucide-react'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { ActionCard } from '../ui/ActionCard'
import { Skeleton } from '../ui/Skeleton'
import { cn } from '../../lib/utils'
import type { SystemInfo } from '../../types'

interface Plugin {
  id: string
  name: string
  desc: string
  icon: React.ReactNode
  version: string
  author: string
  category: string
  status: 'installed' | 'available' | 'enabled'
  enabled: boolean
}

const mockPlugins: Plugin[] = [
  { id: 'sysmon', name: 'System Monitor', desc: 'Real-time system resource monitoring with alerts', icon: <Cpu className="w-5 h-5" />, version: '2.1.0', author: 'Optinix Team', category: 'Monitoring', status: 'enabled', enabled: true },
  { id: 'netanalyzer', name: 'Network Analyzer', desc: 'Deep packet inspection and traffic analysis', icon: <Wifi className="w-5 h-5" />, version: '1.3.2', author: 'Network Labs', category: 'Network', status: 'installed', enabled: false },
  { id: 'diskviz', name: 'Disk Visualizer', desc: 'Interactive disk usage treemap and cleanup', icon: <HardDrive className="w-5 h-5" />, version: '3.0.1', author: 'Storage Inc', category: 'Storage', status: 'available', enabled: false },
  { id: 'gpuoc', name: 'GPU Overclocker', desc: 'Safe GPU overclocking with stability testing', icon: <Zap className="w-5 h-5" />, version: '1.5.0', author: 'GPU Tools', category: 'Performance', status: 'installed', enabled: false },
  { id: 'battery', name: 'Battery Optimizer', desc: 'Extend laptop battery life with smart profiles', icon: <Battery className="w-5 h-5" />, version: '2.0.0', author: 'Mobile Labs', category: 'Power', status: 'available', enabled: false },
  { id: 'theme', name: 'Custom Theme Engine', desc: 'Create and share custom UI themes', icon: <Palette className="w-5 h-5" />, version: '1.0.0', author: 'Design Team', category: 'UI', status: 'installed', enabled: true },
]

export default function PluginsPage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const [plugins, setPlugins] = useState<Plugin[]>(mockPlugins)
  const [loadingAction, setLoadingAction] = useState<string | null>(null)
  const [result, setResult] = useState<{ key: string; message: string; success: boolean } | null>(null)
  const [filter, setFilter] = useState<'all' | 'installed' | 'available' | 'enabled'>('all')

  const runAction = useCallback(async (key: string, fn: () => Promise<unknown>, successMsg: string) => {
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
  }, [])

  const togglePlugin = useCallback(async (id: string) => {
    setLoadingAction(id)
    setPlugins(prev => prev.map(p => p.id === id ? { ...p, enabled: !p.enabled, status: !p.enabled ? 'enabled' : 'installed' } : p))
    setResult(null)
    try {
      await new Promise(r => setTimeout(r, 800))
      setResult({ key: id, message: `Plugin ${id} ${plugins.find(p => p.id === id)?.enabled ? 'disabled' : 'enabled'}`, success: true })
    } catch (e) {
      setResult({ key: id, message: e instanceof Error ? e.message : 'Failed', success: false })
    } finally {
      setLoadingAction(null)
    }
  }, [plugins])

  const installPlugin = useCallback(async (id: string) => {
    setLoadingAction(id)
    setResult(null)
    try {
      await new Promise(r => setTimeout(r, 1500))
      setPlugins(prev => prev.map(p => p.id === id ? { ...p, status: 'installed', enabled: true } : p))
      setResult({ key: id, message: 'Plugin installed successfully', success: true })
    } catch (e) {
      setResult({ key: id, message: e instanceof Error ? e.message : 'Failed', success: false })
    } finally {
      setLoadingAction(null)
    }
  }, [])

  const uninstallPlugin = useCallback(async (id: string) => {
    setLoadingAction(id)
    setResult(null)
    try {
      await new Promise(r => setTimeout(r, 800))
      setPlugins(prev => prev.map(p => p.id === id ? { ...p, status: 'available', enabled: false } : p))
      setResult({ key: id, message: 'Plugin uninstalled', success: true })
    } catch (e) {
      setResult({ key: id, message: e instanceof Error ? e.message : 'Failed', success: false })
    } finally {
      setLoadingAction(null)
    }
  }, [])

  const filteredPlugins = plugins.filter(p => {
    if (filter === 'all') return true
    if (filter === 'installed') return p.status === 'installed' || p.status === 'enabled'
    if (filter === 'available') return p.status === 'available'
    if (filter === 'enabled') return p.status === 'enabled'
    return true
  })

  if (!systemInfo) {
    return (
      <div className="p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <Skeleton variant="text" width="200px" height="28px" />
            <Skeleton variant="text" width="300px" height="16px" />
          </div>
          <Skeleton variant="circular" className="h-32 w-32" />
        </div>
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} variant="rectangular" height="120px" />)}
        </div>
      </div>
    )
  }

  return (
    <motion.div initial="hidden" animate="show" className="p-6 space-y-6">
      <motion.div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="p-2 rounded-xl bg-surface-2 text-accent"><Puzzle className="w-6 h-6" /></div>
            <h1 className="text-2xl font-bold text-text">Plugins</h1>
          </div>
          <p className="text-sm text-text-secondary ml-11">Extend functionality with plugins</p>
        </div>
        <Button variant="secondary" icon={<Plus className="w-4 h-4" />} onClick={() => runAction('install', async () => {}, 'Open plugin marketplace')}>Get More Plugins</Button>
      </motion.div>

      <motion.div className="flex items-center gap-2 mb-4">
        {(['all', 'installed', 'available', 'enabled'] as const).map(f => (
          <button key={f} onClick={() => setFilter(f)} className={cn('px-3 py-1.5 rounded-lg text-sm font-medium transition-colors', filter === f ? 'bg-accent text-white' : 'bg-surface-2 text-text-secondary hover:bg-surface-3 hover:text-text')}>
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </motion.div>

      <motion.div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredPlugins.map((plugin, i) => (
          <motion.div key={plugin.id} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }} className="relative p-5 rounded-2xl bg-surface-1 border border-border hover:border-accent/50 transition-colors">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="p-3 rounded-xl bg-surface-2 text-accent shrink-0">{plugin.icon}</div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold text-text">{plugin.name}</h3>
                    <Badge variant={plugin.status === 'enabled' ? 'success' : plugin.status === 'installed' ? 'info' : 'default'} className="text-[10px]">{plugin.status.charAt(0).toUpperCase() + plugin.status.slice(1)}</Badge>
                  </div>
                  <p className="text-xs text-text-tertiary">{plugin.author} • v{plugin.version}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={() => runAction('settings', async () => {}, `Open ${plugin.name} settings`)} className="p-1.5 rounded-lg bg-surface-2 text-text-secondary hover:bg-surface-3 hover:text-text transition-colors" title="Settings"><Settings className="w-4 h-4" /></button>
                {plugin.status === 'available' ? (
                  <Button variant="secondary" size="sm" icon={<Download className="w-3.5 h-3.5" />} loading={loadingAction === plugin.id} onClick={() => installPlugin(plugin.id)}>Install</Button>
                ) : plugin.enabled ? (
                  <Button variant="secondary" size="sm" icon={<ChevronDown className="w-3.5 h-3.5" />} loading={loadingAction === plugin.id} onClick={() => togglePlugin(plugin.id)}>Disable</Button>
                ) : (
                  <>
                    <Button variant="secondary" size="sm" icon={<ChevronUp className="w-3.5 h-3.5" />} loading={loadingAction === plugin.id} onClick={() => togglePlugin(plugin.id)}>Enable</Button>
                    <Button variant="ghost" size="sm" icon={<Trash2 className="w-3.5 h-3.5" />} loading={loadingAction === plugin.id} onClick={() => uninstallPlugin(plugin.id)} className="text-red hover:text-red/80">Uninstall</Button>
                  </>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2 text-xs text-text-secondary">
              <span className="px-2 py-0.5 rounded bg-surface-3 text-text-tertiary">{plugin.category}</span>
              <span className="text-surface-3">|</span>
              <span>v{plugin.version}</span>
            </div>
            <p className="text-xs text-text-secondary mt-3 leading-relaxed">{plugin.desc}</p>
          </motion.div>
        ))}
      </motion.div>

      <motion.div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <ActionCard icon={<Download className="w-5 h-5" />} title="Install from File" desc="Install a plugin from a local .zip or .oplg file" tags={['Local']} variant="default" onClick={() => runAction('local-install', async () => {}, 'Open file picker')} />
        <ActionCard icon={<RefreshCw className="w-5 h-5" />} title="Check for Updates" desc="Check all installed plugins for updates" tags={['Maintenance']} variant="default" onClick={() => runAction('updates', async () => {}, 'No updates available')} />
        <ActionCard icon={<Code className="w-5 h-5" />} title="Developer Mode" desc="Enable plugin development tools and debugging" tags={['Dev']} variant="default" onClick={() => runAction('devmode', async () => {}, 'Developer mode enabled')} />
      </motion.div>

      {result && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mt-4 p-4 rounded-xl border" style={{ borderColor: result.success ? '#22c55e' : '#ef4444', backgroundColor: result.success ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)' }}>
          <div className="flex items-center gap-3">
            <div className={cn('w-2 h-2 rounded-full', result.success ? 'bg-green' : 'bg-red')} />
            <span className="text-sm text-text">{result.message}</span>
          </div>
        </motion.div>
      )}

      <motion.div className="mt-6 p-4 rounded-xl bg-surface-1 border border-border">
        <h3 className="text-sm font-semibold text-text mb-3 flex items-center gap-2"><Info className="w-4 h-4 text-blue" />Plugin Development</h3>
        <p className="text-xs text-text-secondary mb-3">Build your own plugins with the Optinix Plugin SDK. TypeScript support, hot reload, and full API access.</p>
        <div className="flex gap-3">
          <Button variant="secondary" icon={<ExternalLink className="w-4 h-4" />} onClick={() => window.open('https://github.com/optinix/plugin-sdk', '_blank')}>View SDK Docs</Button>
          <Button variant="ghost" icon={<Plus className="w-4 h-4" />} onClick={() => runAction('create', async () => {}, 'Create plugin scaffold')}>Create New Plugin</Button>
        </div>
      </motion.div>
    </motion.div>
  )
}