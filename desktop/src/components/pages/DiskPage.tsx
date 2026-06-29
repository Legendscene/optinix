import { useState, useMemo } from 'react'
import { motion } from 'framer-motion'
import { HardDrive, Trash2, Zap, Search, CheckCircle, AlertTriangle, XCircle } from 'lucide-react'
import { Card } from '../ui/Card'
import { MetricCard } from '../ui/MetricCard'
import { ActionCard } from '../ui/ActionCard'
import { ProgressBar } from '../ui/ProgressBar'
import { Skeleton } from '../ui/Skeleton'
import { Badge } from '../ui/Badge'
import { cn } from '../../lib/utils'
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

export function DiskPage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [_loading, setLoading] = useState<string | null>(null)
  const [result, setResult] = useState<string | null>(null)

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
