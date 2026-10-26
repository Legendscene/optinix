import { useCallback, useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  AlertCircle, BrainCircuit, CheckCircle2, Info, Loader2, Sparkles, Zap,
} from 'lucide-react'
import { PageHero } from '../ui/PageHero'
import { Card } from '../ui/Card'
import { MetricCard } from '../ui/MetricCard'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import { Skeleton } from '../ui/Skeleton'
import { api } from '../../lib/api'
import type { SmartDetect, SystemInfo } from '../../types'

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.05 } } }
const item = { hidden: { opacity: 0, y: 16 }, show: { opacity: 1, y: 0 } }

const priorityTone = (priority: string) =>
  priority === 'high' ? 'danger' : priority === 'medium' ? 'warning' : 'accent'

/**
 * Smart Detect, shown as what it actually is: a fixed set of live checks with
 * findings. The previous screen invented a "92% confidence", "147 patterns
 * analyzed", a fabricated deep-analysis grid and a schedule that did not
 * exist. None of that had a backend, so none of it remains. Every value here
 * comes from /api/smart-detect or a real optimization call.
 */
export function AiOptimizerPage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const [detect, setDetect] = useState<SmartDetect | null>(null)
  const [checkedAt, setCheckedAt] = useState<number | null>(null)
  const [checking, setChecking] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [applying, setApplying] = useState(false)

  const runCheck = useCallback(async () => {
    setChecking(true)
    setError(null)
    setNotice(null)
    try {
      const d = await api.smartDetect()
      setDetect(d)
      setCheckedAt(Date.now())
      setNotice(
        d.recommendations.length === 0
          ? 'Check complete — nothing to change on this PC.'
          : `Check complete — ${d.recommendations.length} finding${d.recommendations.length === 1 ? '' : 's'}.`,
      )
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Smart Detect is unavailable.')
    } finally {
      setChecking(false)
    }
  }, [])

  useEffect(() => {
    if (systemInfo) void runCheck()
  }, [systemInfo, runCheck])

  const applySafe = useCallback(async () => {
    setApplying(true)
    setNotice(null)
    try {
      await api.optimizeAll()
      setNotice('Safe optimization pass completed. The Optimizer history lists the exact steps.')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'The optimization pass failed.')
    } finally {
      setApplying(false)
    }
  }, [])

  if (!systemInfo) {
    return (
      <div className="page space-y-6">
        <Skeleton variant="text" width="240px" height="30px" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} variant="rectangular" height="120px" />)}
        </div>
        <Skeleton variant="rectangular" height="260px" />
      </div>
    )
  }

  const findings = detect?.recommendations ?? []

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="page space-y-5">
      <motion.div variants={item}>
        <PageHero
          title="Smart Detect"
          subtitle="Findings from the live checks the backend actually runs — nothing is simulated."
          icon={<BrainCircuit size={19} />}
          actions={
            <Badge variant={error ? 'danger' : 'accent'}>
              {checking ? 'Checking…' : error ? 'Unavailable' : `${findings.length} findings`}
            </Badge>
          }
        />
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <MetricCard
          icon={<Sparkles className="w-5 h-5" />}
          label="Findings"
          value={checking ? '—' : String(findings.length)}
          sub="Actionable checks"
        />
        <MetricCard
          icon={<CheckCircle2 className="w-5 h-5" />}
          label="Last check"
          value={checkedAt ? new Date(checkedAt).toLocaleTimeString() : 'Never'}
          sub="Runs on demand"
        />
        <MetricCard
          icon={<Zap className="w-5 h-5" />}
          label="Source"
          value="Live system"
          sub="No model, no score"
        />
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_320px] gap-4 items-start">
        <Card padding="lg">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-text flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-accent" /> Findings
            </h2>
            <Button
              variant="secondary"
              size="sm"
              icon={<Loader2 className={checking ? 'w-4 h-4 animate-spin' : 'w-4 h-4'} />}
              onClick={runCheck}
              disabled={checking}
            >
              Run check
            </Button>
          </div>

          {checking && !detect ? (
            <div className="space-y-2">
              {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} variant="rectangular" height="58px" />)}
            </div>
          ) : error ? (
            <div className="flex items-start gap-2.5 py-4">
              <AlertCircle size={16} className="text-red shrink-0 mt-0.5" />
              <div>
                <p className="text-[13px] text-text">Smart Detect could not run</p>
                <p className="text-[12px] text-text-secondary mt-0.5">{error}</p>
              </div>
            </div>
          ) : findings.length === 0 ? (
            <div className="flex items-start gap-2.5 py-4">
              <CheckCircle2 size={16} className="text-green shrink-0 mt-0.5" />
              <div>
                <p className="text-[13px] text-text">No findings</p>
                <p className="text-[12px] text-text-secondary mt-0.5">
                  Every check that ran came back clean. Checks that could not run are not counted as clean.
                </p>
              </div>
            </div>
          ) : (
            <ul className="space-y-2">
              {findings.map((rec, i) => (
                <li
                  key={`${rec.type}-${i}`}
                  className="flex items-start gap-3 p-3 rounded-xl bg-surface-2/70 border border-border"
                >
                  <span className="p-1.5 rounded-lg bg-surface-3 text-accent shrink-0 mt-0.5">
                    <Sparkles size={13} />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-[12.5px] text-text leading-snug">{rec.message}</p>
                    <p className="mt-1 text-[10.5px] uppercase tracking-[0.07em] text-text-tertiary">
                      {rec.type}
                    </p>
                  </div>
                  <Badge variant={priorityTone(rec.priority)}>{rec.priority}</Badge>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <div className="space-y-4">
          <Card padding="lg">
            <h2 className="text-sm font-semibold text-text mb-2">What this page is</h2>
            <p className="text-[12px] text-text-secondary leading-relaxed">
              Smart Detect runs a fixed set of live checks and reports what each one found. It does not
              compute a confidence score or a “patterns analyzed” figure, because there is no model
              behind those numbers.
            </p>
            <div className="mt-3 flex items-start gap-2 text-[11px] text-text-tertiary">
              <Info size={13} className="shrink-0 mt-0.5" />
              <span>If a check cannot run, the result says so instead of showing a default value.</span>
            </div>
          </Card>

          <Card padding="lg">
            <h2 className="text-sm font-semibold text-text mb-2">Apply safe optimizations</h2>
            <p className="text-[12px] text-text-secondary leading-relaxed mb-3">
              Runs the backend's full safe preset. Every step is recorded in Optimizer history and can
              be reverted there.
            </p>
            <Button
              variant="secondary"
              size="sm"
              icon={<Zap className={applying ? 'w-4 h-4 animate-spin' : 'w-4 h-4'} />}
              onClick={applySafe}
              disabled={applying}
            >
              {applying ? 'Applying…' : 'Apply safe pass'}
            </Button>
          </Card>

          {notice && (
            <div className="flex items-start gap-2.5 px-3.5 py-2.5 rounded-xl bg-surface-2 border border-border">
              <CheckCircle2 size={14} className="text-green shrink-0 mt-0.5" />
              <span className="text-[11.5px] text-text-secondary leading-snug">{notice}</span>
            </div>
          )}
        </div>
      </motion.div>
    </motion.div>
  )
}
