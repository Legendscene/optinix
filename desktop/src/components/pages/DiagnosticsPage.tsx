import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Stethoscope, Activity, AlertTriangle, AlertCircle, CheckCircle2, Bug, HardDrive, Gauge, Wrench, Play, ChevronDown, ChevronUp, ScanLine } from 'lucide-react'
import { Card } from '../ui/Card'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { Skeleton } from '../ui/Skeleton'
import { PageHero } from '../ui/PageHero'
import { api } from '../../lib/api'
import type { SystemInfo, DiagnosticsSummary, DiagnosticsResult } from '../../types'

const diagnosticCategories = [
  { key: 'event_viewer', icon: <Activity size={20} />, name: 'Event Viewer Analyzer' },
  { key: 'reliability', icon: <Stethoscope size={20} />, name: 'Reliability Monitor' },
  { key: 'crash_dumps', icon: <Bug size={20} />, name: 'Crash Dump Analyzer' },
  { key: 'bsod', icon: <AlertCircle size={20} />, name: 'BSOD Analyzer' },
  { key: 'driver_conflicts', icon: <Wrench size={20} />, name: 'Driver Conflict Detector' },
  { key: 'memory_leaks', icon: <HardDrive size={20} />, name: 'Memory Leak Detector' },
  { key: 'startup_delays', icon: <Gauge size={20} />, name: 'Startup Delay Analyzer' },
  { key: 'windows_errors', icon: <AlertTriangle size={20} />, name: 'Windows Error Analyzer' },
]

const containerVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.05 } },
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { type: 'spring' as const, stiffness: 260, damping: 24 } },
}

function statusBadgeVariant(status: string): 'success' | 'warning' | 'danger' {
  switch (status) {
    case 'good': return 'success'
    case 'warning': return 'warning'
    case 'critical': return 'danger'
    default: return 'warning'
  }
}

function statusDotColor(status: string): string {
  switch (status) {
    case 'good': return 'var(--color-green)'
    case 'warning': return 'var(--color-yellow)'
    case 'critical': return 'var(--color-red)'
    default: return 'var(--color-text-tertiary)'
  }
}

function statusLabel(status: string): string {
  switch (status) {
    case 'good': return 'Good'
    case 'warning': return 'Warning'
    case 'critical': return 'Critical'
    default: return 'Unknown'
  }
}

export function DiagnosticsPage(_props: { systemInfo: SystemInfo | null }) {
  const [summary, setSummary] = useState<DiagnosticsSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState<string | null>(null)
  const [runningAll, setRunningAll] = useState(false)
  const [results, setResults] = useState<Record<string, DiagnosticsResult>>({})
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})

  const fetchSummary = () => {
    api.diagnosticsSummary()
      .then(d => { setSummary(d); setResults(d.results ?? {}); setLoading(false) })
      .catch(() => setLoading(false))
  }

  useEffect(() => {
    fetchSummary()
  }, [])

  const runCategory = async (key: string) => {
    setRunning(key)
    try {
      const r = await api.diagnosticsCategory(key)
      setResults(prev => ({ ...prev, [key]: r }))
    } catch {
      setResults(prev => ({
        ...prev,
        [key]: { status: 'critical', summary: 'Diagnostic failed to run', details: [{ source: key, message: 'Request failed' }], issues_count: 1 },
      }))
    }
    setRunning(null)
  }

  const runAll = async () => {
    setRunningAll(true)
    try {
      const all = await api.diagnosticsAll()
      setResults(prev => ({ ...prev, ...all }))
    } catch {
      for (const cat of diagnosticCategories) {
        if (!results[cat.key]) {
          setResults(prev => ({
            ...prev,
            [cat.key]: { status: 'critical', summary: 'Diagnostic failed to run', details: [{ source: cat.key, message: 'Request failed' }], issues_count: 1 },
          }))
        }
      }
    }
    setRunningAll(false)
  }

  const toggleExpand = (key: string) => {
    setExpanded(prev => ({ ...prev, [key]: !prev[key] }))
  }

  if (loading && !summary) {
    return (
      <div className="page space-y-6">
        <div className="flex items-center justify-between">
          <div><Skeleton className="h-8 w-56 mb-1" /><Skeleton className="h-4 w-64" /></div>
          <Skeleton className="h-9 w-24 rounded-lg" />
        </div>
        <Skeleton className="h-16 w-full rounded-xl" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-44 rounded-xl" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <motion.div variants={containerVariants} initial="hidden" animate="show" className="page space-y-6">
      {/* The four counters that used to sit in their own strip are the band's
          stat grid now — same numbers, one less surface to scan. */}
      <motion.div variants={itemVariants}>
        <PageHero
          eyebrow="Diagnostics"
          title="Windows Diagnostics"
          subtitle="Eight independent analyzers over the event log, reliability history, crash dumps and driver state. Each one reports only what it found."
          icon={<Stethoscope size={19} />}
          stats={[
            { label: 'Issues', value: String(summary?.total_issues ?? 0), tone: (summary?.total_issues ?? 0) > 0 ? 'warn' : 'good' },
            { label: 'Critical', value: String(summary?.critical ?? 0), tone: (summary?.critical ?? 0) > 0 ? 'bad' : 'default' },
            { label: 'Warnings', value: String(summary?.warnings ?? 0), tone: (summary?.warnings ?? 0) > 0 ? 'warn' : 'default' },
            { label: 'Good', value: String(summary?.good ?? 0), tone: 'good' },
          ]}
          actions={
            <Button
              variant="primary"
              size="md"
              icon={runningAll ? <ScanLine size={16} className="animate-spin" /> : <Play size={16} />}
              onClick={runAll}
              loading={runningAll}
            >
              Run all
            </Button>
          }
        />
      </motion.div>

      <motion.div variants={itemVariants} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {diagnosticCategories.map(({ key, icon, name }) => {
          const result = results[key]
          const isRunning = running === key
          const isExpanded = expanded[key] ?? false
          const status = result?.status ?? 'good'
          const details = result?.details ?? []

          return (
            <motion.div key={key} variants={itemVariants}>
              <Card padding="md" className="h-full flex flex-col">
                <div className="flex items-start gap-3 mb-3">
                  <span className="icon-chip text-accent h-9 w-9 shrink-0">
                    {icon}
                  </span>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-semibold text-text truncate">{name}</h3>
                    <div className="flex items-center gap-1.5 mt-1">
                      <span
                        className="w-2 h-2 rounded-full"
                        style={{ backgroundColor: statusDotColor(status) }}
                      />
                      <Badge variant={statusBadgeVariant(status)}>{statusLabel(status)}</Badge>
                    </div>
                  </div>
                </div>

                {result && (
                  <p className="text-xs text-text-secondary mb-3 leading-relaxed flex-1">{result.summary}</p>
                )}

                <div className="flex items-center gap-2 mt-auto">
                  <Button
                    size="sm"
                    variant={status === 'critical' ? 'danger' : 'secondary'}
                    icon={isRunning ? <ScanLine size={14} className="animate-spin" /> : <Play size={14} />}
                    onClick={() => runCategory(key)}
                    loading={isRunning}
                    className="flex-1"
                  >
                    {isRunning ? 'Running...' : 'Run'}
                  </Button>
                  {details.length > 0 && (
                    <Button
                      size="sm"
                      variant="ghost"
                      icon={isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                      onClick={() => toggleExpand(key)}
                    >
                      {String(details.length)}
                    </Button>
                  )}
                </div>

                {details.length > 0 && isExpanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    className="mt-3 pt-3 border-t border-border space-y-1.5"
                  >
                    {details.map((d, i) => (
                      <div key={i} className="flex items-start gap-2 text-[11px] p-1.5 rounded-lg bg-surface-2/40">
                        {d.severity === 'critical' ? (
                          <AlertCircle size={10} className="text-red shrink-0 mt-0.5" />
                        ) : d.severity === 'warning' ? (
                          <AlertTriangle size={10} className="text-yellow shrink-0 mt-0.5" />
                        ) : (
                          <CheckCircle2 size={10} className="text-green shrink-0 mt-0.5" />
                        )}
                        <div>
                          <span className="text-text-secondary">{d.source}: </span>
                          <span className="text-text-tertiary">{d.message}</span>
                        </div>
                      </div>
                    ))}
                  </motion.div>
                )}
              </Card>
            </motion.div>
          )
        })}
      </motion.div>
    </motion.div>
  )
}
