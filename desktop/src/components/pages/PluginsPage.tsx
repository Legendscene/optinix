import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  Puzzle, Cpu, Wifi, HardDrive, Zap, Battery, Palette,
  Settings, Download, RefreshCw, Code, Plus, Trash2,
  ExternalLink, ChevronDown, ChevronUp, Info, CheckCircle2,
} from 'lucide-react'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { ActionCard } from '../ui/ActionCard'
import { Skeleton } from '../ui/Skeleton'
import { PageHero } from '../ui/PageHero'
import { cn } from '../../lib/utils'
import { api } from '../../lib/api'
import type { SystemInfo } from '../../types'

const FALLBACK_ICONS: Record<string, React.ReactNode> = {
  monitoring: <Cpu className="w-5 h-5" />,
  network: <Wifi className="w-5 h-5" />,
  storage: <HardDrive className="w-5 h-5" />,
  performance: <Zap className="w-5 h-5" />,
  power: <Battery className="w-5 h-5" />,
  ui: <Palette className="w-5 h-5" />,
}

/* Plugins installed before the manifest gained a category come back without
   one, so the lookup must tolerate a missing field instead of taking the
   whole page down on `undefined.toLowerCase()`. */
function pluginIcon(category?: string | null) {
  const key = (category ?? '').toLowerCase()
  return FALLBACK_ICONS[key] ?? <Puzzle className="w-5 h-5" />
}

interface PluginEntry {
  id: string
  name: string
  version: string
  author: string
  description: string
  category: string
  status: string
  enabled: boolean
}

export default function PluginsPage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const [plugins, setPlugins] = useState<PluginEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingAction, setLoadingAction] = useState<string | null>(null)
  const [result, setResult] = useState<{ key: string; message: string; success: boolean } | null>(null)
  const [filter, setFilter] = useState<'all' | 'installed' | 'available' | 'enabled'>('all')

  const loadPlugins = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.pluginList()
      setPlugins(res.plugins)
    } catch {
      setPlugins([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadPlugins() }, [loadPlugins])

  const runAction = useCallback(async (key: string, fn: () => Promise<unknown>, successMsg: string) => {
    setLoadingAction(key)
    setResult(null)
    try {
      await fn()
      setResult({ key, message: successMsg, success: true })
      await loadPlugins()
    } catch (e) {
      setResult({ key, message: e instanceof Error ? e.message : 'Operation failed', success: false })
    } finally {
      setLoadingAction(null)
    }
  }, [loadPlugins])

  const togglePlugin = useCallback(async (id: string) => {
    const p = plugins.find(p => p.id === id)
    if (!p) return
    await runAction(id, () => p.enabled ? api.pluginDisable(id) : api.pluginEnable(id), `${p.name} ${p.enabled ? 'disabled' : 'enabled'}`)
  }, [plugins, runAction])

  const installPlugin = useCallback(async (id: string) => {
    await runAction(id, () => api.pluginLoad(id), `Plugin ${id} loaded`)
  }, [runAction])

  const uninstallPlugin = useCallback(async (id: string) => {
    await runAction(id, () => api.pluginUnload(id), `Plugin ${id} unloaded`)
  }, [runAction])

  const filteredPlugins = plugins.filter(p => {
    if (filter === 'all') return true
    if (filter === 'installed') return p.status === 'installed' || p.status === 'enabled'
    if (filter === 'available') return p.status === 'available'
    if (filter === 'enabled') return p.status === 'enabled'
    return true
  })

  if (!systemInfo) {
    return (
      <div className="page space-y-6">
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <Skeleton variant="text" width="200px" height="28px" />
            <Skeleton variant="text" width="300px" height="16px" />
          </div>
        </div>
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} variant="rectangular" height="120px" />)}
        </div>
      </div>
    )
  }

  return (
    <motion.div initial="hidden" animate="show" className="page space-y-6">
        <PageHero
          title="Plugins"
          subtitle="Extend functionality with plugins"
          icon={<Puzzle size={19} />}
          actions={
            <Button variant="secondary" icon={<RefreshCw className="w-4 h-4" />} onClick={loadPlugins}>
              Refresh
            </Button>
          }
        />

      <motion.div className="flex items-center gap-2 mb-4">
        {(['all', 'installed', 'available', 'enabled'] as const).map(f => (
          <button key={f} onClick={() => setFilter(f)} className={cn('px-3 py-1.5 rounded-lg text-sm font-medium transition-colors', filter === f ? 'bg-accent text-surface-0' : 'bg-surface-2 text-text-secondary hover:bg-surface-3 hover:text-text')}>
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </motion.div>

      <motion.div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {loading ? (
          Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} variant="rectangular" height="180px" />
          ))
        ) : filteredPlugins.length === 0 ? (
          <div className="col-span-full text-center py-12 text-text-tertiary text-sm">No plugins found</div>
        ) : (
          filteredPlugins.map((plugin, i) => (
            <motion.div key={plugin.id} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }} className="relative p-5 rounded-2xl bg-surface-1 border border-border hover:border-accent/50 transition-colors">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="p-3 rounded-xl bg-surface-2 text-accent shrink-0">{pluginIcon(plugin.category)}</div>
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
              <p className="text-xs text-text-secondary mt-3 leading-relaxed">{plugin.description}</p>
            </motion.div>
          ))
        )}
      </motion.div>

      <motion.div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <ActionCard icon={<Download className="w-5 h-5" />} title="Check for Updates" desc="Check all installed plugins for updates" tags={['Maintenance']} onClick={() => runAction('updates', () => api.pluginCheckUpdates(), 'Plugin update check complete')} />
        <ActionCard icon={<Code className="w-5 h-5" />} title="Create Plugin Template" desc="Scaffold a new plugin project from template" tags={['Dev']} onClick={() => runAction('template', () => api.pluginCreateTemplate('my-plugin'), 'Plugin template created')} />
        <ActionCard icon={<CheckCircle2 className="w-5 h-5" />} title="Validate Plugin" desc="Validate a plugin package for correctness" tags={['Quality']} onClick={() => runAction('validate', () => api.pluginValidate('/plugins/my-plugin'), 'Plugin validation complete')} />
      </motion.div>

      {result && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mt-4 p-4 rounded-xl border" style={{ borderColor: result.success ? 'var(--color-green)' : 'var(--color-red)', backgroundColor: result.success ? 'var(--color-green-dim)' : 'var(--color-red-dim)' }}>
          <div className="flex items-center gap-3">
            <div className={cn('w-2 h-2 rounded-full', result.success ? 'bg-green' : 'bg-red')} />
            <span className="text-sm text-text">{result.message}</span>
          </div>
        </motion.div>
      )}

      <motion.div className="mt-6 p-4 rounded-xl bg-surface-1 border border-border">
        <h3 className="text-sm font-semibold text-text mb-3 flex items-center gap-2"><Info className="w-4 h-4 text-cyan" />Plugin Development</h3>
        <p className="text-xs text-text-secondary mb-3">Build your own plugins with the Optinix Plugin SDK. TypeScript support, hot reload, and full API access.</p>
        <div className="flex gap-3">
          <Button variant="secondary" icon={<ExternalLink className="w-4 h-4" />} onClick={() => window.open('https://github.com/optinix/plugin-sdk', '_blank')}>View SDK Docs</Button>
          <Button variant="ghost" icon={<Plus className="w-4 h-4" />} onClick={() => runAction('create', () => api.pluginCreateTemplate('my-plugin'), 'Plugin scaffold created')}>Create New Plugin</Button>
        </div>
      </motion.div>
    </motion.div>
  )
}
