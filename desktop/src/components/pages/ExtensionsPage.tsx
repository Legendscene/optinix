import { useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  Globe,
  Shield,
  Key,
  Download,
  Trash2,
  CheckCircle2,
  RefreshCw,
  ExternalLink,
  Plus,
  X,
  Menu,
  Search,
  Settings,
  Wifi,
  Cloud,
  Lock,
} from 'lucide-react'
import { Button } from '../ui/Button'
import { ActionCard } from '../ui/ActionCard'
import { Skeleton } from '../ui/Skeleton'
import { cn } from '../../lib/utils'
import type { SystemInfo } from '../../types'

interface Extension {
  id: string
  name: string
  browser: 'chrome' | 'firefox' | 'edge' | 'shell'
  desc: string
  version: string
  author: string
  status: 'installed' | 'available'
  enabled: boolean
  icon: React.ReactNode
}

type Filter = 'all' | 'enabled' | 'installed' | 'available'

const mockExtensions: Extension[] = [
  { id: 'ublock', name: 'uBlock Origin', browser: 'chrome', desc: 'Efficient ad and tracker blocker', version: '1.54.0', author: 'Raymond Hill', status: 'installed', enabled: true, icon: <Shield className="w-5 h-5" /> },
  { id: 'bitwarden', name: 'Bitwarden', browser: 'chrome', desc: 'Open source password manager', version: '2024.12.0', author: '8bit Solutions', status: 'installed', enabled: true, icon: <Key className="w-5 h-5" /> },
  { id: 'privacy_badger', name: 'Privacy Badger', browser: 'firefox', desc: 'Learn to block invisible trackers', version: '2024.11.15', author: 'EFF', status: 'installed', enabled: true, icon: <Lock className="w-5 h-5" /> },
  { id: 'dark_reader', name: 'Dark Reader', browser: 'edge', desc: 'Dark mode for every website', version: '4.9.90', author: 'Alexander Shutau', status: 'available', enabled: false, icon: <Cloud className="w-5 h-5" /> },
  { id: 'download_mgr', name: 'Free Download Manager', browser: 'chrome', desc: 'Powerful download accelerator', version: '6.20.0', author: 'FDM Team', status: 'available', enabled: false, icon: <Download className="w-5 h-5" /> },
  { id: 'tab_suspender', name: 'Tab Suspender', browser: 'firefox', desc: 'Auto-suspend unused tabs to save memory', version: '1.2.3', author: 'Tab Labs', status: 'available', enabled: false, icon: <Menu className="w-5 h-5" /> },
  { id: 'clipboard', name: 'Clipboard History', browser: 'shell', desc: 'System-wide clipboard history manager', version: '1.0.0', author: 'Optinix', status: 'installed', enabled: true, icon: <Wifi className="w-5 h-5" /> },
  { id: 'context_menu', name: 'Classic Context Menu', browser: 'shell', desc: 'Restore classic right-click menu', version: '1.0.0', author: 'Optinix', status: 'available', enabled: false, icon: <Globe className="w-5 h-5" /> },
]

const browserColor = (b: string) => b === 'chrome' ? 'bg-blue-dim text-blue' : b === 'firefox' ? 'bg-orange-dim text-orange' : b === 'edge' ? 'bg-green-dim text-green' : 'bg-purple-dim text-purple'

export default function ExtensionsPage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const [extensions, setExtensions] = useState<Extension[]>(mockExtensions)
  const [loadingAction, setLoadingAction] = useState<string | null>(null)
  const [result, setResult] = useState<{ key: string; message: string; success: boolean } | null>(null)
  const [filter, setFilter] = useState<Filter>('all')
  const [search, setSearch] = useState('')

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

  const toggleExtension = useCallback(async (id: string) => {
    setLoadingAction(id)
    setExtensions(prev => prev.map(e => e.id === id ? { ...e, enabled: !e.enabled } : e))
    setResult(null)
    try {
      await new Promise(r => setTimeout(r, 500))
      setResult({ key: id, message: `Extension ${id} ${extensions.find(e => e.id === id)?.enabled ? 'disabled' : 'enabled'}`, success: true })
    } catch (e) {
      setResult({ key: id, message: e instanceof Error ? e.message : 'Failed', success: false })
    } finally {
      setLoadingAction(null)
    }
  }, [extensions])

  const installExtension = useCallback(async (id: string) => {
    setLoadingAction(id)
    setResult(null)
    try {
      await new Promise(r => setTimeout(r, 1200))
      setExtensions(prev => prev.map(e => e.id === id ? { ...e, status: 'installed', enabled: true } : e))
      setResult({ key: id, message: 'Extension installed', success: true })
    } catch (e) {
      setResult({ key: id, message: e instanceof Error ? e.message : 'Failed', success: false })
    } finally {
      setLoadingAction(null)
    }
  }, [])

  const uninstallExtension = useCallback(async (id: string) => {
    setLoadingAction(id)
    setResult(null)
    try {
      await new Promise(r => setTimeout(r, 500))
      setExtensions(prev => prev.map(e => e.id === id ? { ...e, status: 'available', enabled: false } : e))
      setResult({ key: id, message: 'Extension uninstalled', success: true })
    } catch (e) {
      setResult({ key: id, message: e instanceof Error ? e.message : 'Failed', success: false })
    } finally {
      setLoadingAction(null)
    }
  }, [])

  const filteredExtensions = extensions.filter(e => {
    if (filter !== 'all' && e.status !== filter && e.enabled !== (filter === 'enabled')) return false
    if (search && !e.name.toLowerCase().includes(search.toLowerCase()) && !e.desc.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  const installedCount = extensions.filter(e => e.status === 'installed').length
  const enabledCount = extensions.filter(e => e.enabled).length

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
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} variant="rectangular" height="120px" />)}
        </div>
      </div>
    )
  }

  return (
    <motion.div initial="hidden" animate="show" className="p-6 space-y-6">
      <motion.div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="p-2 rounded-xl bg-surface-2 text-accent"><Globe className="w-6 h-6" /></div>
            <h1 className="text-2xl font-bold text-text">Extensions</h1>
          </div>
          <p className="text-sm text-text-secondary ml-11">Browser and shell extensions</p>
        </div>
        <motion.div className="flex items-center gap-2">
          <span className="px-3 py-1 rounded-full bg-blue-dim text-blue text-xs font-medium">{installedCount} installed</span>
          <span className="px-3 py-1 rounded-full bg-green-dim text-green text-xs font-medium">{enabledCount} enabled</span>
        </motion.div>
      </motion.div>

      <motion.div className="flex flex-col md:flex-row gap-4 mb-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-tertiary" />
          <input type="text" value={search} onChange={e => setSearch(e.target.value)} placeholder="Search extensions..." className="w-full pl-10 pr-4 py-2 rounded-lg bg-surface-2 border border-border text-text placeholder-text-tertiary focus:border-accent focus:outline-none transition-colors" />
        </div>
        <div className="flex gap-2">
          {['all', 'installed', 'available', 'enabled'].map(f => (
            <button key={f} onClick={() => setFilter(f as Filter)} className={cn('px-3 py-2 rounded-lg text-sm font-medium transition-colors', filter === f ? 'bg-accent text-white' : 'bg-surface-2 text-text-secondary hover:bg-surface-3 hover:text-text')}>
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </motion.div>

      <motion.div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredExtensions.map((ext, i) => (
          <motion.div key={ext.id} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.03 }} className="relative p-5 rounded-2xl bg-surface-1 border border-border hover:border-accent/50 transition-colors">
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className="p-3 rounded-xl bg-surface-2 text-accent shrink-0">{ext.icon}</div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold text-text">{ext.name}</h3>
                    <span className={cn('px-2 py-0.5 rounded text-[10px] font-medium', browserColor(ext.browser))}>
                      {ext.browser.charAt(0).toUpperCase() + ext.browser.slice(1)}
                    </span>
                  </div>
                  <p className="text-xs text-text-secondary">{ext.author} • v{ext.version}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={() => runAction('settings', async () => {}, `Open ${ext.name} settings`)} className="p-1.5 rounded-lg bg-surface-2 text-text-secondary hover:bg-surface-3 hover:text-text transition-colors" title="Settings"><Settings className="w-4 h-4" /></button>
                {ext.status === 'available' ? (
                  <Button variant="secondary" size="sm" icon={<Plus className="w-3.5 h-3.5" />} loading={loadingAction === ext.id} onClick={() => installExtension(ext.id)}>Install</Button>
                ) : ext.enabled ? (
                  <Button variant="secondary" size="sm" icon={<X className="w-3.5 h-3.5" />} loading={loadingAction === ext.id} onClick={() => toggleExtension(ext.id)}>Disable</Button>
                ) : (
                  <>
                    <Button variant="secondary" size="sm" icon={<CheckCircle2 className="w-3.5 h-3.5" />} loading={loadingAction === ext.id} onClick={() => toggleExtension(ext.id)}>Enable</Button>
                    <Button variant="ghost" size="sm" icon={<Trash2 className="w-3.5 h-3.5" />} loading={loadingAction === ext.id} onClick={() => uninstallExtension(ext.id)} className="text-red hover:text-red/80">Uninstall</Button>
                  </>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2 text-xs text-text-secondary">
              <span className="px-2 py-0.5 rounded bg-surface-3 text-text-tertiary">{ext.version}</span>
            </div>
            <p className="text-xs text-text-secondary mt-3 leading-relaxed">{ext.desc}</p>
          </motion.div>
        ))}
      </motion.div>

      <motion.div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <ActionCard icon={<Plus className="w-5 h-5" />} title="Install from File" desc="Install extension from .crx, .xpi, or .zip" tags={['Local']} variant="default" onClick={() => runAction('local', async () => {}, 'Open file picker')} />
        <ActionCard icon={<RefreshCw className="w-5 h-5" />} title="Check for Updates" desc="Check all extensions for updates" tags={['Maintenance']} variant="default" onClick={() => runAction('updates', async () => {}, 'All extensions up to date')} />
        <ActionCard icon={<ExternalLink className="w-5 h-5" />} title="Sync Across Browsers" desc="Sync installed extensions across Chrome, Edge, Firefox" tags={['Sync']} variant="success" onClick={() => runAction('sync', async () => {}, 'Sync initiated')} />
      </motion.div>

      <motion.div className="mt-6 p-4 rounded-xl bg-surface-1 border border-border">
        <h3 className="text-sm font-semibold text-text mb-3 flex items-center gap-2"><Cloud className="w-4 h-4 text-blue" />Recommended Bundles</h3>
        <div className="flex flex-wrap gap-2">
          {[
            { name: 'Privacy Pack', desc: 'uBlock + Privacy Badger + HTTPS Everywhere', count: 3 },
            { name: 'Developer Tools', desc: 'React DevTools + Redux DevTools + JSON Viewer', count: 3 },
            { name: 'Productivity', desc: 'Tab Suspender + Clipboard History + Dark Reader', count: 3 },
          ].map((bundle, i) => (
            <motion.button key={i} onClick={() => runAction('bundle', async () => {}, `${bundle.name} installed`)} className="p-3 rounded-xl bg-surface-2 border border-border hover:border-accent/50 hover:bg-surface-3 transition-colors text-left">
              <p className="font-medium text-text">{bundle.name}</p>
              <p className="text-xs text-text-secondary mt-0.5">{bundle.desc}</p>
              <p className="text-[10px] text-text-tertiary mt-1">{bundle.count} extensions</p>
            </motion.button>
          ))}
        </div>
      </motion.div>

      {result && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mt-4 p-4 rounded-xl border" style={{ borderColor: result.success ? '#22c55e' : '#ef4444', backgroundColor: result.success ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)' }}>
          <div className="flex items-center gap-3">
            <div className={cn('w-2 h-2 rounded-full', result.success ? 'bg-green' : 'bg-red')} />
            <span className="text-sm text-text">{result.message}</span>
          </div>
        </motion.div>
      )}
    </motion.div>
  )
}