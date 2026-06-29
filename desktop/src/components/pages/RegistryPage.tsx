import { useState, useCallback, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  Database,
  AlertTriangle,
  Shield,
  CheckCircle2,
  RefreshCw,
  Download,
  RotateCw,
  Search,
  ChevronRight,
  X,
  AlertCircle as AlertCircleIcon,
} from 'lucide-react'
import { Card } from '../ui/Card'
import { MetricCard } from '../ui/MetricCard'
import { ActionCard } from '../ui/ActionCard'
import { Button } from '../ui/Button'
import { Skeleton } from '../ui/Skeleton'
import { cn } from '../../lib/utils'
import type { SystemInfo } from '../../types'
import { api } from '../../lib/api'

interface RegistryIssue {
  id: string
  category: string
  title: string
  desc: string
  severity: 'critical' | 'high' | 'medium' | 'low'
  selected: boolean
  path: string
  fixable: boolean
}

export default function RegistryPage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const [issues, setIssues] = useState<RegistryIssue[]>([])
  const [loadingAction, setLoadingAction] = useState<string | null>(null)
  const [result, setResult] = useState<{ key: string; message: string; success: boolean } | null>(null)
  const [scanProgress, setScanProgress] = useState(0)
  const [scanning, setScanning] = useState(false)
  const [backupCount, setBackupCount] = useState(0)
  const [backups, setBackups] = useState<{ name: string; size: number; created: string }[]>([])

  useEffect(() => {
    api.registryScan().then(res => {
      setIssues(res.issues.map((iss, i) => ({
        id: String(i + 1),
        category: iss.type,
        title: iss.name,
        desc: iss.description,
        severity: iss.severity as RegistryIssue['severity'],
        selected: false,
        path: iss.path,
        fixable: iss.fixable,
      })))
    }).catch(() => {})
    api.registryBackups().then(res => {
      setBackups(res.backups)
      setBackupCount(res.backups.length)
    }).catch(() => {})
  }, [])

  const runScan = useCallback(async () => {
    setScanning(true)
    setScanProgress(0)
    setResult(null)
    try {
      const res = await api.registryScan()
      const mapped: RegistryIssue[] = res.issues.map((iss, i) => ({
        id: String(i + 1),
        category: iss.type,
        title: iss.name,
        desc: iss.description,
        severity: iss.severity as RegistryIssue['severity'],
        selected: false,
        path: iss.path,
        fixable: iss.fixable,
      }))
      setIssues(mapped)
      setResult({ key: 'scan', message: `Scan complete — ${mapped.length} issues found`, success: true })
    } catch (e) {
      setResult({ key: 'scan', message: e instanceof Error ? e.message : 'Scan failed', success: false })
    } finally {
      setScanning(false)
      setScanProgress(0)
    }
  }, [])

  const fixSelected = useCallback(async () => {
    const selected = issues.filter(i => i.selected)
    setLoadingAction('fix')
    setResult(null)
    try {
      const res = await api.registryFix(selected.map(i => i.path))
      const fixedCount = res.results.filter(r => r.success).length
      setIssues(prev => prev.filter(i => !i.selected))
      setResult({ key: 'fix', message: `Fixed ${fixedCount} of ${selected.length} registry issues`, success: res.success })
    } catch (e) {
      setResult({ key: 'fix', message: e instanceof Error ? e.message : 'Fix failed', success: false })
    } finally {
      setLoadingAction(null)
    }
  }, [issues])

  const backupRegistry = useCallback(async () => {
    setLoadingAction('backup')
    setResult(null)
    try {
      const res = await api.registryBackup()
      setBackups(res.backups)
      setBackupCount(res.backups.length)
      setResult({ key: 'backup', message: res.message, success: res.success })
    } catch (e) {
      setResult({ key: 'backup', message: e instanceof Error ? e.message : 'Backup failed', success: false })
    } finally {
      setLoadingAction(null)
    }
  }, [])

  const restoreRegistry = useCallback(async () => {
    setLoadingAction('restore')
    setResult(null)
    try {
      if (backups.length === 0) throw new Error('No backups available')
      const res = await api.registryRestore(backups[0].name)
      setResult({ key: 'restore', message: res.message, success: res.success })
    } catch (e) {
      setResult({ key: 'restore', message: e instanceof Error ? e.message : 'Restore failed', success: false })
    } finally {
      setLoadingAction(null)
    }
  }, [backups])

  const selectAll = useCallback(() => setIssues(prev => prev.map(i => ({ ...i, selected: true }))), [])
  const selectNone = useCallback(() => setIssues(prev => prev.map(i => ({ ...i, selected: false }))), [])

  const severityColor = (s: string) => s === 'critical' ? 'text-red' : s === 'high' ? 'text-red' : s === 'medium' ? 'text-yellow' : 'text-blue'
  const severityBg = (s: string) => s === 'critical' ? 'bg-red-dim' : s === 'high' ? 'bg-red-dim' : s === 'medium' ? 'bg-yellow-dim' : 'bg-blue-dim'

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
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} variant="rectangular" height="100px" />)}
        </div>
        <Skeleton variant="rectangular" height="300px" />
      </div>
    )
  }

  const selectedCount = issues.filter(i => i.selected).length
  const criticalCount = issues.filter(i => i.severity === 'critical').length
  const highCount = issues.filter(i => i.severity === 'high').length

  return (
    <motion.div initial="hidden" animate="show" className="p-6 space-y-6">
      <motion.div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="p-2 rounded-xl bg-surface-2 text-accent"><Database className="w-6 h-6" /></div>
            <h1 className="text-2xl font-bold text-text">Registry Cleaner</h1>
          </div>
          <p className="text-sm text-text-secondary ml-11">Clean and optimize Windows registry</p>
        </div>
        <motion.div className="flex items-center gap-2">
          <span className={cn('px-3 py-1 rounded-full text-xs font-medium', criticalCount > 0 ? 'bg-red-dim text-red' : 'bg-green-dim text-green')}>
            {criticalCount > 0 ? `${criticalCount} Critical` : 'Healthy'}
          </span>
          <span className="px-3 py-1 rounded-full bg-yellow-dim text-yellow text-xs font-medium">{highCount} High</span>
        </motion.div>
      </motion.div>

      <motion.div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard icon={<Database className="w-5 h-5" />} label="Total Issues" value={String(issues.length)} progress={Math.min(issues.length * 5, 100)} sub="Registry entries" />
        <MetricCard icon={<AlertTriangle className="w-5 h-5" />} label="Critical" value={String(criticalCount)} progressColor="#ef4444" sub="Immediate action needed" />
        <MetricCard icon={<Shield className="w-5 h-5" />} label="Backups" value={String(backupCount)} sub="Available restore points" />
        <MetricCard icon={<RotateCw className="w-5 h-5" />} label="Last Clean" value={scanning ? 'Scanning...' : '2 days ago'} sub={scanning ? `${scanProgress}%` : 'Last maintenance'} />
      </motion.div>

      <motion.div className="flex flex-col gap-4">
        <Card padding="lg">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-text flex items-center gap-2"><Search className="w-4 h-4 text-accent" />Registry Issues</h2>
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" icon={<ChevronRight className="w-4 h-4" />} onClick={selectAll} disabled={scanning}>Select All</Button>
              <Button variant="ghost" size="sm" icon={<X className="w-4 h-4" />} onClick={selectNone} disabled={scanning}>Deselect All</Button>
            </div>
          </div>
          {scanning ? (
            <div className="space-y-2">
              <div className="flex items-center gap-3 mb-4">
                <div className="flex-1 h-2 rounded-full bg-surface-3 overflow-hidden">
                  <motion.div initial={{ width: 0 }} animate={{ width: `${scanProgress}%` }} className="h-full bg-accent rounded-full" />
                </div>
                <span className="text-sm text-text-secondary">{scanProgress}%</span>
              </div>
              <div className="space-y-2">
                {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} variant="rectangular" height="56px" />)}
              </div>
            </div>
          ) : issues.length ? (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {issues.map((issue, i) => (
                <motion.div key={issue.id} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.03 }} className="group relative p-4 rounded-xl bg-surface-2/60 hover:bg-surface-2 transition-colors">
                  <div className="flex items-start gap-3">
                    <input type="checkbox" checked={issue.selected} onChange={() => setIssues(prev => prev.map(i => i.id === issue.id ? { ...i, selected: !i.selected } : i))} className="mt-1 w-4 h-4 rounded border-border bg-surface-3 text-accent focus:ring-accent" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={cn('px-2 py-0.5 rounded text-[10px] font-medium uppercase', severityBg(issue.severity), severityColor(issue.severity))}>{issue.severity.toUpperCase()}</span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-surface-3 text-text-tertiary">{issue.category}</span>
                      </div>
                      <h3 className="text-sm font-semibold text-text">{issue.title}</h3>
                      <p className="text-xs text-text-secondary mt-1">{issue.desc}</p>
                    </div>
                    <ChevronRight className="w-4 h-4 text-text-tertiary group-hover:text-accent transition-colors shrink-0" />
                  </div>
                </motion.div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-8">
              <CheckCircle2 className="w-12 h-12 text-green mb-3" />
              <p className="text-text-secondary text-center">No registry issues found</p>
              <Button variant="ghost" size="sm" icon={<RefreshCw className="w-4 h-4" />} onClick={runScan} className="mt-3">Scan Again</Button>
            </div>
          )}
        </Card>

        <div className="flex flex-col gap-4">
          <ActionCard icon={<Search className="w-5 h-5" />} title="Scan Registry" desc="Full registry scan for invalid entries" tags={['Scan']} variant="default" onClick={runScan} loading={scanning} />
          <ActionCard icon={<CheckCircle2 className="w-5 h-5" />} title="Fix Selected Issues" desc={`Fix ${selectedCount} selected registry issues`} tags={['Fix']} variant="success" onClick={fixSelected} loading={loadingAction === 'fix'} disabled={selectedCount === 0} />
          <ActionCard icon={<Download className="w-5 h-5" />} title="Backup Registry" desc="Create restore point before making changes" tags={['Backup']} variant="default" onClick={backupRegistry} loading={loadingAction === 'backup'} />
          <ActionCard icon={<RotateCw className="w-5 h-5" />} title="Restore Registry" desc="Restore from previous backup" tags={['Restore']} variant="default" onClick={restoreRegistry} loading={loadingAction === 'restore'} disabled={loadingAction !== null} />
        </div>
      </motion.div>

      <motion.div className="p-4 rounded-xl bg-surface-1 border border-border">
        <div className="flex items-center gap-2 mb-3">
          <AlertCircleIcon className="w-4 h-4 text-yellow" />
          <span className="text-sm font-semibold text-text">Important Warning</span>
        </div>
        <p className="text-xs text-text-secondary">
          Modifying the Windows registry can cause system instability if done incorrectly. Always create a backup before making changes.
          The issues listed above are detected automatically — review each carefully before fixing. Critical and high severity issues should be addressed first.
        </p>
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