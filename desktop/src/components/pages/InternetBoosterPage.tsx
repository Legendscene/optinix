import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  Wifi,
  Globe,
  ArrowUpRight,
  ArrowDownRight,
  RefreshCw,
  Cloud,
  Shield,
  Zap,
  Settings,
  AlertCircle,
  Loader2,
  Wifi as WifiIcon,
  Gauge,
  Database,
} from 'lucide-react'
import { Card } from '../ui/Card'
import { MetricCard } from '../ui/MetricCard'
import { ActionCard } from '../ui/ActionCard'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { Skeleton } from '../ui/Skeleton'
import { cn, formatSpeed } from '../../lib/utils'
import type { SystemInfo, NetworkAdapter } from '../../types'
import { api } from '../../lib/api'

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.05 } } }
const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }

interface DNSProvider {
  id: string
  name: string
  icon: React.ReactNode
  primary: string
  secondary: string
}

interface BufferbloatPreset {
  id: string
  name: string
  desc: string
  icon: React.ReactNode
}

const dnsProviders: DNSProvider[] = [
  { id: 'cloudflare', name: 'Cloudflare', icon: <Cloud className="w-5 h-5" />, primary: '1.1.1.1', secondary: '1.0.0.1' },
  { id: 'google', name: 'Google', icon: <Globe className="w-5 h-5" />, primary: '8.8.8.8', secondary: '8.8.4.4' },
  { id: 'opendns', name: 'OpenDNS', icon: <Shield className="w-5 h-5" />, primary: '208.67.222.222', secondary: '208.67.220.220' },
  { id: 'quad9', name: 'Quad9', icon: <AlertCircle className="w-5 h-5" />, primary: '9.9.9.9', secondary: '149.112.112.112' },
  { id: 'adguard', name: 'AdGuard', icon: <Shield className="w-5 h-5" />, primary: '94.140.14.14', secondary: '94.140.15.15' },
]

const bufferbloatPresets: BufferbloatPreset[] = [
  { id: 'low_latency', name: 'Low Latency', desc: 'Best for gaming & real-time apps', icon: <Zap className="w-5 h-5" /> },
  { id: 'high_throughput', name: 'High Throughput', desc: 'Best for downloads & streaming', icon: <ArrowDownRight className="w-5 h-5" /> },
  { id: 'balanced', name: 'Balanced', desc: 'Good all-around performance', icon: <Gauge className="w-5 h-5" /> },
]

export default function InternetBoosterPage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const [adapters, setAdapters] = useState<NetworkAdapter[]>([])
  const [loadingAdapters, setLoadingAdapters] = useState(true)
  const [dnsLoading, setDnsLoading] = useState<string | null>(null)
  const [bufferbloatLoading, setBufferbloatLoading] = useState<string | null>(null)
  const [qosLoading, setQosLoading] = useState(false)
  const [pingLoading, setPingLoading] = useState(false)
  const [pingResult, setPingResult] = useState<string | null>(null)
  const [flushResult, setFlushResult] = useState<string | null>(null)
  const [qosEnabled, setQosEnabled] = useState(false)
  const [loadingAction, setLoadingAction] = useState<string | null>(null)
  const [result, setResult] = useState<{ key: string; message: string; success: boolean } | null>(null)

  useEffect(() => {
    if (!systemInfo) return
    setLoadingAdapters(true)
    fetch('/api/network/adapters')
      .then(r => r.json())
      .then(d => { setAdapters(d.adapters || []); setLoadingAdapters(false) })
      .catch(() => setLoadingAdapters(false))
  }, [systemInfo])

  const setDNS = useCallback(async (provider: DNSProvider) => {
    setDnsLoading(provider.id)
    setResult(null)
    try {
      await api.dns(provider.id)
      setResult({ key: 'dns', message: `DNS set to ${provider.name}`, success: true })
    } catch (e) {
      setResult({ key: 'dns', message: e instanceof Error ? e.message : 'Failed to set DNS', success: false })
    } finally {
      setDnsLoading(null)
    }
  }, [])

  const setBufferbloat = useCallback(async (preset: BufferbloatPreset) => {
    setBufferbloatLoading(preset.id)
    setResult(null)
    try {
      await api.bufferbloat(preset.id)
      setResult({ key: 'bufferbloat', message: `Bufferbloat: ${preset.name}`, success: true })
    } catch (e) {
      setResult({ key: 'bufferbloat', message: e instanceof Error ? e.message : 'Failed', success: false })
    } finally {
      setBufferbloatLoading(null)
    }
  }, [])

  const toggleQoS = useCallback(async () => {
    setQosLoading(true)
    setResult(null)
    try {
      await api.qos(!qosEnabled)
      setQosEnabled(!qosEnabled)
      setResult({ key: 'qos', message: qosEnabled ? 'QoS disabled' : 'QoS enabled', success: true })
    } catch (e) {
      setResult({ key: 'qos', message: e instanceof Error ? e.message : 'Failed', success: false })
    } finally {
      setQosLoading(false)
    }
  }, [qosEnabled])

  const runPing = useCallback(async () => {
    setPingLoading(true)
    setResult(null)
    try {
      const d = await api.ping()
      setPingResult(d.output || 'Ping complete')
      setResult({ key: 'ping', message: 'Ping complete', success: true })
    } catch (e) {
      setPingResult('Ping failed')
      setResult({ key: 'ping', message: e instanceof Error ? e.message : 'Ping failed', success: false })
    } finally {
      setPingLoading(false)
    }
  }, [])

  const runFlushDNS = useCallback(async () => {
    setLoadingAction('flushdns')
    setResult(null)
    try {
      await api.flushDns()
      setFlushResult('DNS cache flushed')
      setResult({ key: 'flushdns', message: 'DNS cache flushed', success: true })
    } catch (e) {
      setResult({ key: 'flushdns', message: e instanceof Error ? e.message : 'Failed', success: false })
    } finally {
      setLoadingAction(null)
    }
  }, [])

  const runOptimizeTCP = useCallback(async () => {
    setLoadingAction('tcp')
    setResult(null)
    try {
      await api.advancedNetwork()
      setResult({ key: 'tcp', message: 'TCP stack optimized', success: true })
    } catch (e) {
      setResult({ key: 'tcp', message: e instanceof Error ? e.message : 'Failed', success: false })
    } finally {
      setLoadingAction(null)
    }
  }, [])

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
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} variant="rectangular" height="100px" />)}
        </div>
        <Skeleton variant="rectangular" height="200px" />
        <Skeleton variant="rectangular" height="300px" />
      </div>
    )
  }

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="p-6 space-y-6">
      <motion.div variants={item} className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="p-2 rounded-xl bg-surface-2 text-accent"><Globe className="w-6 h-6" /></div>
            <h1 className="text-2xl font-bold text-text">Internet Booster</h1>
          </div>
          <p className="text-sm text-text-secondary ml-11">Optimize connection speed and stability</p>
        </div>
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard icon={<ArrowDownRight className="w-5 h-5" />} label="Download" value={formatSpeed(systemInfo.network?.speed_down)} progress={Math.min((systemInfo.network?.speed_down || 0) / 1024 / 1024 * 100, 100)} sub="Current speed" />
        <MetricCard icon={<ArrowUpRight className="w-5 h-5" />} label="Upload" value={formatSpeed(systemInfo.network?.speed_up)} progress={Math.min((systemInfo.network?.speed_up || 0) / 1024 / 1024 * 100, 100)} sub="Current speed" />
        <MetricCard icon={<Wifi className="w-5 h-5" />} label="Total Downloaded" value={systemInfo.network ? (systemInfo.network.bytes_recv / 1024 / 1024 / 1024).toFixed(1) + ' GB' : '--'} sub="Since boot" />
        <MetricCard icon={<Globe className="w-5 h-5" />} label="Total Uploaded" value={systemInfo.network ? (systemInfo.network.bytes_sent / 1024 / 1024 / 1024).toFixed(1) + ' GB' : '--'} sub="Since boot" />
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card padding="lg" className="lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-text flex items-center gap-2"><Wifi className="w-4 h-4 text-accent" />Network Adapters</h2>
            <Button variant="ghost" size="sm" icon={<RefreshCw className="w-4 h-4" />} loading={loadingAdapters} onClick={() => window.location.reload()}>Refresh</Button>
          </div>
          {loadingAdapters ? (
            <div className="space-y-2">{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} variant="rectangular" height="56px" />)}</div>
          ) : adapters.length ? (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {adapters.map((adapter, i) => (
                <motion.div key={i} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.05 }} className="flex items-center justify-between p-3 rounded-xl bg-surface-2/60 hover:bg-surface-2 transition-colors">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-surface-3 text-accent"><WifiIcon className="w-5 h-5" /></div>
                    <div>
                      <p className="text-sm font-medium text-text">{adapter.name}</p>
                      <p className="text-xs text-text-secondary">{adapter.description}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={cn('px-2 py-1 rounded text-xs font-medium', adapter.enabled ? 'bg-green-dim text-green' : 'bg-red-dim text-red')}>
                      {adapter.enabled ? 'Enabled' : 'Disabled'}
                    </span>
                    <Badge variant="info">{adapter.speed}</Badge>
                  </div>
                </motion.div>
              ))}
            </div>
          ) : (
            <p className="text-text-secondary text-center py-8">No network adapters found</p>
          )}
        </Card>

        <Card padding="lg">
          <h2 className="text-sm font-semibold text-text mb-4 flex items-center gap-2"><Shield className="w-4 h-4 text-accent" />DNS Optimization</h2>
          <div className="grid grid-cols-2 gap-2">
            {dnsProviders.map((provider, i) => (
              <motion.button key={i} initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: i * 0.05 }} onClick={() => setDNS(provider)} disabled={!!dnsLoading} className="relative p-3 rounded-xl bg-surface-2 border border-border text-left hover:bg-surface-3 hover:border-accent/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
                <div className="flex items-center gap-2 mb-1">
                  <div className="p-1.5 rounded bg-surface-3 text-accent">{provider.icon}</div>
                  <span className="font-medium text-text">{provider.name}</span>
                </div>
                <div className="flex items-center gap-1 text-xs text-text-tertiary">
                  <span>{provider.primary}</span>
                  <span className="text-surface-3">/</span>
                  <span>{provider.secondary}</span>
                </div>
                {dnsLoading === provider.id && <Loader2 className="absolute top-2 right-2 w-4 h-4 text-accent animate-spin" />}
              </motion.button>
            ))}
          </div>
        </Card>
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card padding="lg" className="lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-text flex items-center gap-2"><Gauge className="w-4 h-4 text-accent" />Bufferbloat Control</h2>
          </div>
          <div className="grid grid-cols-3 gap-2">
            {bufferbloatPresets.map((preset, i) => (
              <motion.button key={i} initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: i * 0.05 }} onClick={() => setBufferbloat(preset)} disabled={!!bufferbloatLoading} className="relative p-4 rounded-xl bg-surface-2 border border-border text-left hover:bg-surface-3 hover:border-accent/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
                <div className="p-2 rounded-lg bg-surface-3 text-accent mb-2">{preset.icon}</div>
                <p className="font-medium text-text">{preset.name}</p>
                <p className="text-xs text-text-secondary">{preset.desc}</p>
                {bufferbloatLoading === preset.id && <Loader2 className="absolute top-2 right-2 w-4 h-4 text-accent animate-spin" />}
              </motion.button>
            ))}
          </div>
        </Card>

        <Card padding="lg">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-text flex items-center gap-2"><Shield className="w-4 h-4 text-accent" />QoS / Network Priority</h2>
            <button onClick={toggleQoS} disabled={qosLoading} className={cn('relative px-3 py-1.5 rounded-lg text-sm font-medium transition-colors', qosEnabled ? 'bg-accent text-white' : 'bg-surface-2 text-text-secondary hover:bg-surface-3 hover:text-text')}>
              {qosLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : qosEnabled ? 'Enabled' : 'Disabled'}
            </button>
          </div>
          <p className="text-xs text-text-secondary mb-4">Force game packets priority for lower latency</p>
          <Button variant="default" icon={<Zap className="w-4 h-4" />} loading={bufferbloatLoading === 'low_latency'} onClick={() => setBufferbloat(bufferbloatPresets[0])} className="w-full">Low Latency (Gaming)</Button>
          <Button variant="secondary" icon={<ArrowDownRight className="w-4 h-4" />} loading={bufferbloatLoading === 'high_throughput'} onClick={() => setBufferbloat(bufferbloatPresets[1])} className="w-full mt-2">High Throughput</Button>
          <Button variant="secondary" icon={<Gauge className="w-4 h-4" />} loading={bufferbloatLoading === 'balanced'} onClick={() => setBufferbloat(bufferbloatPresets[2])} className="w-full mt-2">Balanced</Button>
          <Button variant="ghost" icon={<Settings className="w-4 h-4" />} loading={loadingAction === 'tcp'} onClick={runOptimizeTCP} className="w-full mt-2">Advanced TCP Tweaks</Button>
        </Card>
      </motion.div>

      <motion.div variants={item}>
        <h2 className="text-sm font-semibold text-text mb-3 flex items-center gap-2"><Wifi className="w-4 h-4 text-accent" />Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <ActionCard icon={<RefreshCw className="w-5 h-5" />} title="Flush DNS Cache" desc="Clear DNS resolver cache for fresh lookups" tags={['Network']} variant="default" onClick={runFlushDNS} loading={loadingAction === 'flushdns'} />
          <ActionCard icon={<WifiIcon className="w-5 h-5" />} title="Run Speed Test" desc="Ping test to measure latency" tags={['Test']} variant="default" onClick={runPing} loading={pingLoading} />
          <ActionCard icon={<Globe className="w-5 h-5" />} title="Optimize TCP Stack" desc="BBR, window scaling, timestamps" tags={['TCP', 'Advanced']} variant="default" onClick={runOptimizeTCP} loading={loadingAction === 'tcp'} />
          <ActionCard icon={<Shield className="w-5 h-5" />} title="Enable QoS" desc="Prioritize gaming traffic" tags={['Priority']} variant="success" onClick={toggleQoS} loading={qosLoading} />
        </div>
      </motion.div>

      {(pingResult || flushResult) && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mt-4 p-4 rounded-xl bg-surface-2/60 border border-border">
          <div className="flex items-center gap-2 text-sm text-text-secondary">
            <Database className="w-4 h-4 text-accent" />
            {pingResult && <span>Ping: {pingResult}</span>}
            {flushResult && <span>Flush DNS: {flushResult}</span>}
          </div>
        </motion.div>
      )}

      {result && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="relative z-10 mt-4 p-4 rounded-xl border" style={{ borderColor: result.success ? '#22c55e' : '#ef4444', backgroundColor: result.success ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)' }}>
          <div className="flex items-center gap-3">
            <div className={cn('w-2 h-2 rounded-full', result.success ? 'bg-green' : 'bg-red')} />
            <span className="text-sm text-text">{result.message}</span>
          </div>
        </motion.div>
      )}
    </motion.div>
  )
}