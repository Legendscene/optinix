import { useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  Trash2,
  HardDrive,
  RefreshCw,
  FileText,
  Delete,
  Trash,
  Search,
  FolderOpen,
} from 'lucide-react'
import { Card } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { MetricCard } from '../ui/MetricCard'
import { ActionCard } from '../ui/ActionCard'
import { Skeleton } from '../ui/Skeleton'
import { cn, formatBytes } from '../../lib/utils'
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

export function CleanupPage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const [loadingAction, setLoadingAction] = useState<string | null>(null)
  const [result, setResult] = useState<{ key: string; message: string; success: boolean } | null>(null)
  const [cleaned, setCleaned] = useState<Record<string, boolean>>({})
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

  const runAction = async (key: string, fn: () => Promise<unknown>, successMsg: string) => {
    setLoadingAction(key)
    setResult(null)
    try {
      await fn()
      setCleaned((prev) => ({ ...prev, [key]: true }))
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

  const totalCache = scanResults?.find((c) => /cache/i.test(c.name))?.bytes ?? 0
  const tempFiles = scanResults?.find((c) => /temp/i.test(c.name))?.bytes ?? 0
  const recycleBin = scanResults?.find((c) => /recycle/i.test(c.name))?.bytes ?? 0

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="p-6 space-y-6">
      <motion.div variants={item}>
        <div className="flex items-center gap-3 mb-1">
          <Trash2 className="w-6 h-6 text-accent" />
          <h1 className="text-2xl font-bold text-text">Cleanup</h1>
        </div>
        <p className="text-sm text-text-secondary ml-9">Remove junk and free up space</p>
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-3 gap-4">
        <MetricCard icon={<HardDrive className="w-5 h-5" />} label="System Cache" value={formatBytes(totalCache)} progress={65} sub="Temporary and cache files" />
        <MetricCard icon={<FileText className="w-5 h-5" />} label="Temp Files" value={formatBytes(tempFiles)} progress={35} sub="User and system temp data" />
        <MetricCard icon={<Delete className="w-5 h-5" />} label="Recycle Bin" value={formatBytes(recycleBin)} progress={45} sub={`${Math.floor(recycleBin / (100 * 1024 ** 2))}+ items`} />
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-4">
        <ActionCard
          icon={<Trash2 className="w-5 h-5" />}
          title="Full System Cleanup"
          desc="Clear all caches, temp files, and junk data"
          tags={['Recommended']}
          onClick={() => runAction('cleanup', () => api.optimize('cleanup'), 'System cleanup complete')}
        />
        <ActionCard
          icon={<RefreshCw className="w-5 h-5" />}
          title="Flush DNS"
          desc="Clear DNS resolver cache to fix connectivity"
          tags={['Network']}
          onClick={() => runAction('flushdns', () => api.flushDns(), 'DNS cache flushed')}
        />
        <ActionCard
          icon={<FileText className="w-5 h-5" />}
          title="Office Telemetry Cleanup"
          desc="Remove Office telemetry data and logs"
          tags={['Office']}
          onClick={() => runAction('officetel', () => api.disableOfficeTelemetry(), 'Office telemetry cleaned')}
        />
        <ActionCard
          icon={<Trash className="w-5 h-5" />}
          title="Empty Recycle Bin"
          desc="Permanently delete all recycled items"
          tags={['Storage']}
          onClick={() => runAction('recycle', () => api.optimize('cleanup'), 'Recycle bin emptied')}
        />
        <ActionCard
          icon={<Search className="w-5 h-5" />}
          title="Deep Scan"
          desc="Scan disk for detailed category breakdown"
          tags={['Analysis']}
          onClick={deepScan}
          loading={scanLoading}
        />
      </motion.div>

      {scanResults && scanResults.length > 0 && (
        <motion.div variants={item}>
          <Card>
            <h2 className="text-sm font-semibold text-text mb-3 flex items-center gap-2"><FolderOpen className="w-4 h-4 text-accent" />Scan Results — {formatBytes(scanTotal)} total</h2>
            <div className="space-y-2">
              {scanResults.map((cat) => (
                <div key={cat.name} className="flex items-center justify-between py-2">
                  <div className="flex-1 min-w-0 mr-4">
                    <p className="text-sm font-medium text-text truncate">{cat.name}</p>
                    <p className="text-xs text-text-tertiary truncate">{cat.description} &middot; {cat.items} items</p>
                  </div>
                  <span className="text-sm font-mono text-text-secondary shrink-0">{formatBytes(cat.bytes)}</span>
                </div>
              ))}
            </div>
          </Card>
        </motion.div>
      )}

      <motion.div variants={item}>
        <Card>
          <h2 className="text-sm font-semibold text-text mb-3">Cleanup History</h2>
          <div className="space-y-2">
            {[
              { key: 'cleanup', label: 'System Cleanup' },
              { key: 'flushdns', label: 'Flush DNS' },
              { key: 'officetel', label: 'Office Telemetry' },
              { key: 'recycle', label: 'Recycle Bin' },
            ].map((c) => (
              <div key={c.key} className="flex items-center justify-between py-2">
                <span className="text-sm text-text">{c.label}</span>
                {cleaned[c.key] ? (
                  <Badge variant="success">Completed</Badge>
                ) : (
                  <Badge variant="default">Pending</Badge>
                )}
              </div>
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

      {loadingAction && (
        <div className="flex items-center gap-2 text-xs text-text-secondary">
          <svg className="animate-spin h-3 w-3 text-accent" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
          Cleaning system...
        </div>
      )}
    </motion.div>
  )
}
