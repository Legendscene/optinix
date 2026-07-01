import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  Shield,
  Download,
  HardDrive,
  RefreshCw,
  Search,
  AlertTriangle,
  CheckCircle,
  FileDown,
  Package,
} from 'lucide-react'
import { Card } from '../ui/Card'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { Skeleton } from '../ui/Skeleton'
import { MetricCard } from '../ui/MetricCard'
import { cn } from '../../lib/utils'
import { api } from '../../lib/api'

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.05 } },
}

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
}

interface DriverEntry {
  name: string
  version: string
  latest_version: string
  update_available: boolean
  category: string
  manufacturer: string
  download_url?: string
}

export function DriverBoosterPage() {
  const [scanLoading, setScanLoading] = useState(true)
  const [drivers, setDrivers] = useState<DriverEntry[]>([])
  const [total, setTotal] = useState(0)
  const [outdated, setOutdated] = useState(0)
  const [upToDate, setUpToDate] = useState(0)
  const [filter, setFilter] = useState('')
  const [loadingAction, setLoadingAction] = useState<string | null>(null)
  const [result, setResult] = useState<{ key: string; message: string; success: boolean } | null>(null)

  const scan = useCallback(async () => {
    setScanLoading(true)
    setResult(null)
    try {
      const res = await api.driverCheckUpdates()
      setDrivers(res.drivers)
      setTotal(res.total)
      setOutdated(res.outdated)
      setUpToDate(res.up_to_date)
    } catch {
      setDrivers([])
      setTotal(0)
      setOutdated(0)
      setUpToDate(0)
    } finally {
      setScanLoading(false)
    }
  }, [])

  useEffect(() => { scan() }, [scan])

  const runAction = async (key: string, fn: () => Promise<unknown>, successMsg: string) => {
    setLoadingAction(key)
    setResult(null)
    try {
      await fn()
      setResult({ key, message: successMsg, success: true })
      if (key === 'scan') await scan()
    } catch (e) {
      setResult({ key, message: e instanceof Error ? e.message : 'Operation failed', success: false })
    } finally {
      setLoadingAction(null)
    }
  }

  const filtered = drivers.filter(d =>
    d.name.toLowerCase().includes(filter.toLowerCase()) ||
    d.category.toLowerCase().includes(filter.toLowerCase())
  )

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-6">
      <motion.div variants={item}>
        <div className="flex items-center gap-3 mb-1">
          <Shield className="w-6 h-6 text-accent" />
          <h1 className="text-2xl font-bold tracking-tight text-text">Driver Booster</h1>
        </div>
        <p className="text-sm text-text-secondary ml-9">Scan, download, and install driver updates</p>
      </motion.div>

      <motion.div variants={item} className="flex flex-wrap gap-2">
        <Button
          variant="primary"
          size="md"
          icon={<Search className="w-4 h-4" />}
          loading={scanLoading}
          onClick={scan}
        >
          Scan for Driver Updates
        </Button>
        <Button
          variant="secondary"
          size="md"
          icon={<FileDown className="w-4 h-4" />}
          loading={loadingAction === 'download-all'}
          disabled={outdated === 0}
          onClick={() => runAction('download-all', () => api.driverDownloadAll(), 'All drivers downloaded')}
        >
          Download All
        </Button>
        <Button
          variant="secondary"
          size="md"
          icon={<Package className="w-4 h-4" />}
          loading={loadingAction === 'install-all'}
          disabled={outdated === 0}
          onClick={() => runAction('install-all', () => api.driverInstallAll(), 'All drivers installed')}
        >
          Install All
        </Button>
      </motion.div>

      {!scanLoading && drivers.length > 0 && (
        <motion.div variants={item} className="grid grid-cols-3 gap-4">
          <MetricCard icon={<HardDrive className="w-5 h-5" />} label="Total Drivers" value={String(total)} />
          <MetricCard icon={<AlertTriangle className="w-5 h-5" />} label="Outdated" value={String(outdated)} trend={outdated > 0 ? { value: String(outdated), up: false } : undefined} />
          <MetricCard icon={<CheckCircle className="w-5 h-5" />} label="Up to Date" value={String(upToDate)} />
        </motion.div>
      )}

      <motion.div variants={item}>
        <Card padding="lg">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <RefreshCw className="w-5 h-5 text-accent" />
              <h2 className="text-sm font-semibold text-text">Driver Updates</h2>
              {!scanLoading && <Badge>{drivers.length} drivers</Badge>}
            </div>
            <input
              type="text"
              placeholder="Filter drivers..."
              value={filter}
              onChange={e => setFilter(e.target.value)}
              className="px-3 py-1.5 rounded-lg bg-surface-2 border border-border text-sm text-text placeholder:text-text-tertiary focus:outline-none focus:border-accent w-48"
            />
          </div>
          {scanLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-14 rounded-xl" />)}
            </div>
          ) : drivers.length === 0 ? (
            <p className="text-xs text-text-tertiary py-6 text-center">No drivers found. Run a scan.</p>
          ) : (
            <div className="divide-y divide-border max-h-[500px] overflow-y-auto">
              {filtered.map((d, i) => (
                <div key={`${d.name}-${i}`} className="flex items-center justify-between py-3 first:pt-0 last:pb-0 gap-4">
                  <div className="flex items-center gap-3 min-w-0 flex-1">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-text truncate">{d.name}</p>
                      <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                        <span className="text-[11px] text-text-tertiary">{d.category}</span>
                        <span className="text-[10px] text-text-tertiary">•</span>
                        <span className="text-[11px] text-text-tertiary">{d.version}</span>
                      </div>
                    </div>
                    <span className="text-xs text-text-secondary shrink-0 font-mono">{d.latest_version}</span>
                  </div>
                  <Badge variant={d.update_available ? 'warning' : 'success'}>
                    {d.update_available ? 'Update Available' : 'Up to Date'}
                  </Badge>
                  {d.update_available && (
                    <div className="flex gap-1 shrink-0">
                      <Button
                        size="sm"
                        variant="secondary"
                        icon={<Download className="w-3 h-3" />}
                        loading={loadingAction === `download-${d.name}`}
                        onClick={() => runAction(`download-${d.name}`, () => api.driverDownload(d.name), `${d.name} downloaded`)}
                      >
                        Download
                      </Button>
                      <Button
                        size="sm"
                        variant="primary"
                        icon={<Package className="w-3 h-3" />}
                        loading={loadingAction === `install-${d.name}`}
                        onClick={() => runAction(`install-${d.name}`, () => api.driverInstall(d.name), `${d.name} installed`)}
                      >
                        Install
                      </Button>
                    </div>
                  )}
                </div>
              ))}
              {filter && filtered.length === 0 && (
                <p className="text-xs text-text-tertiary py-4 text-center">No drivers match your filter.</p>
              )}
            </div>
          )}
        </Card>
      </motion.div>

      {result && (
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
