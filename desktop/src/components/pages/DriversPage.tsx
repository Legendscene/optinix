import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  Cpu,
  Monitor,
  Wifi,
  SlidersHorizontal,
  Download,
  Search,
  AlertTriangle,
  Globe,
  RefreshCw,
} from 'lucide-react'
import { Card } from '../ui/Card'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { Skeleton } from '../ui/Skeleton'
import { cn } from '../../lib/utils'
import { api } from '../../lib/api'
import type { SystemInfo, DriverInfo } from '../../types'

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.05 } },
}

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
}

const QUICK_DOWNLOADS = [
  { name: 'NVIDIA', icon: <Cpu size={18} />, url: 'https://www.nvidia.com/download/index.aspx' },
  { name: 'AMD', icon: <Cpu size={18} />, url: 'https://www.amd.com/en/support' },
  { name: 'Intel', icon: <Cpu size={18} />, url: 'https://www.intel.com/content/www/us/en/download-center/home.html' },
  { name: 'Realtek', icon: <Wifi size={18} />, url: 'https://www.realtek.com/en/downloads' },
  { name: 'Qualcomm', icon: <Cpu size={18} />, url: 'https://www.qualcomm.com/products/technology/wireless-networks/downloads' },
  { name: 'Intel WiFi', icon: <Wifi size={18} />, url: 'https://www.intel.com/content/www/us/en/support/articles/000005511/wireless.html' },
]

function driverIcon(name: string) {
  const l = name.toLowerCase()
  if (l.includes('nvidia') || l.includes('gpu') || l.includes('graphics')) return <Monitor size={16} />
  if (l.includes('realtek') || l.includes('audio') || l.includes('sound')) return <Wifi size={16} />
  if (l.includes('intel') || l.includes('chipset')) return <Cpu size={16} />
  if (l.includes('qualcomm') || l.includes('broadcom') || l.includes('wifi')) return <Globe size={16} />
  return <SlidersHorizontal size={16} />
}

export function DriversPage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const [drivers, setDrivers] = useState<DriverInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingAction, setLoadingAction] = useState<string | null>(null)
  const [missing, setMissing] = useState<string[] | null>(null)
  const [result, setResult] = useState<{ key: string; message: string; success: boolean } | null>(null)

  const loadDrivers = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.drivers()
      setDrivers(res.drivers)
    } catch {
      setDrivers([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadDrivers() }, [loadDrivers])

  const runAction = async (key: string, fn: () => Promise<unknown>, successMsg: string) => {
    setLoadingAction(key)
    setResult(null)
    setMissing(null)
    try {
      if (key === 'missing') {
        const res = await fn() as { missing: string[] }
        setMissing(res.missing)
      } else {
        const res = await fn() as { drivers: DriverInfo[] }
        if (res.drivers) setDrivers(res.drivers)
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
        <div><Skeleton className="h-8 w-52 mb-1" /><Skeleton className="h-4 w-64" /></div>
        <div className="flex gap-2"><Skeleton className="h-9 w-32 rounded-lg" /><Skeleton className="h-9 w-36 rounded-lg" /></div>
        <Skeleton className="h-64 rounded-xl" />
        <div className="grid grid-cols-3 gap-3">
          {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-20 rounded-xl" />)}
        </div>
      </div>
    )
  }

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-6">
      <motion.div variants={item}>
        <div className="flex items-center gap-3 mb-1">
          <Monitor className="w-6 h-6 text-accent" />
          <h1 className="text-2xl font-bold tracking-tight text-text">Driver Manager</h1>
        </div>
        <p className="text-sm text-text-secondary ml-9">Scan and manage drivers</p>
      </motion.div>

      <motion.div variants={item} className="flex flex-wrap gap-2">
        <Button
          variant="primary"
          size="md"
          icon={<Search className="w-4 h-4" />}
          loading={loadingAction === 'scan'}
          onClick={() => runAction('scan', () => api.drivers(), 'Driver scan completed')}
        >
          Scan Drivers
        </Button>
        <Button
          variant="secondary"
          size="md"
          icon={<AlertTriangle className="w-4 h-4" />}
          loading={loadingAction === 'missing'}
          onClick={() => runAction('missing', () => api.missingDrivers(), 'Missing drivers check completed')}
        >
          Missing Drivers
        </Button>
      </motion.div>

      {missing && missing.length > 0 && (
        <motion.div variants={item}>
          <Card padding="lg" className="border-yellow/30">
            <div className="flex items-center gap-2 mb-3">
              <AlertTriangle className="w-5 h-5 text-yellow" />
              <h2 className="text-sm font-semibold text-text">Missing Drivers</h2>
              <Badge variant="warning">{missing.length} found</Badge>
            </div>
            <div className="flex flex-wrap gap-2">
              {missing.map(m => (
                <Badge key={m} variant="warning">{m}</Badge>
              ))}
            </div>
          </Card>
        </motion.div>
      )}

      {missing && missing.length === 0 && (
        <motion.div variants={item}>
          <Card padding="lg" className="border-green/30">
            <div className="flex items-center gap-2">
              <RefreshCw className="w-5 h-5 text-green" />
              <p className="text-sm font-medium text-green">All drivers are up to date</p>
            </div>
          </Card>
        </motion.div>
      )}

      <motion.div variants={item}>
        <Card padding="lg">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <SlidersHorizontal className="w-5 h-5 text-accent" />
              <h2 className="text-sm font-semibold text-text">Installed Drivers</h2>
            </div>
            <Badge>{drivers.length} drivers</Badge>
          </div>
          {loading ? (
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-14 rounded-xl" />)}
            </div>
          ) : drivers.length === 0 ? (
            <p className="text-xs text-text-tertiary py-6 text-center">No drivers detected. Run a scan.</p>
          ) : (
            <div className="divide-y divide-border max-h-[420px] overflow-y-auto">
              {drivers.map((d, i) => (
                <div key={`${d.name}-${i}`} className="flex items-center justify-between py-3 first:pt-0 last:pb-0">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="p-2 rounded-lg bg-surface-2 text-text-secondary shrink-0">
                      {driverIcon(d.name)}
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-text truncate">{d.name}</p>
                      <div className="flex items-center gap-2 mt-0.5">
                        {d.manufacturer && <span className="text-[11px] text-text-tertiary">{d.manufacturer}</span>}
                        {d.version && (
                          <>
                            <span className="text-[10px] text-text-tertiary">•</span>
                            <span className="text-[11px] text-text-tertiary">v{d.version}</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                  {d.download_url && (
                    <a
                      href={d.download_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-2 rounded-lg text-text-secondary hover:text-accent hover:bg-accent-dim transition-colors"
                    >
                      <Download size={16} />
                    </a>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>
      </motion.div>

      <motion.div variants={item}>
        <Card padding="lg">
          <div className="flex items-center gap-2 mb-4">
            <Download className="w-5 h-5 text-accent" />
            <h2 className="text-sm font-semibold text-text">Quick Downloads</h2>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2">
            {QUICK_DOWNLOADS.map(qd => (
              <a
                key={qd.name}
                href={qd.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex flex-col items-center gap-2 p-4 rounded-xl border border-border bg-surface-2 hover:border-accent/50 hover:bg-surface-3 transition-colors text-center"
              >
                <div className="text-accent">{qd.icon}</div>
                <span className="text-xs font-medium text-text">{qd.name}</span>
              </a>
            ))}
          </div>
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
