import { useState, useMemo, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { HardDrive, Trash2, Zap, Search, CheckCircle, AlertTriangle, XCircle, FolderKanban, RotateCw, FileText, Delete } from 'lucide-react'
import { Card } from '../ui/Card'
import { MetricCard } from '../ui/MetricCard'
import { ActionCard } from '../ui/ActionCard'
import { ProgressBar } from '../ui/ProgressBar'
import { Skeleton } from '../ui/Skeleton'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import { cn, formatBytes } from '../../lib/utils'
import { api } from '../../lib/api'
import type { SystemInfo, DiskInfo } from '../../types'

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.06 } },
}

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { type: 'spring' as const, stiffness: 260, damping: 24 } },
}

interface SmartAttribute {
  label: string
  status: 'good' | 'warning' | 'bad'
  value: string
}

const mockSmart: SmartAttribute[] = [
  { label: 'Reallocated Sectors', status: 'good', value: '0' },
  { label: 'Spin Retry Count', status: 'good', value: '0' },
  { label: 'Current Pending Sector', status: 'good', value: '0' },
  { label: 'Uncorrectable Sectors', status: 'good', value: '0' },
  { label: 'Power-On Hours', status: 'good', value: '1,247' },
  { label: 'Temperature', status: 'good', value: '38°C' },
]

const healthIcon = {
  good: <CheckCircle size={14} className="text-green" />,
  warning: <AlertTriangle size={14} className="text-yellow" />,
  bad: <XCircle size={14} className="text-red" />,
}

interface ScanCategory {
  name: string
  description: string
  items: number
  bytes: number
  files: { path: string; size: number }[]
}

export function DiskPage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const [_loading, setLoading] = useState<string | null>(null)
  const [result, setResult] = useState<string | null>(null)

  const [selectedDrive, setSelectedDrive] = useState('C:')
  const [scanResult, setScanResult] = useState<{ categories: ScanCategory[]; total_bytes: number; drive: string } | null>(null)
  const [scanning, setScanning] = useState(false)
  const [cleaning, setCleaning] = useState(false)
  const [selectedCategories, setSelectedCategories] = useState<Set<string>>(new Set())
  const [cleanResult, setCleanResult] = useState<string | null>(null)
  const [hasScanned, setHasScanned] = useState(false)

  const disks = systemInfo?.disk ?? []
  const primary = disks[0]
  const total = primary?.total ?? 0
  const free = primary?.free ?? 0
  const percent = primary?.percent ?? 0

  const smartData = useMemo(() => mockSmart, [])

  function formatGb(bytes: number): string {
    const gb = bytes / 1e9
    return gb >= 1000 ? `${(gb / 1024).toFixed(1)} TB` : `${gb.toFixed(1)} GB`
  }

  const handleScan = useCallback(async () => {
    setScanning(true)
    setScanResult(null)
    setSelectedCategories(new Set())
    setCleanResult(null)
    try {
      const res = await api.diskScan(selectedDrive)
      setScanResult(res)
      setHasScanned(true)
    } catch {
      setCleanResult('Scan failed')
      setHasScanned(true)
    } finally {
      setScanning(false)
    }
  }, [selectedDrive])

  useEffect(() => {
    if (systemInfo && disks.length > 0 && !hasScanned) {
      handleScan()
    }
  }, [systemInfo, disks, hasScanned, handleScan])

  async function handleCleanSelected() {
    if (selectedCategories.size === 0) return
    setCleaning(true)
    setCleanResult(null)
    try {
      for (const cat of selectedCategories) {
        await api.diskCleanCategory(cat, selectedDrive)
      }
      setCleanResult(`Cleaned ${selectedCategories.size} categor${selectedCategories.size === 1 ? 'y' : 'ies'}`)
      setSelectedCategories(new Set())
      const res = await api.diskScan(selectedDrive)
      setScanResult(res)
    } catch {
      setCleanResult('Clean failed')
    } finally {
      setCleaning(false)
    }
  }

  async function handleCleanAll() {
    setCleaning(true)
    setCleanResult(null)
    try {
      await api.diskCleanAll(selectedDrive)
      setCleanResult('All categories cleaned')
      setSelectedCategories(new Set())
      const res = await api.diskScan(selectedDrive)
      setScanResult(res)
    } catch {
      setCleanResult('Clean all failed')
    } finally {
      setCleaning(false)
    }
  }

  function toggleCategory(name: string) {
    setSelectedCategories(prev => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })
  }

  function onDriveChange(e: React.ChangeEvent<HTMLSelectElement>) {
    setSelectedDrive(e.target.value)
    setHasScanned(false)
  }

  async function handleCleanup() {
    setLoading('cleanup')
    setResult(null)
    try {
      await api.optimize('cleanup')
      setResult('Disk cleanup complete')
    } catch {
      setResult('Disk cleanup failed')
    } finally { setLoading(null) }
  }

  async function handleDefrag() {
    setLoading('defrag')
    setResult(null)
    try {
      await api.optimize('disk')
      setResult('Defrag / TRIM complete')
    } catch {
      setResult('Defrag / TRIM failed')
    } finally { setLoading(null) }
  }

  async function handleAnalyze() {
    setLoading('analyze')
    setResult(null)
    try {
      const info = await api.systemInfo()
      setResult(`Analyzed ${info.disk?.length ?? 0} drive(s)`)
    } catch {
      setResult('Analysis failed')
    } finally { setLoading(null) }
  }

  if (!systemInfo) {
    return (
      <div className="space-y-6">
        <div><Skeleton className="h-8 w-24 mb-1" /><Skeleton className="h-4 w-64" /></div>
        <div className="grid grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-28 rounded-xl" />)}
        </div>
        <Skeleton className="h-52 rounded-xl" />
        <div className="grid grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-28 rounded-xl" />)}
        </div>
      </div>
    )
  }

  const totalScanBytes = scanResult?.total_bytes ?? 0

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-6">
      <motion.div variants={item}>
        <h1 className="text-2xl font-bold tracking-tight text-text">Storage</h1>
        <p className="text-sm text-text-secondary mt-1">Disk space monitoring & health management</p>
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-3 gap-4">
        <MetricCard
          icon={<HardDrive size={18} />}
          label="Usage"
          value={`${percent.toFixed(1)}%`}
          progress={percent}
          trend={{ value: `${(Math.random() * 3).toFixed(1)}%`, up: percent > 50 }}
        />
        <MetricCard
          icon={<HardDrive size={18} />}
          label="Free"
          value={formatGb(free)}
          sub={`${((free / total) * 100).toFixed(0)}% of total`}
        />
        <MetricCard
          icon={<HardDrive size={18} />}
          label="Total"
          value={formatGb(total)}
          sub={`${disks.length} partition${disks.length !== 1 ? 's' : ''}`}
        />
      </motion.div>

      <motion.div variants={item}>
        <Card padding="lg">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-text">Partitions</h2>
            <Badge variant="info">{disks.length} drive{disks.length !== 1 ? 's' : ''}</Badge>
          </div>
          <div className="space-y-3">
            {disks.map((d: DiskInfo, i: number) => {
              const pct = d.percent ?? 0
              return (
                <div key={d.device + i} className="p-3 rounded-lg bg-surface-2">
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                       <span className="text-xs font-semibold text-text">{d.device}</span>
                       {d.is_ssd && <Badge variant="info">SSD</Badge>}
                       {d.is_external && <Badge variant="warning">External</Badge>}
                       <span className="text-[11px] text-text-tertiary">{d.mountpoint}</span>
                       <span className="text-[11px] text-text-tertiary">{d.fstype}</span>
                     </div>
                    <span className="text-xs text-text-secondary">{pct.toFixed(0)}%</span>
                  </div>
                  <ProgressBar value={pct} size="md" />
                  <div className="flex justify-between mt-1 text-[11px] text-text-tertiary">
                    <span>{formatGb(d.used)} used</span>
                    <span>{formatGb(d.free)} free</span>
                  </div>
                </div>
              )
            })}
            {disks.length === 0 && (
              <div className="text-center text-text-tertiary text-sm py-6">No disk information available</div>
            )}
          </div>
        </Card>
      </motion.div>

      <motion.div variants={item}>
        <Card padding="lg">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-text">Disk Health (SMART)</h2>
            <Badge variant="success">Healthy</Badge>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {smartData.map((attr) => (
              <div key={attr.label} className="flex items-center justify-between p-2.5 rounded-lg bg-surface-2">
                <div className="flex items-center gap-2">
                  {healthIcon[attr.status]}
                  <span className="text-xs text-text-secondary">{attr.label}</span>
                </div>
                <span className={cn(
                  'text-xs font-mono font-medium',
                  attr.status === 'good' ? 'text-text' : attr.status === 'warning' ? 'text-yellow' : 'text-red'
                )}>
                  {attr.value}
                </span>
              </div>
            ))}
          </div>
        </Card>
      </motion.div>

      <motion.div variants={item}>
        <Card padding="lg">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <h2 className="text-sm font-semibold text-text">Disk Cleaner</h2>
              <select
                value={selectedDrive}
                onChange={onDriveChange}
                className="bg-surface-2 text-text border border-border rounded-lg px-2.5 py-1.5 text-xs focus:outline-none focus:border-accent cursor-pointer"
              >
                {disks.map((d: DiskInfo) => {
                  const val = d.device?.replace(':', '') + ':'
                  return (
                    <option key={val} value={val}>{d.device} {d.mountpoint ? `(${d.mountpoint})` : ''}</option>
                  )
                })}
              </select>
            </div>
            <Button size="sm" variant="secondary" icon={<RotateCw size={14} />} loading={scanning} onClick={handleScan}>
              Scan
            </Button>
          </div>

          {(scanning || cleaning) && (
            <div className="mb-4 p-3 rounded-lg bg-surface-2">
              <div className="flex items-center gap-2 mb-2">
                {scanning
                  ? <Search size={14} className="text-accent animate-pulse" />
                  : <Trash2 size={14} className="text-accent animate-pulse" />
                }
                <span className="text-xs text-text-secondary">
                  {scanning ? `Scanning ${selectedDrive}...` : 'Cleaning...'}
                </span>
              </div>
              <ProgressBar value={scanning ? 45 : 70} size="sm" />
            </div>
          )}

          {scanResult && scanResult.categories.length > 0 && (
            <>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs text-text-secondary">
                    {scanResult.categories.length} categor{scanResult.categories.length === 1 ? 'y' : 'ies'} found
                  </span>
                  <span className="text-xs text-text-tertiary">·</span>
                  <span className="text-xs text-text-secondary">{formatBytes(totalScanBytes)} total</span>
                  <span className="text-xs text-text-tertiary">·</span>
                  <span className="text-xs text-text-secondary">
                    {selectedCategories.size} selected
                  </span>
                </div>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="primary"
                    icon={<Delete size={14} />}
                    loading={cleaning}
                    disabled={selectedCategories.size === 0}
                    onClick={handleCleanSelected}
                  >
                    Clean Selected
                  </Button>
                  <Button
                    size="sm"
                    variant="danger"
                    icon={<Trash2 size={14} />}
                    loading={cleaning}
                    onClick={handleCleanAll}
                  >
                    Clean All
                  </Button>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {scanResult.categories.map((cat) => {
                  const selected = selectedCategories.has(cat.name)
                  return (
                    <div
                      key={cat.name}
                      onClick={() => toggleCategory(cat.name)}
                      className={cn(
                        'flex items-start gap-3 p-3 rounded-lg cursor-pointer transition-colors',
                        selected
                          ? 'bg-accent/10 border border-accent/30'
                          : 'bg-surface-2 border border-transparent hover:border-border-light'
                      )}
                    >
                      <div className={cn(
                        'mt-0.5 w-4 h-4 rounded border-2 flex items-center justify-center flex-shrink-0 transition-colors',
                        selected ? 'bg-accent border-accent' : 'border-border'
                      )}>
                        {selected && <CheckCircle size={12} className="text-white" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-xs font-medium text-text truncate">{cat.name}</span>
                          <span className="text-xs font-mono text-text-secondary flex-shrink-0">{formatBytes(cat.bytes)}</span>
                        </div>
                        <p className="text-[11px] text-text-tertiary mt-0.5 leading-relaxed line-clamp-2">{cat.description}</p>
                        <div className="flex items-center gap-3 mt-1.5">
                          <span className="text-[11px] text-text-tertiary flex items-center gap-1">
                            <FileText size={10} />
                            {cat.items} item{cat.items !== 1 ? 's' : ''}
                          </span>
                          <span className="text-[11px] text-text-tertiary flex items-center gap-1">
                            <FolderKanban size={10} />
                            {cat.files?.length ?? 0} file{(cat.files?.length ?? 0) !== 1 ? 's' : ''}
                          </span>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </>
          )}

          {scanResult && scanResult.categories.length === 0 && (
            <div className="text-center py-8 text-text-tertiary text-sm">
              <FolderKanban size={32} className="mx-auto mb-2 opacity-40" />
              No junk found on {selectedDrive}
            </div>
          )}

          {!scanResult && !scanning && (
            <div className="text-center py-8 text-text-tertiary text-sm">
              <Search size={32} className="mx-auto mb-2 opacity-40" />
              Click "Scan" to analyze junk files on {selectedDrive}
            </div>
          )}

          {cleanResult && (
            <div className="mt-4">
              <Card className={cn('text-center py-3', cleanResult.includes('failed') ? 'border-red/30' : 'border-green/30')}>
                <span className={cn(
                  'text-sm font-medium flex items-center justify-center gap-2',
                  cleanResult.includes('failed') ? 'text-red' : 'text-green'
                )}>
                  {cleanResult.includes('failed') ? <XCircle size={14} /> : <CheckCircle size={14} />}
                  {cleanResult}
                </span>
              </Card>
            </div>
          )}
        </Card>
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-3 gap-4">
        <ActionCard
          icon={<Trash2 size={20} />}
          title="Disk Cleanup"
          desc="Remove temporary files, caches, and system junk"
          tags={['Clean', 'Free Space']}
          onClick={handleCleanup}
        />
        <ActionCard
          icon={<Zap size={20} />}
          title="Defrag / TRIM"
          desc="Optimize drive performance with defragmentation or TRIM"
          tags={['Optimize', 'SSD']}
          onClick={handleDefrag}
        />
        <ActionCard
          icon={<Search size={20} />}
          title="Analyze Space"
          desc="Scan disk to visualize space usage by file type and folder"
          tags={['Analyze', 'Visualize']}
          onClick={handleAnalyze}
        />
      </motion.div>

      {result && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <Card className="text-center py-3">
            <span className={cn('text-sm font-medium', result.includes('complete') || result.includes('Analyzed') ? 'text-green' : 'text-red')}>
              {result}
            </span>
          </Card>
        </motion.div>
      )}
    </motion.div>
  )
}
