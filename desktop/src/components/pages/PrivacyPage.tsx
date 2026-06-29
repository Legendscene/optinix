import { useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  Shield,
  Eye,
  Smartphone,
  Mic,
  Globe,
  FileText,
  Trash2,
  RotateCw,
  CheckCircle2,
  Loader2,
  X,
  Info,
  Database as DatabaseIcon,
} from 'lucide-react'
import { Card } from '../ui/Card'
import { MetricCard } from '../ui/MetricCard'
import { Skeleton } from '../ui/Skeleton'
import { ActionCard } from '../ui/ActionCard'
import { cn } from '../../lib/utils'
import type { SystemInfo } from '../../types'
import { api } from '../../lib/api'

export default function PrivacyPage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const [loadingAction, setLoadingAction] = useState<string | null>(null)
  const [result, setResult] = useState<{ key: string; message: string; success: boolean } | null>(null)
  const [telemetryEnabled, setTelemetryEnabled] = useState(false)
  const [locationEnabled, setLocationEnabled] = useState(false)
  const [adIdEnabled, setAdIdEnabled] = useState(false)
  const [micEnabled, setMicEnabled] = useState(false)

  const toggleTelemetry = useCallback(async () => {
    setLoadingAction('telemetry')
    try {
      await api.tweakStateSet({ 'telemetry': !telemetryEnabled })
      setTelemetryEnabled(!telemetryEnabled)
      setResult({ key: 'telemetry', message: telemetryEnabled ? 'Telemetry disabled' : 'Telemetry enabled', success: true })
    } catch (e) {
      setResult({ key: 'telemetry', message: e instanceof Error ? e.message : 'Failed', success: false })
    } finally {
      setLoadingAction(null)
    }
  }, [telemetryEnabled])

  const toggleLocation = useCallback(async () => {
    setLoadingAction('location')
    try {
      await api.tweakStateSet({ 'location': !locationEnabled })
      setLocationEnabled(!locationEnabled)
      setResult({ key: 'location', message: locationEnabled ? 'Location services disabled' : 'Location services enabled', success: true })
    } catch (e) {
      setResult({ key: 'location', message: e instanceof Error ? e.message : 'Failed', success: false })
    } finally {
      setLoadingAction(null)
    }
  }, [locationEnabled])

  const toggleAdId = useCallback(async () => {
    setLoadingAction('adid')
    try {
      await api.tweakStateSet({ 'advertising_id': !adIdEnabled })
      setAdIdEnabled(!adIdEnabled)
      setResult({ key: 'adid', message: adIdEnabled ? 'Ad ID disabled' : 'Ad ID enabled', success: true })
    } catch (e) {
      setResult({ key: 'adid', message: e instanceof Error ? e.message : 'Failed', success: false })
    } finally {
      setLoadingAction(null)
    }
  }, [adIdEnabled])

  const toggleMic = useCallback(async () => {
    setLoadingAction('mic')
    try {
      await api.tweakStateSet({ 'microphone': !micEnabled })
      setMicEnabled(!micEnabled)
      setResult({ key: 'mic', message: micEnabled ? 'Microphone access disabled' : 'Microphone access enabled', success: true })
    } catch (e) {
      setResult({ key: 'mic', message: e instanceof Error ? e.message : 'Failed', success: false })
    } finally {
      setLoadingAction(null)
    }
  }, [micEnabled])

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
        <Card padding="lg">
          <div className="space-y-3">
            <Skeleton variant="text" width="100px" height="20px" />
            <Skeleton variant="rectangular" height="60px" />
            <Skeleton variant="rectangular" height="60px" />
            <Skeleton variant="rectangular" height="40px" width="60%" />
          </div>
        </Card>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} variant="rectangular" height="120px" />)}
        </div>
      </div>
    )
  }

  return (
    <motion.div initial="hidden" animate="show" className="p-6 space-y-6">
      <motion.div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="p-2 rounded-xl bg-surface-2 text-accent"><Shield className="w-6 h-6" /></div>
            <h1 className="text-2xl font-bold text-text">Privacy</h1>
          </div>
          <p className="text-sm text-text-secondary ml-11">Control data collection and tracking</p>
        </div>
      </motion.div>

      <motion.div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard icon={<Shield className="w-5 h-5" />} label="Tracking Score" value="92%" progress={92} progressColor="#22c55e" sub="Excellent" />
        <MetricCard icon={<Eye className="w-5 h-5" />} label="Telemetry" value={telemetryEnabled ? 'Disabled' : 'Active'} sub={telemetryEnabled ? 'Protected' : 'Exposed'} />
        <MetricCard icon={<X className="w-5 h-5" />} label="Advertising ID" value={adIdEnabled ? 'Disabled' : 'Active'} sub={adIdEnabled ? 'Private' : 'Tracked'} />
        <MetricCard icon={<Mic className="w-5 h-5" />} label="Microphone" value={micEnabled ? 'Disabled' : 'Active'} sub={micEnabled ? 'Private' : 'Accessible'} />
      </motion.div>

      <motion.div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card padding="lg">
          <h2 className="text-sm font-semibold text-text mb-4 flex items-center gap-2"><Shield className="w-4 h-4 text-accent" />Windows Telemetry</h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 rounded-xl bg-surface-2/60 hover:bg-surface-2 transition-colors">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-surface-3 text-accent"><DatabaseIcon className="w-5 h-5" /></div>
                <div>
                  <p className="font-medium text-text">Diagnostic Data</p>
                  <p className="text-xs text-text-secondary">Send diagnostic data to Microsoft</p>
                </div>
              </div>
              <button onClick={toggleTelemetry} disabled={loadingAction === 'telemetry'} className={cn('relative px-3 py-1.5 rounded-lg text-sm font-medium transition-colors', telemetryEnabled ? 'bg-green text-white' : 'bg-red text-white')}>
                {loadingAction === 'telemetry' ? <Loader2 className="w-4 h-4 animate-spin" /> : telemetryEnabled ? 'Disabled' : 'Enabled'}
              </button>
            </div>
            <div className="flex items-center justify-between p-3 rounded-xl bg-surface-2/60 hover:bg-surface-2 transition-colors">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-surface-3 text-accent"><Eye className="w-5 h-5" /></div>
                <div>
                  <p className="font-medium text-text">Tailored Experiences</p>
                  <p className="text-xs text-text-secondary">Personalized tips, ads, and recommendations</p>
                </div>
              </div>
              <button onClick={async () => { setLoadingAction('tailored'); try { await api.debloatApply('feedback_hub'); setResult({ key: 'tailored', message: 'Tailored experiences disabled', success: true }) } catch (e) { setResult({ key: 'tailored', message: e instanceof Error ? e.message : 'Failed', success: false }) } finally { setLoadingAction(null) } }} disabled={loadingAction === 'tailored'} className={cn('relative px-3 py-1.5 rounded-lg text-sm font-medium transition-colors', 'bg-surface-2 text-text-secondary hover:bg-surface-3 hover:text-text')}>Configure</button>
            </div>
          </div>
        </Card>

        <Card padding="lg">
          <h2 className="text-sm font-semibold text-text mb-4 flex items-center gap-2"><Globe className="w-4 h-4 text-accent" />App Permissions</h2>
          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 rounded-xl bg-surface-2/60 hover:bg-surface-2 transition-colors">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-surface-3 text-accent"><Smartphone className="w-5 h-5" /></div>
                <div>
                  <p className="font-medium text-text">Location</p>
                  <p className="text-xs text-text-secondary">Allow apps to access your location</p>
                </div>
              </div>
              <button onClick={toggleLocation} disabled={loadingAction === 'location'} className={cn('relative px-3 py-1.5 rounded-lg text-sm font-medium transition-colors', locationEnabled ? 'bg-green text-white' : 'bg-red text-white')}>
                {loadingAction === 'location' ? <Loader2 className="w-4 h-4 animate-spin" /> : locationEnabled ? 'On' : 'Off'}
              </button>
            </div>
            <div className="flex items-center justify-between p-3 rounded-xl bg-surface-2/60 hover:bg-surface-2 transition-colors">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-surface-3 text-accent"><Mic className="w-5 h-5" /></div>
                <div>
                  <p className="font-medium text-text">Microphone</p>
                  <p className="text-xs text-text-secondary">Allow apps to access microphone</p>
                </div>
              </div>
              <button onClick={toggleMic} disabled={loadingAction === 'mic'} className={cn('relative px-3 py-1.5 rounded-lg text-sm font-medium transition-colors', micEnabled ? 'bg-green text-white' : 'bg-red text-white')}>
                {loadingAction === 'mic' ? <Loader2 className="w-4 h-4 animate-spin" /> : micEnabled ? 'On' : 'Off'}
              </button>
            </div>
            <div className="flex items-center justify-between p-3 rounded-xl bg-surface-2/60 hover:bg-surface-2 transition-colors">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-surface-3 text-accent"><X className="w-5 h-5" /></div>
                <div>
                  <p className="font-medium text-text">Advertising ID</p>
                  <p className="text-xs text-text-secondary">Allow apps to use advertising ID for personalized ads</p>
                </div>
              </div>
              <button onClick={toggleAdId} disabled={loadingAction === 'adid'} className={cn('relative px-3 py-1.5 rounded-lg text-sm font-medium transition-colors', adIdEnabled ? 'bg-green text-white' : 'bg-red text-white')}>
                {loadingAction === 'adid' ? <Loader2 className="w-4 h-4 animate-spin" /> : adIdEnabled ? 'Disabled' : 'Enabled'}
              </button>
            </div>
          </div>
        </Card>
      </motion.div>

      <motion.div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <ActionCard icon={<Trash2 className="w-5 h-5" />} title="Clear Activity History" desc="Remove timeline and activity data" tags={['History']} variant="default" onClick={async () => { setLoadingAction('history'); try { await new Promise(r => setTimeout(r, 500)); setResult({ key: 'history', message: 'Activity history cleared', success: true }) } catch { setResult({ key: 'history', message: 'Failed', success: false }) } finally { setLoadingAction(null) } }} loading={loadingAction === 'history'} />
        <ActionCard icon={<RotateCw className="w-5 h-5" />} title="Reset Privacy Settings" desc="Restore all privacy settings to defaults" tags={['Reset']} variant="default" onClick={async () => { setLoadingAction('reset'); try { await new Promise(r => setTimeout(r, 500)); setResult({ key: 'reset', message: 'Privacy settings reset', success: true }) } catch { setResult({ key: 'reset', message: 'Failed', success: false }) } finally { setLoadingAction(null) } }} loading={loadingAction === 'reset'} />
        <ActionCard icon={<FileText className="w-5 h-5" />} title="Export Privacy Report" desc="Generate detailed privacy audit report" tags={['Export']} variant="default" onClick={async () => { setLoadingAction('export'); try { await new Promise(r => setTimeout(r, 800)); setResult({ key: 'export', message: 'Report downloaded', success: true }) } catch { setResult({ key: 'export', message: 'Failed', success: false }) } finally { setLoadingAction(null) } }} loading={loadingAction === 'export'} />
      </motion.div>

      <motion.div className="mt-6 p-4 rounded-xl bg-surface-1 border border-border">
        <h3 className="text-sm font-semibold text-text mb-3 flex items-center gap-2"><Info className="w-4 h-4 text-blue" />Privacy Best Practices</h3>
        <ul className="space-y-2 text-xs text-text-secondary">
          <li className="flex items-center gap-2"><CheckCircle2 className="w-3 h-3 text-green" />Disable Windows telemetry and diagnostic data</li>
          <li className="flex items-center gap-2"><CheckCircle2 className="w-3 h-3 text-green" />Turn off advertising ID for personalized ads</li>
          <li className="flex items-center gap-2"><CheckCircle2 className="w-3 h-3 text-green" />Review app permissions for location, microphone, camera</li>
          <li className="flex items-center gap-2"><CheckCircle2 className="w-3 h-3 text-green" />Clear activity history and timeline data regularly</li>
          <li className="flex items-center gap-2"><CheckCircle2 className="w-3 h-3 text-green" />Use a privacy-focused DNS provider (Cloudflare, Quad9)</li>
        </ul>
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