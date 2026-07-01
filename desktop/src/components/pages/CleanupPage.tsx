import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  Trash2, HardDrive, RefreshCw, FileText, Delete, Trash,
  Search, FolderOpen, Monitor, Globe, Bug, Archive, FolderKanban,
  Wifi, Layers, Bomb, CheckCircle2, Loader2,
} from 'lucide-react'
import { Card } from '../ui/Card'
import { MetricCard } from '../ui/MetricCard'
import { Button } from '../ui/Button'
import { Skeleton } from '../ui/Skeleton'
import { cn, formatBytes } from '../../lib/utils'
import type { SystemInfo } from '../../types'
import { api } from '../../lib/api'

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.05 } } }
const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }

const categoryIcons: Record<string, React.ReactNode> = {
  'Temp Files': <FileText className="w-4 h-4" />,
  'Windows Temp': <FolderOpen className="w-4 h-4" />,
  'Recycle Bin': <Trash className="w-4 h-4" />,
  'Browser Cache': <Globe className="w-4 h-4" />,
  'System Logs': <Monitor className="w-4 h-4" />,
  'Windows Update': <RefreshCw className="w-4 h-4" />,
  'Delivery Opt.': <Wifi className="w-4 h-4" />,
  'Crash Dumps': <Bug className="w-4 h-4" />,
  'Thumbnails': <Layers className="w-4 h-4" />,
  'Prefetch': <Archive className="w-4 h-4" />,
  'Old Windows': <FolderKanban className="w-4 h-4" />,
}

export function CleanupPage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const [loadingAction, setLoadingAction] = useState<string | null>(null)
  const [result, setResult] = useState<{ key: string; message: string; success: boolean } | null>(null)
  const [cleanedCategories, setCleanedCategories] = useState<Set<string>>(new Set())
  const [scanResults, setScanResults] = useState<{ name: string; description: string; items: number; bytes: number }[] | null>(null)
  const [scanLoading, setScanLoading] = useState(false)
  const [scanTotal, setScanTotal] = useState(0)

  const deepScan = useCallback(async () => {
    setScanLoading(true)
    try {
      const res = await api.diskScan('C:')
      setScanResults(res.categories)
      setScanTotal(res.total_bytes)
    } catch {
      setScanResults([])
    } finally {
      setScanLoading(false)
    }
  }, [])

  useEffect(() => { deepScan() }, [deepScan])

  const cleanCategory = async (name: string) => {
    setLoadingAction(name)
    setResult(null)
    try {
      await api.diskCleanCategory(name)
      setCleanedCategories(prev => new Set(prev).add(name))
      setResult({ key: name, message: `${name} cleaned successfully`, success: true })
      deepScan()
    } catch (e) {
      setResult({ key: name, message: e instanceof Error ? e.message : 'Clean failed', success: false })
    } finally {
      setLoadingAction(null)
    }
  }

  const cleanAll = async () => {
    setLoadingAction('all')
    setResult(null)
    try {
      await api.diskCleanAll()
      setResult({ key: 'all', message: 'All system cache cleaned', success: true })
      deepScan()
    } catch (e) {
      setResult({ key: 'all', message: e instanceof Error ? e.message : 'Clean all failed', success: false })
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

  const tempFiles = scanResults?.find(c => /temp/i.test(c.name))?.bytes ?? 0
  const recycleBin = scanResults?.find(c => /recycle/i.test(c.name))?.bytes ?? 0
  const browserCache = scanResults?.find(c => /browser/i.test(c.name))?.bytes ?? 0
  const windowsUpdate = scanResults?.find(c => /update/i.test(c.name))?.bytes ?? 0

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-6">
      <motion.div variants={item}>
        <div className="flex items-center gap-3 mb-1">
          <Trash2 className="w-6 h-6 text-accent" />
          <h1 className="text-2xl font-bold text-text">System Cleanup</h1>
        </div>
        <p className="text-sm text-text-secondary ml-9">Scan and remove system junk, cache, and temporary files</p>
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <MetricCard icon={<HardDrive className="w-5 h-5" />} label="Total Junk" value={formatBytes(scanTotal)} progress={scanTotal > 0 ? Math.min(100, Math.round((scanTotal / (10 * 1024 ** 3)) * 100)) : 0} sub="Scannable waste" />
        <MetricCard icon={<FileText className="w-5 h-5" />} label="Temp Files" value={formatBytes(tempFiles)} progress={tempFiles > 0 ? Math.min(100, Math.round((tempFiles / (2 * 1024 ** 3)) * 100)) : 0} sub="User & system temp" />
        <MetricCard icon={<Globe className="w-5 h-5" />} label="Browser Cache" value={formatBytes(browserCache)} progress={browserCache > 0 ? Math.min(100, Math.round((browserCache / (1024 ** 3)) * 100)) : 0} sub="Chrome, Edge, Firefox" />
        <MetricCard icon={<RefreshCw className="w-5 h-5" />} label="Windows Update" value={formatBytes(windowsUpdate)} progress={windowsUpdate > 0 ? Math.min(100, Math.round((windowsUpdate / (2 * 1024 ** 3)) * 100)) : 0} sub="Update cache" />
        <MetricCard icon={<Trash className="w-5 h-5" />} label="Recycle Bin" value={formatBytes(recycleBin)} progress={recycleBin > 0 ? Math.min(100, Math.round((recycleBin / (1024 ** 3)) * 100)) : 0} sub="Deleted files" />
        <MetricCard icon={<Layers className="w-5 h-5" />} label="Thumbnails" value={formatBytes(scanResults?.find(c => /thumb/i.test(c.name))?.bytes ?? 0)} progress={45} sub="Thumbnail cache" />
      </motion.div>

      <motion.div variants={item} className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Button
            variant="primary"
            size="md"
            icon={scanLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            onClick={deepScan}
            loading={scanLoading}
          >
            Rescan
          </Button>
          <Button
            variant="default"
            size="md"
            icon={<Bomb className="w-4 h-4" />}
            onClick={cleanAll}
            loading={loadingAction === 'all'}
          >
            Clean All
          </Button>
        </div>
        {scanResults && (
          <p className="text-xs text-text-secondary">
            {scanResults.filter(c => c.bytes > 0).length} categories with waste
            {cleanedCategories.size > 0 && ` · ${cleanedCategories.size} cleaned`}
          </p>
        )}
      </motion.div>

      {scanLoading && !scanResults && (
        <motion.div variants={item} className="space-y-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} variant="rectangular" height="56px" />
          ))}
        </motion.div>
      )}

      {scanResults && scanResults.length > 0 && (
        <motion.div variants={item} className="space-y-1.5">
          {scanResults
            .sort((a, b) => b.bytes - a.bytes)
            .map(cat => {
              const isCleaned = cleanedCategories.has(cat.name)
              const pct = scanTotal > 0 ? Math.round((cat.bytes / scanTotal) * 100) : 0
              return (
                <div key={cat.name} className={cn(
                  'flex items-center gap-3 px-4 py-3 rounded-xl border transition-all',
                  isCleaned ? 'border-green/30 bg-green-dim/10' :
                    cat.bytes > 0 ? 'border-border bg-surface-1 hover:bg-surface-2' :
                      'border-border/50 bg-surface-1/50 opacity-50'
                )}>
                  <div className={cn(
                    'p-1.5 rounded-lg shrink-0',
                    isCleaned ? 'text-green bg-green-dim/20' : 'text-text-secondary bg-surface-3'
                  )}>
                    {categoryIcons[cat.name] || <FolderKanban className="w-4 h-4" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-medium text-text truncate">{cat.name}</span>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className="text-xs font-mono text-text-secondary">
                          {formatBytes(cat.bytes)}
                        </span>
                        {cat.items > 0 && (
                          <span className="text-[10px] text-text-tertiary">({cat.items} items)</span>
                        )}
                        {isCleaned && <CheckCircle2 className="w-3.5 h-3.5 text-green" />}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 mt-1">
                      <div className="flex-1 h-1 rounded-full bg-surface-3 overflow-hidden">
                        <div
                          className={cn('h-full rounded-full transition-all duration-500', isCleaned ? 'bg-green' : 'bg-accent')}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="text-[10px] text-text-tertiary w-8 text-right">{pct}%</span>
                    </div>
                    <p className="text-[10px] text-text-tertiary mt-0.5 truncate">{cat.description}</p>
                  </div>
                  {cat.bytes > 0 && (
                    <Button
                      variant="ghost"
                      size="sm"
                      icon={<Delete className="w-3.5 h-3.5" />}
                      onClick={() => cleanCategory(cat.name)}
                      loading={loadingAction === cat.name}
                    >
                      Clean
                    </Button>
                  )}
                </div>
              )
            })}
        </motion.div>
      )}

      {!scanLoading && scanResults && scanResults.length === 0 && (
        <motion.div variants={item}>
          <Card padding="lg">
            <div className="flex flex-col items-center gap-2 py-6">
              <Search className="w-8 h-8 text-text-tertiary" />
              <p className="text-sm text-text-secondary">No cache data found. Run a scan to analyze your system.</p>
            </div>
          </Card>
        </motion.div>
      )}

      {result && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
          className={cn('p-4 rounded-xl border', result.success ? 'bg-green-dim border-green/30' : 'bg-red-dim border-red/30')}>
          <div className="flex items-center gap-3">
            <div className={cn('w-2 h-2 rounded-full', result.success ? 'bg-green' : 'bg-red')} />
            <p className={cn('text-sm font-medium', result.success ? 'text-green' : 'text-red')}>{result.message}</p>
          </div>
        </motion.div>
      )}
    </motion.div>
  )
}
