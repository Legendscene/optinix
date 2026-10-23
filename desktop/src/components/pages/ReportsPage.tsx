import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  FileText, FileJson, Download, Trash2, Eye, Plus, Loader2, FileBarChart,
  ChevronDown, X, FileSpreadsheet, Clock, AlertCircle,
} from 'lucide-react'
import { Card } from '../ui/Card'
import { PageHero } from '../ui/PageHero'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { Skeleton } from '../ui/Skeleton'
import { cn, formatBytes } from '../../lib/utils'
import { api } from '../../lib/api'
import type { SystemInfo, ReportInfo } from '../../types'

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.05 } } }
const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }

const reportTypes = [
  { value: 'health', label: 'Health Report' },
  { value: 'optimization', label: 'Optimization Report' },
  { value: 'hardware', label: 'Hardware Report' },
  { value: 'driver', label: 'Driver Report' },
  { value: 'battery', label: 'Battery Report' },
  { value: 'network', label: 'Network Report' },
  { value: 'all', label: 'Full System Report' },
]

const typeBadge: Record<string, 'success' | 'info' | 'warning' | 'accent' | 'danger'> = {
  health: 'success',
  optimization: 'accent',
  hardware: 'info',
  driver: 'warning',
  battery: 'danger',
  network: 'info',
}

export function ReportsPage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const [activeTab, setActiveTab] = useState<'my-reports' | 'generate'>('my-reports')
  const [reports, setReports] = useState<ReportInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedType, setSelectedType] = useState('health')
  const [selectedFormat, setSelectedFormat] = useState('html')
  const [typeOpen, setTypeOpen] = useState(false)
  const [formatOpen, setFormatOpen] = useState(false)
  const [viewingReport, setViewingReport] = useState<{ id: string; content: string; format: string } | null>(null)
  const [viewLoading, setViewLoading] = useState(false)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  const loadReports = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.reportsList()
      setReports(res.reports ?? [])
    } catch {
      setError('Failed to load reports')
      setReports([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadReports() }, [loadReports])

  const handleGenerate = async () => {
    setGenerating(true)
    setError(null)
    setSuccessMsg(null)
    try {
      await api.reportsGenerate(selectedType, selectedFormat)
      setSuccessMsg(`${reportTypes.find(t => t.value === selectedType)?.label} (${selectedFormat.toUpperCase()}) generated successfully`)
      loadReports()
      setActiveTab('my-reports')
    } catch {
      setError('Failed to generate report')
    } finally {
      setGenerating(false)
    }
  }

  const handleView = async (id: string, format: string) => {
    setViewLoading(true)
    setError(null)
    try {
      const content = await api.reportsGet(id) as unknown as string
      setViewingReport({ id, content: typeof content === 'string' ? content : JSON.stringify(content, null, 2), format })
    } catch {
      setError('Failed to load report content')
    } finally {
      setViewLoading(false)
    }
  }

  const handleDelete = async (id: string) => {
    setError(null)
    try {
      await api.reportsDelete(id)
      setReports(prev => prev.filter(r => r.report_id !== id))
    } catch {
      setError('Failed to delete report')
    }
  }

  const selectedTypeLabel = reportTypes.find(t => t.value === selectedType)?.label ?? 'Select type'

  if (!systemInfo) {
    return (
      <div className="page space-y-6">
        <div><Skeleton variant="text" width="200px" height="28px" /><Skeleton variant="text" width="300px" height="16px" className="mt-2" /></div>
        <div className="flex gap-4"><Skeleton variant="rectangular" height="40px" width="200px" /><Skeleton variant="rectangular" height="40px" width="120px" /></div>
        <Skeleton variant="rectangular" height="300px" />
      </div>
    )
  }

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="page space-y-6">
      <motion.div variants={item}>
        <PageHero
          eyebrow="Reports"
          title="Report Center"
          subtitle="Generate a snapshot of system state, then keep it as HTML or a data file. Reports are written from the same readings the rest of the app shows."
          icon={<FileBarChart size={19} />}
          stats={[
            { label: 'Stored', value: String(reports.length), hint: 'reports on disk' },
            { label: 'Format', value: selectedFormat.toUpperCase(), hint: 'for new reports' },
            { label: 'Type', value: selectedType, hint: 'for new reports' },
            { label: 'Status', value: generating ? 'Building' : 'Idle', tone: generating ? 'accent' : 'default' },
          ]}
        />
      </motion.div>

      <motion.div variants={item} className="flex items-center gap-3">
        <div className="relative">
          <button
            onClick={() => setTypeOpen(!typeOpen)}
            className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border bg-surface-2 text-sm text-text hover:bg-surface-3 transition-colors"
          >
            <FileText className="w-4 h-4 text-text-secondary" />
            {selectedTypeLabel}
            <ChevronDown className="w-3.5 h-3.5 text-text-secondary ml-1" />
          </button>
          {typeOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setTypeOpen(false)} />
              <div className="absolute top-full mt-1 left-0 z-20 w-48 rounded-xl border border-border bg-surface-1 shadow-xl py-1 overflow-hidden">
                {reportTypes.map(t => (
                  <button
                    key={t.value}
                    onClick={() => { setSelectedType(t.value); setTypeOpen(false) }}
                    className={cn(
                      'w-full text-left px-3 py-2 text-sm transition-colors',
                      selectedType === t.value ? 'text-accent bg-accent-dim/20' : 'text-text-secondary hover:text-text hover:bg-surface-2'
                    )}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>

        <div className="relative">
          <button
            onClick={() => setFormatOpen(!formatOpen)}
            className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border bg-surface-2 text-sm text-text hover:bg-surface-3 transition-colors"
          >
            <FileJson className="w-4 h-4 text-text-secondary" />
            {selectedFormat.toUpperCase()}
            <ChevronDown className="w-3.5 h-3.5 text-text-secondary ml-1" />
          </button>
          {formatOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setFormatOpen(false)} />
              <div className="absolute top-full mt-1 left-0 z-20 w-32 rounded-xl border border-border bg-surface-1 shadow-xl py-1 overflow-hidden">
                {['html', 'json'].map(f => (
                  <button
                    key={f}
                    onClick={() => { setSelectedFormat(f); setFormatOpen(false) }}
                    className={cn(
                      'w-full text-left px-3 py-2 text-sm transition-colors',
                      selectedFormat === f ? 'text-accent bg-accent-dim/20' : 'text-text-secondary hover:text-text hover:bg-surface-2'
                    )}
                  >
                    {f.toUpperCase()}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>

        <Button
          variant="primary"
          size="md"
          icon={generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
          onClick={handleGenerate}
          loading={generating}
        >
          Generate
        </Button>
      </motion.div>

      <motion.div variants={item} className="flex gap-1 p-1 rounded-xl bg-surface-2 w-fit">
        {(['my-reports', 'generate'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={cn(
              'px-4 py-2 rounded-lg text-sm font-medium transition-all',
              activeTab === tab
                ? 'bg-surface-1 text-text shadow-sm'
                : 'text-text-secondary hover:text-text'
            )}
          >
            {tab === 'my-reports' ? 'My Reports' : 'Generate New'}
          </button>
        ))}
      </motion.div>

      {error && (
        <motion.div variants={item} className="p-4 rounded-xl border border-red/30 bg-red-dim/10">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red" />
            <span className="text-sm text-text">{error}</span>
            <button onClick={() => setError(null)} className="ml-auto p-1 rounded-md hover:bg-surface-2 text-text-secondary"><X className="w-4 h-4" /></button>
          </div>
        </motion.div>
      )}

      {successMsg && (
        <motion.div variants={item} className="p-4 rounded-xl border border-green/30 bg-green-dim/10">
          <div className="flex items-center gap-3">
            <FileSpreadsheet className="w-5 h-5 text-green" />
            <span className="text-sm text-text">{successMsg}</span>
            <button onClick={() => setSuccessMsg(null)} className="ml-auto p-1 rounded-md hover:bg-surface-2 text-text-secondary"><X className="w-4 h-4" /></button>
          </div>
        </motion.div>
      )}

      {activeTab === 'generate' && (
        <motion.div variants={item}>
          <Card padding="lg">
            <h2 className="text-sm font-semibold text-text mb-4 flex items-center gap-2">
              <Plus className="w-4 h-4 text-accent" />
              Generate New Report
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              {reportTypes.filter(t => t.value !== 'all').map(t => (
                <button
                  key={t.value}
                  onClick={() => setSelectedType(t.value)}
                  className={cn(
                    'flex items-center gap-3 p-3 rounded-xl border transition-all text-left',
                    selectedType === t.value
                      ? 'border-accent/50 bg-accent-dim/10'
                      : 'border-border bg-surface-2/50 hover:bg-surface-2'
                  )}
                >
                  <div className={cn(
                    'p-2 rounded-lg',
                    selectedType === t.value ? 'bg-accent-dim text-accent' : 'bg-surface-3 text-text-secondary'
                  )}>
                    <FileText className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-sm font-medium text-text">{t.label}</div>
                    <div className="text-[11px] text-text-tertiary">Generate a {t.label.toLowerCase()}</div>
                  </div>
                </button>
              ))}
            </div>
            <div className="flex items-center gap-3 pt-4 border-t border-border">
              <span className="text-xs text-text-secondary">Format:</span>
              <div className="flex gap-2">
                {['html', 'json'].map(f => (
                  <button
                    key={f}
                    onClick={() => setSelectedFormat(f)}
                    className={cn(
                      'px-3 py-1.5 rounded-lg text-xs font-medium border transition-all',
                      selectedFormat === f
                        ? 'border-accent bg-accent-dim/20 text-accent'
                        : 'border-border text-text-secondary hover:text-text'
                    )}
                  >
                    {f.toUpperCase()}
                  </button>
                ))}
              </div>
              <Button
                variant="primary"
                size="md"
                icon={generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                onClick={handleGenerate}
                loading={generating}
                className="ml-auto"
              >
                Generate Now
              </Button>
            </div>
          </Card>
        </motion.div>
      )}

      {activeTab === 'my-reports' && (
        <motion.div variants={item}>
          <Card padding="lg">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-text flex items-center gap-2">
                <FileText className="w-4 h-4 text-accent" />
                My Reports
              </h2>
              <Button variant="ghost" size="sm" icon={<Loader2 className="w-3.5 h-3.5" />} onClick={loadReports} loading={loading}>
                Refresh
              </Button>
            </div>

            {loading && (
              <div className="space-y-3">
                {Array.from({ length: 4 }).map((_, i) => (
                  <Skeleton key={i} variant="rectangular" height="48px" />
                ))}
              </div>
            )}

            {!loading && reports.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left py-3 px-2 text-[11px] text-text-tertiary uppercase tracking-wider font-medium">Type</th>
                      <th className="text-left py-3 px-2 text-[11px] text-text-tertiary uppercase tracking-wider font-medium">Format</th>
                      <th className="text-left py-3 px-2 text-[11px] text-text-tertiary uppercase tracking-wider font-medium">Date</th>
                      <th className="text-left py-3 px-2 text-[11px] text-text-tertiary uppercase tracking-wider font-medium">Size</th>
                      <th className="text-right py-3 px-2 text-[11px] text-text-tertiary uppercase tracking-wider font-medium">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {reports.map((r, i) => (
                      <motion.tr
                        key={r.report_id}
                        initial={{ opacity: 0, y: -6 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.03 }}
                        className="border-b border-border/50 hover:bg-surface-2/40 transition-colors"
                      >
                        <td className="py-3 px-2">
                          <Badge variant={typeBadge[r.type] ?? 'default'}>{r.type}</Badge>
                        </td>
                        <td className="py-3 px-2">
                          <div className="flex items-center gap-1.5">
                            {r.format === 'json' ? <FileJson className="w-3.5 h-3.5 text-text-secondary" /> : <FileText className="w-3.5 h-3.5 text-text-secondary" />}
                            <span className="text-text">{r.format.toUpperCase()}</span>
                          </div>
                        </td>
                        <td className="py-3 px-2">
                          <div className="flex items-center gap-1.5">
                            <Clock className="w-3.5 h-3.5 text-text-tertiary" />
                            <span className="text-text-secondary text-xs">{new Date(r.timestamp).toLocaleDateString()} {new Date(r.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                          </div>
                        </td>
                        <td className="py-3 px-2 text-text-secondary text-xs">{formatBytes(r.size)}</td>
                        <td className="py-3 px-2 text-right">
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              icon={<Eye className="w-3.5 h-3.5" />}
                              onClick={() => handleView(r.report_id, r.format)}
                              title="View"
                            />
                            <Button
                              variant="ghost"
                              size="sm"
                              icon={<Trash2 className="w-3.5 h-3.5 text-red" />}
                              onClick={() => handleDelete(r.report_id)}
                              title="Delete"
                            />
                          </div>
                        </td>
                      </motion.tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {!loading && reports.length === 0 && (
              <div className="flex flex-col items-center gap-3 py-10">
                <div className="p-4 rounded-full bg-surface-3">
                  <FileBarChart className="w-10 h-10 text-text-tertiary" />
                </div>
                <p className="text-sm text-text-secondary font-medium">No reports generated yet</p>
                <p className="text-xs text-text-tertiary">Generate your first report to see it here</p>
                <Button
                  variant="primary"
                  size="sm"
                  icon={<Plus className="w-3.5 h-3.5" />}
                  onClick={() => setActiveTab('generate')}
                >
                  Generate Report
                </Button>
              </div>
            )}
          </Card>
        </motion.div>
      )}

      {viewLoading && (
        <motion.div variants={item}>
          <Card padding="lg">
            <div className="flex items-center gap-3 py-4">
              <Loader2 className="w-5 h-5 animate-spin text-accent" />
              <span className="text-sm text-text-secondary">Loading report content...</span>
            </div>
          </Card>
        </motion.div>
      )}

      {viewingReport && !viewLoading && (
        <motion.div variants={item}>
          <Card padding="lg">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-text flex items-center gap-2">
                <Eye className="w-4 h-4 text-accent" />
                Report {viewingReport.id.slice(0, 8)}
              </h2>
              <Button
                variant="ghost"
                size="sm"
                icon={<X className="w-3.5 h-3.5" />}
                onClick={() => setViewingReport(null)}
              >
                Close
              </Button>
            </div>
            {viewingReport.format === 'json' ? (
              <pre className="p-4 rounded-xl bg-surface-2 text-xs text-text-secondary overflow-auto max-h-96 leading-relaxed">
                {(() => {
                  try { return JSON.stringify(JSON.parse(viewingReport.content), null, 2) }
                  catch { return viewingReport.content }
                })()}
              </pre>
            ) : (
              <div className="rounded-xl overflow-hidden border border-border max-h-96">
                <iframe
                  srcDoc={viewingReport.content}
                  title="Report"
                  className="w-full h-96 bg-white"
                  sandbox="allow-same-origin"
                />
              </div>
            )}
          </Card>
        </motion.div>
      )}
    </motion.div>
  )
}
