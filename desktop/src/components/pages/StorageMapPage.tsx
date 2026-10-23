import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { FolderTree, HardDrive, Scan, XCircle, File, Folder, Loader2, BarChart3, Table } from 'lucide-react'
import { Card } from '../ui/Card'
import { Button } from '../ui/Button'
import { ProgressBar } from '../ui/ProgressBar'
import { Badge } from '../ui/Badge'
import { Skeleton } from '../ui/Skeleton'
import { PageHero } from '../ui/PageHero'
import { api } from '../../lib/api'
import { formatBytes } from '../../lib/utils'
import type { SystemInfo, StorageScanResult, StorageNode } from '../../types'

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.05 } } }
const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }

const categoryColors: Record<string, string> = {
  System: 'var(--chart-1)', Media: 'var(--color-cyan)', Documents: 'var(--color-green)',
  Archives: 'var(--color-yellow)', Applications: 'var(--color-yellow)', Code: 'var(--chart-2)', Other: 'var(--color-text-tertiary)',
}

const fileExtCategory: Record<string, string> = {
  dll: 'System', sys: 'System', exe: 'Applications', msi: 'Applications',
  mp4: 'Media', mkv: 'Media', avi: 'Media', mov: 'Media', wmv: 'Media',
  mp3: 'Media', wav: 'Media', flac: 'Media', jpg: 'Media', jpeg: 'Media',
  png: 'Media', gif: 'Media', bmp: 'Media', svg: 'Media',
  doc: 'Documents', docx: 'Documents', pdf: 'Documents', txt: 'Documents',
  xls: 'Documents', xlsx: 'Documents', ppt: 'Documents', pptx: 'Documents',
  zip: 'Archives', rar: 'Archives', '7z': 'Archives', tar: 'Archives', gz: 'Archives',
  ts: 'Code', tsx: 'Code', js: 'Code', jsx: 'Code', py: 'Code',
  rs: 'Code', go: 'Code', java: 'Code', cpp: 'Code', c: 'Code',
  json: 'Code', xml: 'Code', yaml: 'Code', html: 'Code', css: 'Code',
}

function categorizeFile(ext: string): string {
  return fileExtCategory[ext.toLowerCase()] || 'Other'
}

function TreemapNode({ node }: { node: StorageNode; depth?: number }) {
  if (!node.children || node.children.length === 0) return null
  return (
    <div className="grid gap-px" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(60px, 1fr))' }}>
      {node.children.slice(0, 30).map(child => (
        <div
          key={child.path}
          className="relative rounded overflow-hidden cursor-pointer group"
          style={{
            backgroundColor: child.category_color || categoryColors[child.category || 'Other'] || 'var(--color-text-tertiary)',
            aspectRatio: '1',
            opacity: 0.8 + (child.percentage || 0) * 0.2,
          }}
          title={`${child.name}: ${formatBytes(child.size)}`}
        >
          <span className="absolute bottom-1 left-1 text-[9px] text-white/80 truncate w-[90%] opacity-0 group-hover:opacity-100 transition-opacity">
            {child.name}
          </span>
        </div>
      ))}
    </div>
  )
}

export function StorageMapPage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const [drives, setDrives] = useState<{ letter: string; label: string }[]>([])
  const [selectedDrive, setSelectedDrive] = useState('C:\\')
  const [scanning, setScanning] = useState(false)
  const [result, setResult] = useState<StorageScanResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [expandedFolder, setExpandedFolder] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const fetchDrives = useCallback(async () => {
    try {
      const d = await api.storageDriveInfo() as { drives: { letter: string; label: string }[] }
      setDrives(d.drives || [])
    } catch { /* ignore */ }
  }, [])

  const fetchResults = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const r = await api.storageResults()
      setResult(r as StorageScanResult)
    } catch {
      setError('Failed to load storage scan results')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchDrives(); fetchResults() }, [fetchDrives, fetchResults])

  const startScan = useCallback(async () => {
    setScanning(true)
    setError(null)
    try {
      await api.storageScan(selectedDrive)
      await fetchResults()
    } catch {
      setError('Scan failed to start')
    } finally {
      setScanning(false)
    }
  }, [selectedDrive, fetchResults])

  const cancelScan = useCallback(async () => {
    try {
      await api.storageCancelScan()
      setScanning(false)
    } catch { /* ignore */ }
  }, [])

  if (!systemInfo) {
    return (
      <div className="page space-y-6">
        <div><Skeleton className="h-8 w-48 mb-1" /><Skeleton className="h-4 w-64" /></div>
        <div className="grid grid-cols-3 gap-4"><Skeleton className="h-32 col-span-3" /></div>
        <Skeleton className="h-64" />
      </div>
    )
  }

  const usedPct = result ? Math.round((result.used_space / result.total_size) * 100) : 0
  const freePct = result ? 100 - usedPct : 0

  const fileTypeData = result?.file_type_chart
    ? Object.entries(result.file_type_chart).map(([cat, data]) => ({
        category: cat,
        size: data.size as number,
        count: data.count as number,
        color: (data.color as string) || categoryColors[cat] || 'var(--color-text-tertiary)',
      })).sort((a, b) => b.size - a.size)
    : []

  const largestFiles = (result?.largest_files || []).slice(0, 20)
  const largestFolders = (result?.largest_folders || []).slice(0, 20)

  const maxFileTypeSize = fileTypeData.length > 0 ? Math.max(...fileTypeData.map(d => d.size)) : 1

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="page space-y-6">
      <motion.div variants={item}>
        <PageHero
          title="Storage Visualizer"
          subtitle="Analyze disk usage with WinDirStat-style visualization"
          icon={<FolderTree size={19} />}
        />
      </motion.div>

      <motion.div variants={item} className="flex items-center gap-3 flex-wrap">
        <select
          value={selectedDrive}
          onChange={e => setSelectedDrive(e.target.value)}
          className="px-3 py-2 rounded-lg bg-surface-2 border border-border text-text text-sm focus:outline-none focus:border-accent"
        >
          {drives.length > 0 ? drives.map(d => (
            <option key={d.letter} value={d.letter + '\\'}>{d.letter} - {d.label}</option>
          )) : (
            <option value="C:\\">C:\ (System)</option>
          )}
        </select>
        <Button variant="primary" size="sm" icon={<Scan size={14} />} onClick={startScan} loading={scanning}>
          Start Scan
        </Button>
        {scanning && (
          <Button variant="danger" size="sm" icon={<XCircle size={14} />} onClick={cancelScan}>
            Cancel
          </Button>
        )}
        {scanning && (
          <div className="flex items-center gap-2 text-sm text-accent">
            <Loader2 size={16} className="animate-spin" />
            <span>Scanning...</span>
          </div>
        )}
      </motion.div>

      {error && (
        <motion.div variants={item} className="p-4 rounded-xl bg-red-dim border border-red/30 text-red text-sm">{error}</motion.div>
      )}

      {loading && !result && (
        <motion.div variants={item} className="space-y-4">
          <Skeleton className="h-32" />
          <Skeleton className="h-48" />
          <Skeleton className="h-64" />
        </motion.div>
      )}

      {result && (
        <>
          <motion.div variants={item}>
            <Card padding="lg">
              <div className="flex items-center gap-2 mb-4">
                <HardDrive size={18} className="text-accent" />
                <h2 className="text-sm font-semibold text-text">Drive Overview — {result.drive}</h2>
              </div>
              <div className="grid grid-cols-4 gap-4 mb-4">
                <div>
                  <span className="text-xs text-text-tertiary">Total Size</span>
                  <p className="text-lg font-semibold text-text">{formatBytes(result.total_size)}</p>
                </div>
                <div>
                  <span className="text-xs text-text-tertiary">Used</span>
                  <p className="text-lg font-semibold text-text">{formatBytes(result.used_space)}</p>
                </div>
                <div>
                  <span className="text-xs text-text-tertiary">Free</span>
                  <p className="text-lg font-semibold text-text">{formatBytes(result.free_space)}</p>
                </div>
                <div>
                  <span className="text-xs text-text-tertiary">Used %</span>
                  <p className="text-lg font-semibold text-text">{usedPct}%</p>
                </div>
              </div>
              <ProgressBar value={usedPct} size="lg" label="Usage" />
              <div className="flex items-center gap-4 mt-3">
                <div className="flex items-center gap-1.5 text-xs">
                  <span className="w-3 h-3 rounded bg-accent" />
                  <span className="text-text-secondary">Used ({usedPct}%)</span>
                </div>
                <div className="flex items-center gap-1.5 text-xs">
                  <span className="w-3 h-3 rounded bg-surface-3" />
                  <span className="text-text-secondary">Free ({freePct}%)</span>
                </div>
              </div>
              {result.scan_time_ms != null && (
                <p className="text-xs text-text-tertiary mt-3">
                  Scan completed in {(result.scan_time_ms / 1000).toFixed(1)}s
                  {result.truncated &&
                    ` — partial view, stopped after ${result.folder_limit?.toLocaleString() ?? 'the folder'} folders`}
                </p>
              )}
            </Card>
          </motion.div>

          {fileTypeData.length > 0 && (
            <motion.div variants={item}>
              <Card padding="lg">
                <div className="flex items-center gap-2 mb-4">
                  <BarChart3 size={18} className="text-accent" />
                  <h2 className="text-sm font-semibold text-text">File Type Breakdown</h2>
                </div>
                <div className="space-y-2.5">
                  {fileTypeData.map(cat => (
                    <div key={cat.category}>
                      <div className="flex items-center justify-between text-xs mb-1">
                        <div className="flex items-center gap-2">
                          <span className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: cat.color }} />
                          <span className="text-text font-medium">{cat.category}</span>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-text-secondary font-mono">{formatBytes(cat.size)}</span>
                          <span className="text-text-tertiary">({cat.count} files)</span>
                        </div>
                      </div>
                      <div className="h-2 rounded-full bg-surface-3 overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{ width: `${(cat.size / maxFileTypeSize) * 100}%`, backgroundColor: cat.color }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            </motion.div>
          )}

          {largestFiles.length > 0 && (
            <motion.div variants={item}>
              <Card padding="lg">
                <div className="flex items-center gap-2 mb-4">
                  <File size={18} className="text-accent" />
                  <h2 className="text-sm font-semibold text-text">Largest Files (Top {largestFiles.length})</h2>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-text-tertiary border-b border-border">
                        <th className="text-left py-2 px-2 w-8">#</th>
                        <th className="text-left py-2 px-2">File Name</th>
                        <th className="text-right py-2 px-2">Size</th>
                        <th className="text-center py-2 px-2">Ext</th>
                        <th className="text-center py-2 px-2">Category</th>
                      </tr>
                    </thead>
                    <tbody>
                      {largestFiles.map((f, i) => {
                        const ext = f.extension || f.path.split('.').pop() || ''
                        const cat = categorizeFile(ext)
                        return (
                          <tr key={f.path} className="border-b border-border/50 hover:bg-surface-2/50 transition-colors">
                            <td className="py-1.5 px-2 text-text-tertiary">{i + 1}</td>
                            <td className="py-1.5 px-2 text-text truncate max-w-[300px]" title={f.path}>{f.path.split('\\').pop() || f.path}</td>
                            <td className="py-1.5 px-2 text-right font-mono text-text-secondary">{formatBytes(f.size)}</td>
                            <td className="py-1.5 px-2 text-center"><Badge variant="accent">{ext}</Badge></td>
                            <td className="py-1.5 px-2 text-center">
                              <Badge variant="default" className="!bg-surface-3">{cat}</Badge>
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </Card>
            </motion.div>
          )}

          {largestFolders.length > 0 && (
            <motion.div variants={item}>
              <Card padding="lg">
                <div className="flex items-center gap-2 mb-4">
                  <Folder size={18} className="text-accent" />
                  <h2 className="text-sm font-semibold text-text">Largest Folders (Top {largestFolders.length})</h2>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-text-tertiary border-b border-border">
                        <th className="text-left py-2 px-2 w-8">#</th>
                        <th className="text-left py-2 px-2">Folder Path</th>
                        <th className="text-right py-2 px-2">Size</th>
                        <th className="text-right py-2 px-2">File Count</th>
                      </tr>
                    </thead>
                    <tbody>
                      {largestFolders.map((f, i) => (
                        <tr key={f.path} className="border-b border-border/50 hover:bg-surface-2/50 transition-colors">
                          <td className="py-1.5 px-2 text-text-tertiary">{i + 1}</td>
                          <td className="py-1.5 px-2 text-text truncate max-w-[400px]" title={f.path}>{f.path}</td>
                          <td className="py-1.5 px-2 text-right font-mono text-text-secondary">{formatBytes(f.size)}</td>
                          <td className="py-1.5 px-2 text-right text-text-secondary">
                            {'file_count' in f && (f as { file_count?: number }).file_count != null ? String((f as { file_count?: number }).file_count) : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            </motion.div>
          )}

          {result.tree && (
            <motion.div variants={item}>
              <Card padding="lg">
                <div className="flex items-center gap-2 mb-4">
                  <Table size={18} className="text-accent" />
                  <h2 className="text-sm font-semibold text-text">Treemap Visualization</h2>
                  {expandedFolder && (
                    <Button size="sm" variant="ghost" onClick={() => setExpandedFolder(null)} className="ml-auto">
                      Reset
                    </Button>
                  )}
                </div>
                <TreemapNode node={result.tree} depth={0} />
              </Card>
            </motion.div>
          )}
        </>
      )}

      {!loading && !result && !error && (
        <motion.div variants={item}>
          <Card padding="lg">
            <div className="flex flex-col items-center gap-3 py-8">
              <FolderTree size={40} className="text-text-tertiary" />
              <p className="text-sm text-text-secondary">No storage scan data available. Click "Start Scan" to analyze your drive.</p>
            </div>
          </Card>
        </motion.div>
      )}
    </motion.div>
  )
}
