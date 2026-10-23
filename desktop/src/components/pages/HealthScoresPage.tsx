import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { HeartPulse, Monitor, Gamepad2, Code, Shield, HardDrive, Battery, Info, ChevronDown, ChevronUp } from 'lucide-react'
import { Card } from '../ui/Card'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { ProgressBar } from '../ui/ProgressBar'
import { Skeleton } from '../ui/Skeleton'
import { PageHero } from '../ui/PageHero'
import { api } from '../../lib/api'
import type { SystemInfo, HealthScoresResponse, HealthScoreEntry } from '../../types'

const scoreCategories: { key: keyof HealthScoresResponse; icon: React.ReactNode; label: string }[] = [
  { key: 'pc_health', icon: <Monitor size={20} />, label: 'PC Health' },
  { key: 'windows_health', icon: <HeartPulse size={20} />, label: 'Windows Health' },
  { key: 'gaming', icon: <Gamepad2 size={20} />, label: 'Gaming' },
  { key: 'developer', icon: <Code size={20} />, label: 'Developer' },
  { key: 'security', icon: <Shield size={20} />, label: 'Security' },
  { key: 'storage', icon: <HardDrive size={20} />, label: 'Storage' },
  { key: 'battery', icon: <Battery size={20} />, label: 'Battery' },
]

const containerVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.06 } },
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { type: 'spring' as const, stiffness: 260, damping: 24 } },
}

function getScoreColor(score: number): string {
  if (score >= 80) return 'var(--color-green)'
  if (score >= 60) return 'var(--color-yellow)'
  if (score >= 40) return 'var(--color-yellow)'
  return 'var(--color-red)'
}

function getScoreLabel(score: number): string {
  if (score >= 80) return 'Excellent'
  if (score >= 60) return 'Good'
  if (score >= 40) return 'Fair'
  return 'Poor'
}

function getBadgeVariant(score: number): 'success' | 'warning' | 'danger' {
  if (score >= 60) return 'success'
  if (score >= 40) return 'warning'
  return 'danger'
}

export function HealthScoresPage(_props: { systemInfo: SystemInfo | null }) {
  const [scores, setScores] = useState<HealthScoresResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})

  useEffect(() => {
    api.healthScores()
      .then(d => { setScores(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  const overall = scores?.overall ?? 0

  const toggleExpand = (key: string) => {
    setExpanded(prev => ({ ...prev, [key]: !prev[key] }))
  }

  if (loading || !scores) {
    return (
      <div className="page space-y-6">
        <Skeleton className="h-8 w-56 mb-1" />
        <Skeleton className="h-4 w-80 mb-6" />
        <div className="flex justify-center mb-8">
          <Skeleton variant="circular" className="h-44 w-44" />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {Array.from({ length: 7 }).map((_, i) => (
            <Skeleton key={i} className="h-40 rounded-xl" />
          ))}
        </div>
      </div>
    )
  }

  /* Strongest and weakest dimensions, from the scores the backend returned.
     Categories with no score (a desktop has no battery) are skipped rather
     than counted as zero. */
  const ranked = scoreCategories
    .map((c) => ({ label: c.label, score: (scores[c.key] as HealthScoreEntry | undefined)?.score }))
    .filter((c): c is { label: string; score: number } => typeof c.score === 'number')
    .sort((a, b) => a.score - b.score)
  const weakest = ranked[0]
  const strongest = ranked[ranked.length - 1]

  return (
    <motion.div variants={containerVariants} initial="hidden" animate="show" className="page space-y-6">
      {/* Overall score moved into the band: it is the page's headline number,
          so it belongs next to the title instead of floating on its own. */}
      <motion.div variants={itemVariants}>
        <PageHero
          eyebrow="Diagnostics"
          title="System Intelligence"
          subtitle="Seven independent health dimensions, each scored from measured system state rather than a generic checklist."
          icon={<HeartPulse size={19} />}
          stats={[
            { label: 'Overall', value: `${overall}`, hint: `${getScoreLabel(overall)} · /100`, tone: overall >= 80 ? 'good' : overall >= 60 ? 'default' : overall >= 40 ? 'warn' : 'bad' },
            { label: 'Weakest', value: weakest ? `${weakest.score}` : '—', hint: weakest?.label ?? 'not scored', tone: weakest && weakest.score < 60 ? 'warn' : 'default' },
            { label: 'Strongest', value: strongest ? `${strongest.score}` : '—', hint: strongest?.label ?? 'not scored', tone: 'good' },
            { label: 'Scored', value: `${ranked.length}`, hint: `of ${scoreCategories.length} dimensions` },
          ]}
        />
      </motion.div>

      <motion.div variants={itemVariants} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {scoreCategories.map(({ key, icon, label }) => {
          const entry = scores[key] as HealthScoreEntry | undefined
          const score = entry?.score ?? 0
          const color = getScoreColor(score)
          const isExpanded = expanded[key] ?? false
          const details = entry?.details as Record<string, unknown> | undefined
          const miniCircumference = 2 * Math.PI * 22

          return (
            <motion.div key={key} variants={itemVariants}>
              <Card padding="md" className="h-full">
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-2 rounded-lg" style={{ backgroundColor: `${color}20`, color }}>
                    {icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-semibold text-text truncate">{label}</h3>
                    <Badge variant={getBadgeVariant(score)}>
                      {score} — {getScoreLabel(score)}
                    </Badge>
                  </div>
                  <div className="relative shrink-0" style={{ width: 52, height: 52 }}>
                    <svg width="52" height="52" viewBox="0 0 52 52">
                      <circle cx="26" cy="26" r="22" fill="none" stroke="currentColor" strokeWidth="4" className="text-surface-3" />
                      <motion.circle
                        cx="26" cy="26" r="22"
                        fill="none"
                        stroke={color}
                        strokeWidth="4"
                        strokeLinecap="round"
                        strokeDasharray={miniCircumference}
                        initial={{ strokeDashoffset: miniCircumference }}
                        animate={{ strokeDashoffset: miniCircumference * (1 - score / 100) }}
                        transition={{ duration: 1.2, ease: 'easeOut' }}
                        transform="rotate(-90 26 26)"
                      />
                    </svg>
                  </div>
                </div>
                <ProgressBar value={score} color={color} size="sm" />
                {details && Object.keys(details).length > 0 && (
                  <>
                    <Button
                      size="sm"
                      variant="ghost"
                      icon={isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                      onClick={() => toggleExpand(key)}
                      className="mt-2 w-full justify-center"
                    >
                      {isExpanded ? 'Hide Details' : 'Show Details'}
                    </Button>
                    {isExpanded && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        className="mt-2 pt-2 border-t border-border space-y-1.5"
                      >
                        {Object.entries(details).map(([dk, dv]) => (
                          <div key={dk} className="flex items-start gap-2 text-[11px]">
                            <Info size={10} className="text-text-tertiary shrink-0 mt-0.5" />
                            <span className="text-text-secondary capitalize">{dk.replace(/_/g, ' ')}: </span>
                            <span className="text-text-tertiary">{String(dv)}</span>
                          </div>
                        ))}
                      </motion.div>
                    )}
                  </>
                )}
              </Card>
            </motion.div>
          )
        })}
      </motion.div>
    </motion.div>
  )
}
