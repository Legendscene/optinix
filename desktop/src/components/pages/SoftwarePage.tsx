import { useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  Package,
  Search,
  ExternalLink,
  AlertTriangle,
  CheckCircle,
  AppWindow} from 'lucide-react'
import { Card } from '../ui/Card'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { Skeleton } from '../ui/Skeleton'
import { MetricCard } from '../ui/MetricCard'

import { api } from '../../lib/api'

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.05 } }}

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 }}

interface SoftwareEntry {
  name: string
  current_version: string
  latest_version: string
  update_available: boolean
  download_url: string
  category: string
}

export function SoftwarePage() {
  const [loading, setLoading] = useState(false)
  const [software, setSoftware] = useState<SoftwareEntry[]>([])
  const [total, setTotal] = useState(0)
  const [updatesAvailable, setUpdatesAvailable] = useState(0)
  const [upToDate, setUpToDate] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const check = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.softwareCheckUpdates()
      setSoftware(res.software)
      setTotal(res.total)
      setUpdatesAvailable(res.updates_available)
      setUpToDate(res.up_to_date)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to check for updates')
      setSoftware([])
    } finally {
      setLoading(false)
    }
  }, [])

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-6">
      <motion.div variants={item}>
        <div className="flex items-center gap-3 mb-1">
          <Package className="w-6 h-6 text-accent" />
          <h1 className="text-2xl font-bold tracking-tight text-text">Software Updates</h1>
        </div>
        <p className="text-sm text-text-secondary ml-9">Check for outdated software and update to latest versions</p>
      </motion.div>

      <motion.div variants={item} className="flex flex-wrap gap-2">
        <Button
          variant="primary"
          size="md"
          icon={<Search className="w-4 h-4" />}
          loading={loading}
          onClick={check}
        >
          Check for Updates
        </Button>
      </motion.div>

      {software.length > 0 && (
        <motion.div variants={item} className="grid grid-cols-3 gap-4">
          <MetricCard icon={<AppWindow className="w-5 h-5" />} label="Total Apps" value={String(total)} />
          <MetricCard icon={<AlertTriangle className="w-5 h-5" />} label="Updates Available" value={String(updatesAvailable)} />
          <MetricCard icon={<CheckCircle className="w-5 h-5" />} label="Up to Date" value={String(upToDate)} />
        </motion.div>
      )}

      {error && (
        <motion.div variants={item} className="p-4 rounded-xl border bg-red-dim border-red/30">
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-red" />
            <p className="text-sm font-medium text-red">{error}</p>
          </div>
        </motion.div>
      )}

      <motion.div variants={item}>
        <Card padding="lg">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Package className="w-5 h-5 text-accent" />
              <h2 className="text-sm font-semibold text-text">Installed Software</h2>
              {software.length > 0 && <Badge>{software.length} apps</Badge>}
            </div>
          </div>
          {loading ? (
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-14 rounded-xl" />)}
            </div>
          ) : software.length === 0 && !error ? (
            <p className="text-xs text-text-tertiary py-6 text-center">Click "Check for Updates" to scan installed software.</p>
          ) : (
            <div className="divide-y divide-border max-h-[500px] overflow-y-auto">
              {software.map((s, i) => (
                <div key={`${s.name}-${i}`} className="flex items-center justify-between py-3 first:pt-0 last:pb-0 gap-4">
                  <div className="flex items-center gap-3 min-w-0 flex-1">
                    <div className="p-2 rounded-lg bg-surface-2 text-text-secondary shrink-0">
                      <AppWindow className="w-4 h-4" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-text truncate">{s.name}</p>
                      <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                        <span className="text-[11px] text-text-tertiary">{s.category}</span>
                        <span className="text-[10px] text-text-tertiary">•</span>
                        <span className="text-[11px] text-text-tertiary">v{s.current_version}</span>
                      </div>
                    </div>
                    <span className="text-xs text-text-secondary shrink-0 font-mono">v{s.latest_version}</span>
                  </div>
                  <Badge variant={s.update_available ? 'warning' : 'success'}>
                    {s.update_available ? 'Update Available' : 'Up to Date'}
                  </Badge>
                  {s.update_available && s.download_url && (
                    <a
                      href={s.download_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="shrink-0"
                    >
                      <Button size="sm" variant="secondary" icon={<ExternalLink className="w-3 h-3" />}>
                        Open Download Page
                      </Button>
                    </a>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>
      </motion.div>
    </motion.div>
  )
}
