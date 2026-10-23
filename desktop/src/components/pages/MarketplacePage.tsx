import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  Store, Package, Download, Check, X, Search, Grid3X3,
  Video, Code2, Box, Palette, Gamepad2, Gamepad,
  Pickaxe, Container, RefreshCw,
} from 'lucide-react'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { Skeleton } from '../ui/Skeleton'
import { PageHero } from '../ui/PageHero'
import { cn } from '../../lib/utils'
import { api } from '../../lib/api'
import type { SystemInfo, MarketplaceModule } from '../../types'

const iconMap: Record<string, React.ReactNode> = {
  'video': <Video size={24} />,
  'code-2': <Code2 size={24} />,
  'cube': <Box size={24} />,
  'palette': <Palette size={24} />,
  'gamepad-2': <Gamepad2 size={24} />,
  'box': <Package size={24} />,
  'gamepad': <Gamepad size={24} />,
  'pickaxe': <Pickaxe size={24} />,
  'container': <Container size={24} />,
}

const CATEGORIES = ['All', 'Content Creation', 'Development', 'Gaming'] as const
type Category = (typeof CATEGORIES)[number]

export function MarketplacePage(_props: { systemInfo: SystemInfo | null }) {
  const [modules, setModules] = useState<MarketplaceModule[]>([])
  const [, setCategories] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingAction, setLoadingAction] = useState<string | null>(null)
  const [result, setResult] = useState<{ message: string; success: boolean } | null>(null)
  const [category, setCategory] = useState<Category>('All')
  const [search, setSearch] = useState('')

  const loadModules = useCallback(async (cat: Category) => {
    setLoading(true)
    try {
      const apiCat = cat === 'All' ? undefined : cat
      const res = await api.marketplaceModules(apiCat)
      setModules(res.modules)
    } catch {
      setModules([])
    } finally {
      setLoading(false)
    }
  }, [])

  const loadCategories = useCallback(async () => {
    try {
      const res = await api.marketplaceCategories()
      setCategories(res.categories)
    } catch {
      // use defaults
    }
  }, [])

  useEffect(() => { loadModules(category) }, [category, loadModules])
  useEffect(() => { loadCategories() }, [loadCategories])

  const installedCount = modules.filter(m => m.installed).length

  const handleInstall = useCallback(async (id: string) => {
    setLoadingAction(id)
    setResult(null)
    setModules(prev => prev.map(m => m.id === id ? { ...m, installed: true } : m))
    try {
      await api.marketplaceInstall(id)
      setResult({ message: 'Module installed successfully', success: true })
    } catch (e) {
      setModules(prev => prev.map(m => m.id === id ? { ...m, installed: false } : m))
      setResult({ message: e instanceof Error ? e.message : 'Install failed', success: false })
    } finally {
      setLoadingAction(null)
    }
  }, [])

  const handleUninstall = useCallback(async (id: string) => {
    if (!window.confirm('Are you sure you want to uninstall this module?')) return
    setLoadingAction(id)
    setResult(null)
    setModules(prev => prev.map(m => m.id === id ? { ...m, installed: false } : m))
    try {
      await api.marketplaceUninstall(id)
      setResult({ message: 'Module uninstalled', success: true })
    } catch (e) {
      setModules(prev => prev.map(m => m.id === id ? { ...m, installed: true } : m))
      setResult({ message: e instanceof Error ? e.message : 'Uninstall failed', success: false })
    } finally {
      setLoadingAction(null)
    }
  }, [])

  const filteredModules = modules.filter(m =>
    !search || m.name.toLowerCase().includes(search.toLowerCase()) || m.description.toLowerCase().includes(search.toLowerCase())
  )

  if (!_props.systemInfo) {
    return (
      <div className="page space-y-6">
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <Skeleton variant="text" width="200px" height="28px" />
            <Skeleton variant="text" width="300px" height="16px" />
          </div>
        </div>
        <div className="space-y-4">
          {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} variant="rectangular" height="200px" />)}
        </div>
      </div>
    )
  }

  return (
    <motion.div initial="hidden" animate="show" className="page space-y-6">
            <PageHero
        title="Marketplace"
        subtitle="Discover and install toolkits"
        icon={<Store size={19} />}
        actions={
          <>
    <div className="flex items-center gap-3">
              <motion.div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-cyan-dim text-cyan text-xs font-medium">
                <Package className="w-3.5 h-3.5" />
                <span>{installedCount} installed</span>
              </motion.div>
              <Button variant="secondary" size="sm" icon={<RefreshCw className="w-4 h-4" />} onClick={() => loadModules(category)}>
                Refresh
              </Button>
            </div>
          </>
        }
      />

      <motion.div className="flex flex-col md:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-tertiary" />
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search modules..."
            className="w-full pl-10 pr-4 py-2 rounded-lg bg-surface-2 border border-border text-text placeholder-text-tertiary focus:border-accent focus:outline-none transition-colors"
          />
        </div>
        <div className="flex gap-2 flex-wrap">
          {CATEGORIES.map(c => (
            <button
              key={c}
              onClick={() => setCategory(c)}
              className={cn(
                'px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                category === c
                  ? 'bg-accent text-surface-0'
                  : 'bg-surface-2 text-text-secondary hover:bg-surface-3 hover:text-text'
              )}
            >
              {c}
            </button>
          ))}
        </div>
      </motion.div>

      <motion.div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {loading ? (
          Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} variant="rectangular" height="220px" />
          ))
        ) : filteredModules.length === 0 ? (
          <div className="col-span-full flex flex-col items-center justify-center py-16 text-text-tertiary">
            <Grid3X3 className="w-12 h-12 mb-3 opacity-40" />
            <p className="text-sm">No modules found</p>
          </div>
        ) : (
          filteredModules.map((mod, i) => (
            <motion.div
              key={mod.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04 }}
              whileHover={{ scale: 1.02, boxShadow: '0 8px 30px rgba(0,0,0,0.35)' }}
              className="relative p-5 rounded-2xl bg-surface-1 border border-border hover:border-accent/50 transition-colors"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="p-3 rounded-xl bg-surface-2 text-accent shrink-0">
                    {iconMap[mod.icon] ?? <Package size={24} />}
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-sm font-semibold text-text truncate">{mod.name}</h3>
                    <Badge variant="info" className="text-[10px] mt-1">
                      {mod.category}
                    </Badge>
                  </div>
                </div>
                {mod.installed ? (
                  <Button
                    variant="ghost"
                    size="sm"
                    icon={<X className="w-3.5 h-3.5" />}
                    loading={loadingAction === mod.id}
                    onClick={() => handleUninstall(mod.id)}
                    className="text-red hover:text-red/80 shrink-0"
                  >
                    Uninstall
                  </Button>
                ) : (
                  <Button
                    variant="secondary"
                    size="sm"
                    icon={<Download className="w-3.5 h-3.5" />}
                    loading={loadingAction === mod.id}
                    onClick={() => handleInstall(mod.id)}
                    className="shrink-0"
                  >
                    Install
                  </Button>
                )}
              </div>

              {mod.installed && (
                <div className="absolute top-3 right-3">
                  <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-dim text-green text-[10px] font-medium">
                    <Check className="w-3 h-3" />
                    Installed
                  </div>
                </div>
              )}

              <p className="text-xs text-text-secondary line-clamp-2 leading-relaxed mb-3">
                {mod.description}
              </p>

              <div className="flex items-center gap-2 text-xs text-text-tertiary mb-2">
                <span>v{mod.version}</span>
                {mod.downloads != null && (
                  <>
                    <span className="text-surface-4">|</span>
                    <span>{mod.downloads.toLocaleString()} downloads</span>
                  </>
                )}
              </div>

              {mod.tags && mod.tags.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {mod.tags.map(tag => (
                    <span
                      key={tag}
                      className="px-2 py-0.5 rounded text-[10px] font-medium bg-surface-3 text-text-tertiary"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </motion.div>
          ))
        )}
      </motion.div>

      {result && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 rounded-xl border"
          style={{
            borderColor: result.success ? 'var(--color-green)' : 'var(--color-red)',
            backgroundColor: result.success ? 'var(--color-green-dim)' : 'var(--color-red-dim)',
          }}
        >
          <div className="flex items-center gap-3">
            <div className={cn('w-2 h-2 rounded-full', result.success ? 'bg-green' : 'bg-red')} />
            <span className="text-sm text-text">{result.message}</span>
          </div>
        </motion.div>
      )}
    </motion.div>
  )
}
