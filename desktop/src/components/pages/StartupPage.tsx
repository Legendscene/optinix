import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { Play, Power, PowerOff, Clock, CheckCircle2, AlertTriangle } from 'lucide-react'
import { Card } from '../ui/Card'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { ProgressBar } from '../ui/ProgressBar'
import { Skeleton } from '../ui/Skeleton'
import { cn } from '../../lib/utils'
import { api } from '../../lib/api'
import type { SystemInfo } from '../../types'

interface StartupAppWithState {
  name: string
  desc: string
  enabled: boolean
}

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.05 } },
}

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
}

const BOOT_IMPACT_MULTIPLIER = 0.3

export function StartupPage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const [apps, setApps] = useState<StartupAppWithState[]>([])
  const [loading, setLoading] = useState(true)
  const [toggling, setToggling] = useState<string | null>(null)
  const [disablingAll, setDisablingAll] = useState(false)
  const [result, setResult] = useState<{ message: string; success: boolean } | null>(null)

  const loadApps = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.startup()
      setApps(res.apps.map(a => ({ ...a, enabled: 'enabled' in a ? (a as any).enabled : false })))
      setResult(null)
    } catch {
      setApps([])
      setResult({ message: 'Failed to load startup apps', success: false })
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadApps() }, [loadApps])

  async function handleToggle(appName: string, enabled: boolean) {
    setToggling(appName)
    try {
      await api.toggleStartup(appName, enabled)
      setApps(prev => prev.map(a => a.name === appName ? { ...a, enabled } : a))
    } catch {
      setResult({ message: `Failed to toggle ${appName}`, success: false })
    } finally {
      setToggling(null)
    }
  }

  async function handleDisableAll() {
    setDisablingAll(true)
    setResult(null)
    try {
      for (const app of apps) {
        if (app.enabled) {
          await api.toggleStartup(app.name, false)
        }
      }
      setApps(prev => prev.map(a => ({ ...a, enabled: false })))
      setResult({ message: 'All startup apps disabled', success: true })
    } catch {
      setResult({ message: 'Failed to disable all apps', success: false })
    } finally {
      setDisablingAll(false)
    }
  }

  const enabledCount = apps.filter(a => a.enabled).length
  const bootImpact = Math.min(enabledCount * BOOT_IMPACT_MULTIPLIER, 100)

  if (!systemInfo) {
    return (
      <div className="space-y-6">
        <div><Skeleton className="h-8 w-48 mb-1" /><Skeleton className="h-4 w-64" /></div>
        <Skeleton className="h-32 rounded-xl" />
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-16 rounded-xl" />)}
        </div>
      </div>
    )
  }

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-6">
      <motion.div variants={item} className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Play className="w-6 h-6 text-accent" />
            <h1 className="text-2xl font-bold tracking-tight text-text">Startup Manager</h1>
          </div>
          <p className="text-sm text-text-secondary ml-9">Control which apps run at boot</p>
        </div>
        <Button
          variant="danger"
          size="sm"
          icon={<PowerOff className="w-4 h-4" />}
          loading={disablingAll}
          disabled={enabledCount === 0}
          onClick={handleDisableAll}
        >
          Disable All
        </Button>
      </motion.div>

      <motion.div variants={item}>
        <Card padding="lg">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-accent" />
              <h2 className="text-sm font-semibold text-text">Boot Time Impact</h2>
            </div>
            <Badge variant={bootImpact > 60 ? 'danger' : bootImpact > 30 ? 'warning' : 'success'}>
              {enabledCount} enabled
            </Badge>
          </div>
          <ProgressBar value={bootImpact} label="Impact" />
          <p className="text-xs text-text-tertiary mt-2">
            {bootImpact > 60
              ? 'High boot impact — consider disabling unnecessary startup items'
              : bootImpact > 30
                ? 'Moderate boot impact — review startup apps'
                : 'Low boot impact — system should boot quickly'}
          </p>
        </Card>
      </motion.div>

      <motion.div variants={item}>
        <Card padding="lg">
          <div className="flex items-center gap-2 mb-4">
            <Power className="w-5 h-5 text-accent" />
            <h2 className="text-sm font-semibold text-text">Startup Applications</h2>
          </div>
          {loading ? (
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-16 rounded-xl" />)}
            </div>
          ) : apps.length === 0 ? (
            <p className="text-xs text-text-tertiary py-6 text-center">No startup apps detected</p>
          ) : (
            <div className="divide-y divide-border">
              {apps.map(app => (
                <div key={app.name} className="flex items-center justify-between py-3 first:pt-0 last:pb-0">
                  <div className="flex-1 min-w-0 mr-4">
                    <p className="text-sm font-medium text-text truncate">{app.name}</p>
                    {app.desc && <p className="text-xs text-text-tertiary truncate mt-0.5">{app.desc}</p>}
                  </div>
                  <button
                    disabled={toggling === app.name}
                    onClick={() => handleToggle(app.name, !app.enabled)}
                    className={cn(
                      'relative inline-flex h-6 w-11 shrink-0 rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none',
                      app.enabled ? 'bg-accent' : 'bg-surface-4',
                      toggling === app.name && 'opacity-50 cursor-not-allowed'
                    )}
                  >
                    <span
                      className={cn(
                        'pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow transition duration-200 ease-in-out',
                        app.enabled ? 'translate-x-5' : 'translate-x-0'
                      )}
                    />
                  </button>
                </div>
              ))}
            </div>
          )}
        </Card>
      </motion.div>
      {result && (
        <motion.div variants={item} className={cn('p-4 rounded-xl border', result.success ? 'bg-green-dim/10 border-green' : 'bg-red-dim/10 border-red')}>
          <div className="flex items-center gap-3">
            {result.success ? <CheckCircle2 className="w-5 h-5 text-green" /> : <AlertTriangle className="w-5 h-5 text-red" />}
            <span className="text-sm text-text">{result.message}</span>
          </div>
        </motion.div>
      )}
    </motion.div>
  )
}
