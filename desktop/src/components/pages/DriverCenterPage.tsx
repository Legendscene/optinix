import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  Shield, Download, HardDrive, RefreshCw, Search,
  AlertTriangle, CheckCircle, Package, Upload,
  Bug, Eye, Archive, Wrench,
} from 'lucide-react'
import { Card } from '../ui/Card'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { Skeleton } from '../ui/Skeleton'
import { MetricCard } from '../ui/MetricCard'
import { ActionCard } from '../ui/ActionCard'
import { PageHero } from '../ui/PageHero'
import { cn } from '../../lib/utils'
import { api } from '../../lib/api'

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.05 } } }
const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }

interface DriverEntry {
  name: string
  version: string
  latest_version: string
  update_available: boolean
  category: string
  manufacturer: string
  download_url?: string
}

interface ProblemDevice {
  name: string
  code: number
  problem: string
}

interface VulnerableDriver {
  name: string
  driver: string
  risk: string
}

export default function DriverCenterPage() {
  const [health, setHealth] = useState<{ total: number; outdated: number; problems: number; vulnerable: number } | null>(null)
  const [drivers, setDrivers] = useState<DriverEntry[]>([])
  const [problemDevices, setProblemDevices] = useState<ProblemDevice[]>([])
  const [vulnerableDrivers, setVulnerableDrivers] = useState<VulnerableDriver[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingAction, setLoadingAction] = useState<string | null>(null)
  const [filter, setFilter] = useState('')
  const [result, setResult] = useState<{ key: string; message: string; success: boolean } | null>(null)
  const [showVulnerable, setShowVulnerable] = useState(false)

  const scan = useCallback(async () => {
    setLoading(true)
    setResult(null)
    try {
      const [healthRes, driversRes, problemsRes] = await Promise.all([
        api.driverHealth(),
        api.driverCheckUpdates(),
        api.driverProblemDevices(),
      ])
      setHealth(healthRes)
      setDrivers(driversRes.drivers)
      setProblemDevices(problemsRes.devices)
    } catch {
      setHealth(null)
      setDrivers([])
      setProblemDevices([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { scan() }, [scan])

  const runAction = async (key: string, fn: () => Promise<unknown>, successMsg: string) => {
    setLoadingAction(key)
    setResult(null)
    try {
      const res = await fn()
      if (key === 'vulnerable-scan') {
        setVulnerableDrivers((res as { vulnerable: VulnerableDriver[] }).vulnerable)
        setShowVulnerable(true)
      }
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
    <motion.div variants={container} initial="hidden" animate="show" className="page space-y-6">
            <motion.div variants={item}>
        <PageHero
          title="Driver Center"
          subtitle="Comprehensive driver health, backup, and security scanning"
          icon={<Shield size={19} />}
        />
      </motion.div>

      <motion.div variants={item} className="flex flex-wrap gap-2">
        <Button variant="primary" icon={<RefreshCw className="w-4 h-4" />} loading={loading} onClick={scan}>Scan All</Button>
        <Button variant="secondary" icon={<Archive className="w-4 h-4" />} loading={loadingAction === 'backup'} onClick={() => runAction('backup', () => api.driverBackup(), 'Driver backup created')}>Backup Drivers</Button>
        <Button variant="secondary" icon={<Upload className="w-4 h-4" />} loading={loadingAction === 'restore'} onClick={() => runAction('restore', () => api.driverRestore(), 'Drivers restored')}>Restore Drivers</Button>
        <Button variant="ghost" icon={<Bug className="w-4 h-4" />} loading={loadingAction === 'vulnerable-scan'} onClick={() => runAction('vulnerable-scan', () => api.driverVulnerableScan(), 'Vulnerability scan complete')}>Vulnerability Scan</Button>
      </motion.div>

      {!loading && health && (
        <motion.div variants={item} className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricCard icon={<HardDrive className="w-5 h-5" />} label="Total Drivers" value={String(health.total)} />
          <MetricCard icon={<AlertTriangle className="w-5 h-5" />} label="Outdated" value={String(health.outdated)} trend={health.outdated > 0 ? { value: String(health.outdated), up: false } : undefined} />
          <MetricCard icon={<Wrench className="w-5 h-5" />} label="Problem Devices" value={String(health.problems)} trend={health.problems > 0 ? { value: String(health.problems), up: false } : undefined} />
          <MetricCard icon={<Shield className="w-5 h-5" />} label="Vulnerable" value={String(health.vulnerable)} trend={health.vulnerable > 0 ? { value: String(health.vulnerable), up: false } : undefined} />
        </motion.div>
      )}

      {problemDevices.length > 0 && (
        <motion.div variants={item}>
          <Card padding="lg" className="border-red/30">
            <div className="flex items-center gap-2 mb-3">
              <AlertTriangle className="w-5 h-5 text-red" />
              <h2 className="text-sm font-semibold text-text">Problem Devices</h2>
              <Badge variant="danger">{problemDevices.length}</Badge>
            </div>
            <div className="space-y-2">
              {problemDevices.map((d, i) => (
                <div key={i} className="flex items-center justify-between p-2 rounded-lg bg-surface-2">
                  <div>
                    <p className="text-sm font-medium text-text">{d.name}</p>
                    <p className="text-xs text-text-secondary">Code {d.code}: {d.problem}</p>
                  </div>
                  <Badge variant="danger">Issue</Badge>
                </div>
              ))}
            </div>
          </Card>
        </motion.div>
      )}

      {showVulnerable && vulnerableDrivers.length > 0 && (
        <motion.div variants={item}>
          <Card padding="lg" className="border-yellow/30">
            <div className="flex items-center gap-2 mb-3">
              <Shield className="w-5 h-5 text-yellow" />
              <h2 className="text-sm font-semibold text-text">Vulnerable Drivers</h2>
              <Badge variant="warning">{vulnerableDrivers.length}</Badge>
            </div>
            <div className="space-y-2">
              {vulnerableDrivers.map((d, i) => (
                <div key={i} className="flex items-center justify-between p-2 rounded-lg bg-surface-2">
                  <div>
                    <p className="text-sm font-medium text-text">{d.name}</p>
                    <p className="text-xs text-text-secondary">{d.driver} — {d.risk}</p>
                  </div>
                  <Badge variant="warning">{d.risk}</Badge>
                </div>
              ))}
            </div>
          </Card>
        </motion.div>
      )}

      {showVulnerable && vulnerableDrivers.length === 0 && (
        <motion.div variants={item}>
          <Card padding="lg" className="border-green/30">
            <div className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-green" />
              <p className="text-sm font-medium text-green">No vulnerable drivers found</p>
            </div>
          </Card>
        </motion.div>
      )}

      <motion.div variants={item}>
        <Card padding="lg">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Search className="w-5 h-5 text-accent" />
              <h2 className="text-sm font-semibold text-text">All Drivers</h2>
              {!loading && <Badge>{drivers.length}</Badge>}
            </div>
            <input
              type="text" placeholder="Search drivers..."
              value={filter} onChange={e => setFilter(e.target.value)}
              className="px-3 py-1.5 rounded-lg bg-surface-2 border border-border text-sm text-text placeholder:text-text-tertiary focus:outline-none focus:border-accent w-48"
            />
          </div>
          {loading ? (
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
                        <span className="text-[11px] text-text-secondary">{d.manufacturer}</span>
                      </div>
                    </div>
                    <span className="text-xs text-text-secondary shrink-0 font-mono">{d.version} → {d.latest_version}</span>
                  </div>
                  <Badge variant={d.update_available ? 'warning' : 'success'}>
                    {d.update_available ? 'Update Available' : 'Up to Date'}
                  </Badge>
                  {d.update_available && (
                    <div className="flex gap-1 shrink-0">
                      <Button size="sm" variant="secondary" icon={<Download className="w-3 h-3" />}
                        loading={loadingAction === `download-${d.name}`}
                        onClick={() => runAction(`download-${d.name}`, () => api.driverDownload(d.name), `${d.name} downloaded`)}>
                        DL
                      </Button>
                      <Button size="sm" variant="primary" icon={<Package className="w-3 h-3" />}
                        loading={loadingAction === `install-${d.name}`}
                        onClick={() => runAction(`install-${d.name}`, () => api.driverInstall(d.name), `${d.name} installed`)}>
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

      <motion.div variants={item} className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ActionCard icon={<Archive className="w-5 h-5" />} title="Driver Backup" desc="Create a full backup of all installed drivers for safe recovery" tags={['Backup']} onClick={() => runAction('backup', () => api.driverBackup(), 'Backup completed')} />
        <ActionCard icon={<Upload className="w-5 h-5" />} title="Driver Restore" desc="Restore drivers from a previous backup point" tags={['Restore']} variant="default" onClick={() => runAction('restore', () => api.driverRestore(), 'Restore completed')} />
        <ActionCard icon={<Bug className="w-5 h-5" />} title="Vulnerability Scan" desc="Check for known vulnerable drivers on your system" tags={['Security']} variant="danger" onClick={() => runAction('vulnerable-scan', () => api.driverVulnerableScan(), 'Vulnerability scan complete')} />
        <ActionCard icon={<Eye className="w-5 h-5" />} title="Problem Devices" desc="View devices with driver issues or errors in Device Manager" tags={['Diagnostics']} onClick={() => { if (problemDevices.length) setResult({ key: 'problems', message: `${problemDevices.length} problem devices found`, success: true }) }} />
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
