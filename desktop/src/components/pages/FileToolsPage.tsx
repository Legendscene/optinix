import { useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  Files, Copy, Search, Trash2, HardDrive,
  AlertTriangle, Shield, FolderOpen, Gauge
} from 'lucide-react'
import { Card } from '../ui/Card'
import { Button } from '../ui/Button'
import { Skeleton } from '../ui/Skeleton'
import { cn, formatBytes } from '../../lib/utils'
import { api } from '../../lib/api'

const tabs = ['duplicates', 'large-files', 'shredder', 'disk-optimize'] as const
type Tab = typeof tabs[number]

const tabLabels: Record<Tab, string> = {
  duplicates: 'Duplicate Finder',
  'large-files': 'Large Files',
  shredder: 'File Shredder',
  'disk-optimize': 'Disk Optimization'}

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.05 } }}

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 }}

export function FileToolsPage() {
  const [activeTab, setActiveTab] = useState<Tab>('duplicates')
  const [loading, setLoading] = useState<string | null>(null)
  const [result, setResult] = useState<{ key: string; message: string; success: boolean } | null>(null)

  // Duplicates
  const [duplicates, setDuplicates] = useState<{ original: string; duplicate: string; size: number; original_name: string; duplicate_name: string }[]>([])

  // Large files
  const [largeFiles, setLargeFiles] = useState<{ path: string; name: string; size: number; category: string }[]>([])
  const [sizeThreshold, setSizeThreshold] = useState(500)

  // Shredder
  const [shredPath, setShredPath] = useState('')
  const [shredPasses, setShredPasses] = useState(3)

  // Disk
  const [drive, setDrive] = useState('C:')
  const [driveInfo, setDriveInfo] = useState<{ total?: number; used?: number; free?: number; percent?: number; model?: string; is_ssd?: boolean } | null>(null)

  const runAction = async (key: string, fn: () => Promise<unknown>, successMsg: string) => {
    setLoading(key)
    setResult(null)
    try {
      const res = await fn() as Record<string, unknown>
      if (key === 'scan-duplicates') setDuplicates((res as { duplicates: typeof duplicates }).duplicates)
      if (key === 'scan-large') setLargeFiles((res as { large_files: typeof largeFiles }).large_files)
      if (key === 'drive-info' && res) setDriveInfo(res as typeof driveInfo)
      setResult({ key, message: successMsg, success: true })
    } catch (e) {
      setResult({ key, message: e instanceof Error ? e.message : 'Operation failed', success: false })
    } finally {
      setLoading(null)
    }
  }

  const loadDriveInfo = useCallback(async () => {
    setLoading('drive-info')
    try {
      const res = await api.diskDriveInfo(drive)
      setDriveInfo(res)
    } catch { /* ignore */ }
    setLoading(null)
  }, [drive])

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-6">
      <motion.div variants={item}>
        <div className="flex items-center gap-3 mb-1">
          <Files className="w-6 h-6 text-accent" />
          <h1 className="text-2xl font-bold tracking-tight text-text">File Tools</h1>
        </div>
        <p className="text-sm text-text-secondary ml-9">Duplicate files, large files, shredder, and disk optimization</p>
      </motion.div>

      <motion.div variants={item} className="flex gap-1 bg-surface-2 rounded-xl p-1 w-fit">
        {tabs.map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={cn(
              'px-4 py-2 rounded-lg text-sm font-medium transition-all',
              activeTab === tab ? 'bg-accent text-white' : 'text-text-secondary hover:text-text'
            )}
          >
            {tabLabels[tab]}
          </button>
        ))}
      </motion.div>

      {/* Duplicate Finder */}
      {activeTab === 'duplicates' && (
        <motion.div variants={item} className="space-y-4">
          <Card padding="lg">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Copy className="w-5 h-5 text-accent" />
                <h2 className="text-sm font-semibold text-text">Duplicate File Finder</h2>
              </div>
              <Button
                variant="primary"
                icon={<Search className="w-4 h-4" />}
                loading={loading === 'scan-duplicates'}
                onClick={() => runAction('scan-duplicates', () => api.fileDuplicates(), 'Duplicate scan complete')}
              >
                Scan for Duplicates
              </Button>
            </div>
            {duplicates.length > 0 ? (
              <div className="divide-y divide-border max-h-[400px] overflow-y-auto">
                {duplicates.map((d, i) => (
                  <div key={i} className="flex items-center justify-between py-3 first:pt-0 last:pb-0 gap-4">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-text truncate">{d.original_name}</p>
                      <p className="text-[11px] text-text-tertiary truncate">{d.original}</p>
                      <p className="text-[11px] text-text-tertiary truncate mt-0.5">→ {d.duplicate}</p>
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                      <span className="text-xs text-text-secondary font-mono">{formatBytes(d.size)}</span>
                      <Button
                        size="sm"
                        variant="danger"
                        icon={<Trash2 className="w-3 h-3" />}
                        loading={loading === `delete-${i}`}
                        onClick={() => runAction(`delete-${i}`, () => api.fileDelete(d.duplicate), 'Duplicate deleted')}
                      >
                        Delete
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            ) : loading !== 'scan-duplicates' ? (
              <p className="text-xs text-text-tertiary py-6 text-center">Click "Scan for Duplicates" to find duplicate files.</p>
            ) : (
              <div className="space-y-3">
                {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-14 rounded-xl" />)}
              </div>
            )}
          </Card>
        </motion.div>
      )}

      {/* Large Files */}
      {activeTab === 'large-files' && (
        <motion.div variants={item} className="space-y-4">
          <Card padding="lg">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <HardDrive className="w-5 h-5 text-accent" />
                <h2 className="text-sm font-semibold text-text">Large File Finder</h2>
              </div>
              <Button
                variant="primary"
                icon={<Search className="w-4 h-4" />}
                loading={loading === 'scan-large'}
                onClick={() => runAction('scan-large', () => api.fileLarge(sizeThreshold), 'Large file scan complete')}
              >
                Scan for Large Files
              </Button>
            </div>
            <div className="flex items-center gap-4 mb-4">
              <label className="text-xs text-text-secondary">Min size: {sizeThreshold} MB</label>
              <input
                type="range"
                min={100}
                max={5000}
                step={100}
                value={sizeThreshold}
                onChange={e => setSizeThreshold(Number(e.target.value))}
                className="flex-1 accent-accent"
              />
              <span className="text-xs text-text-tertiary">5000 MB</span>
            </div>
            {largeFiles.length > 0 ? (
              <div className="divide-y divide-border max-h-[400px] overflow-y-auto">
                {largeFiles.map((f, i) => (
                  <div key={i} className="flex items-center justify-between py-3 first:pt-0 last:pb-0 gap-4">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-text truncate">{f.name}</p>
                      <p className="text-[11px] text-text-tertiary truncate">{f.path}</p>
                      <p className="text-[11px] text-text-tertiary">{f.category}</p>
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                      <span className="text-xs text-text-secondary font-mono">{formatBytes(f.size)}</span>
                      <Button
                        size="sm"
                        variant="danger"
                        icon={<Trash2 className="w-3 h-3" />}
                        loading={loading === `delete-${i}`}
                        onClick={() => runAction(`delete-${i}`, () => api.fileDelete(f.path), `${f.name} deleted`)}
                      >
                        Delete
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            ) : loading !== 'scan-large' ? (
              <p className="text-xs text-text-tertiary py-6 text-center">Click "Scan for Large Files" to find large files.</p>
            ) : (
              <div className="space-y-3">
                {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-14 rounded-xl" />)}
              </div>
            )}
          </Card>
        </motion.div>
      )}

      {/* Shredder */}
      {activeTab === 'shredder' && (
        <motion.div variants={item} className="space-y-4">
          <Card padding="lg">
            <div className="flex items-center gap-2 mb-4">
              <Shield className="w-5 h-5 text-accent" />
              <h2 className="text-sm font-semibold text-text">File Shredder</h2>
            </div>
            <div className="p-3 rounded-xl border border-yellow/30 bg-yellow-dim mb-4">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-yellow shrink-0" />
                <p className="text-xs text-yellow">Warning: Shredded files cannot be recovered. This operation is permanent.</p>
              </div>
            </div>
            <div className="space-y-4">
              <div>
                <label className="text-xs text-text-secondary mb-1 block">File or Folder Path</label>
                <input
                  type="text"
                  value={shredPath}
                  onChange={e => setShredPath(e.target.value)}
                  placeholder="C:\path\to\file.exe"
                  className="w-full px-3 py-2 rounded-lg bg-surface-2 border border-border text-sm text-text placeholder:text-text-tertiary focus:outline-none focus:border-accent"
                />
              </div>
              <div>
                <label className="text-xs text-text-secondary mb-1 block">Passes: {shredPasses}</label>
                <input
                  type="range"
                  min={1}
                  max={7}
                  value={shredPasses}
                  onChange={e => setShredPasses(Number(e.target.value))}
                  className="w-full accent-accent"
                />
                <div className="flex justify-between text-[10px] text-text-tertiary">
                  <span>1 (Quick)</span>
                  <span>7 (Maximum)</span>
                </div>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="danger"
                  icon={<Trash2 className="w-4 h-4" />}
                  loading={loading === 'shred-file'}
                  disabled={!shredPath.trim()}
                  onClick={() => runAction('shred-file', () => api.fileShred(shredPath, shredPasses), 'File shredded')}
                >
                  Shred File
                </Button>
                <Button
                  variant="danger"
                  icon={<FolderOpen className="w-4 h-4" />}
                  loading={loading === 'shred-folder'}
                  disabled={!shredPath.trim()}
                  onClick={() => runAction('shred-folder', () => api.fileShredFolder(shredPath, shredPasses), 'Folder shredded')}
                >
                  Shred Folder
                </Button>
              </div>
            </div>
          </Card>
        </motion.div>
      )}

      {/* Disk Optimization */}
      {activeTab === 'disk-optimize' && (
        <motion.div variants={item} className="space-y-4">
          <Card padding="lg">
            <div className="flex items-center gap-2 mb-4">
              <Gauge className="w-5 h-5 text-accent" />
              <h2 className="text-sm font-semibold text-text">Disk Optimization</h2>
            </div>
            <div className="flex items-center gap-3 mb-4">
              <label className="text-xs text-text-secondary">Drive</label>
              <select
                value={drive}
                onChange={e => { setDrive(e.target.value); setDriveInfo(null) }}
                className="px-3 py-1.5 rounded-lg bg-surface-2 border border-border text-sm text-text focus:outline-none focus:border-accent"
              >
                {['C:', 'D:', 'E:', 'F:'].map(d => <option key={d} value={d}>{d}</option>)}
              </select>
              <Button size="sm" variant="secondary" onClick={loadDriveInfo} loading={loading === 'drive-info'}>
                Load Info
              </Button>
            </div>
            {driveInfo && (
              <div className="grid grid-cols-2 gap-3 mb-4">
                <div className="p-3 rounded-xl bg-surface-2">
                  <p className="text-[11px] text-text-tertiary">Model</p>
                  <p className="text-sm font-medium text-text truncate">{driveInfo.model || 'Unknown'}</p>
                </div>
                <div className="p-3 rounded-xl bg-surface-2">
                  <p className="text-[11px] text-text-tertiary">Type</p>
                  <p className="text-sm font-medium text-text">{driveInfo.is_ssd ? 'SSD' : 'HDD'}</p>
                </div>
                <div className="p-3 rounded-xl bg-surface-2">
                  <p className="text-[11px] text-text-tertiary">Used</p>
                  <p className="text-sm font-medium text-text">{driveInfo.used ? formatBytes(driveInfo.used) : '--'}</p>
                </div>
                <div className="p-3 rounded-xl bg-surface-2">
                  <p className="text-[11px] text-text-tertiary">Free</p>
                  <p className="text-sm font-medium text-text">{driveInfo.free ? formatBytes(driveInfo.free) : '--'}</p>
                </div>
              </div>
            )}
            <div className="flex gap-2">
              <Button
                variant="secondary"
                icon={<HardDrive className="w-4 h-4" />}
                loading={loading === 'defrag'}
                onClick={() => runAction('defrag', () => api.diskDefrag(drive), `${drive} defragmented`)}
              >
                Defragment
              </Button>
              <Button
                variant="secondary"
                icon={<Gauge className="w-4 h-4" />}
                loading={loading === 'trim'}
                onClick={() => runAction('trim', () => api.diskTrim(drive), `${drive} TRIM completed`)}
              >
                TRIM
              </Button>
            </div>
          </Card>
        </motion.div>
      )}

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
