import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  Network,
  ArrowDownToLine,
  ArrowUpFromLine,
  Database,
  Wifi,
  Zap,
  RefreshCw,
  Gauge,
  SlidersHorizontal,
  Globe,
  Cloud,
  Shield,
  AlertCircle,
  Loader2,
} from 'lucide-react'
import { Card } from '../ui/Card'
import { Button } from '../ui/Button'
import { MetricCard } from '../ui/MetricCard'
import { ActionCard } from '../ui/ActionCard'
import { Skeleton } from '../ui/Skeleton'
import { cn, formatBytes, formatSpeed } from '../../lib/utils'
import type { SystemInfo, NetworkAdapter } from '../../types'
import { api } from '../../lib/api'

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.05 } },
}

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
}

export function NetworkPage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const [adapters, setAdapters] = useState<NetworkAdapter[]>([])
  const [adaptersLoading, setAdaptersLoading] = useState(true)
  const [loadingAction, setLoadingAction] = useState<string | null>(null)
  const [result, setResult] = useState<{ key: string; message: string; success: boolean } | null>(null)
  const [dnsLoading, setDnsLoading] = useState<string | null>(null)
  const [pingHost, setPingHost] = useState('8.8.8.8')
  const [pingLoading, setPingLoading] = useState(false)
  const [pingResult, setPingResult] = useState<string | null>(null)

  const dnsProviders = [
    { id: 'cloudflare', name: 'Cloudflare', icon: <Cloud className="w-5 h-5" />, primary: '1.1.1.1', secondary: '1.0.0.1' },
    { id: 'google', name: 'Google', icon: <Globe className="w-5 h-5" />, primary: '8.8.8.8', secondary: '8.8.4.4' },
    { id: 'opendns', name: 'OpenDNS', icon: <Shield className="w-5 h-5" />, primary: '208.67.222.222', secondary: '208.67.220.220' },
    { id: 'quad9', name: 'Quad9', icon: <AlertCircle className="w-5 h-5" />, primary: '9.9.9.9', secondary: '149.112.112.112' },
    { id: 'adguard', name: 'AdGuard', icon: <Shield className="w-5 h-5" />, primary: '94.140.14.14', secondary: '94.140.15.15' },
  ]

  const setDNS = async (provider: typeof dnsProviders[0]) => {
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
  }

  const runCustomPing = async () => {
    setPingLoading(true)
    setResult(null)
    try {
      const d = await api.ping(pingHost)
      setPingResult(d.output || 'Ping complete')
      setResult({ key: 'ping', message: `Ping to ${pingHost} complete`, success: true })
    } catch (e) {
      setPingResult('Ping failed')
      setResult({ key: 'ping', message: e instanceof Error ? e.message : 'Ping failed', success: false })
    } finally {
      setPingLoading(false)
    }
  }

  const loadAdapters = useCallback(async () => {
    setAdaptersLoading(true)
    try {
      const res = await api.networkAdapters()
      setAdapters(res.adapters)
    } catch {
      setAdapters([])
    } finally {
      setAdaptersLoading(false)
    }
  }, [])

  useEffect(() => { loadAdapters() }, [loadAdapters])

  const runAction = async (key: string, fn: () => Promise<unknown>, successMsg: string) => {
    setLoadingAction(key)
    setResult(null)
    try {
      await fn()
      setResult({ key, message: successMsg, success: true })
    } catch (e) {
      setResult({ key, message: e instanceof Error ? e.message : 'Operation failed', success: false })
    } finally {
      setLoadingAction(null)
    }
  }

  if (!systemInfo) {
    return (
      <div className="p-6 space-y-6">
        <div><Skeleton variant="text" width="200px" height="28px" /><Skeleton variant="text" width="300px" height="16px" className="mt-2" /></div>
        <div className="grid grid-cols-3 gap-4"><Skeleton variant="rectangular" height="120px" /><Skeleton variant="rectangular" height="120px" /><Skeleton variant="rectangular" height="120px" /></div>
        <Skeleton variant="rectangular" height="200px" />
        <div className="grid grid-cols-3 gap-4"><Skeleton variant="rectangular" height="160px" /><Skeleton variant="rectangular" height="160px" /><Skeleton variant="rectangular" height="160px" /></div>
      </div>
    )
  }

  const net = systemInfo.network
  const totalData = net.bytes_sent + net.bytes_recv

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="p-6 space-y-6">
      <motion.div variants={item}>
        <div className="flex items-center gap-3 mb-1">
          <Network className="w-6 h-6 text-accent" />
          <h1 className="text-2xl font-bold text-text">Network</h1>
        </div>
        <p className="text-sm text-text-secondary ml-9">Monitor and optimize network performance</p>
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-3 gap-4">
        <MetricCard icon={<ArrowDownToLine className="w-5 h-5" />} label="Download Speed" value={formatSpeed(net.speed_down)} trend={{ value: 'active', up: true }} sub="Current throughput" />
        <MetricCard icon={<ArrowUpFromLine className="w-5 h-5" />} label="Upload Speed" value={formatSpeed(net.speed_up)} trend={{ value: 'active', up: true }} sub="Current throughput" />
        <MetricCard icon={<Database className="w-5 h-5" />} label="Total Data" value={formatBytes(totalData)} sub={`${formatBytes(net.bytes_recv)} down / ${formatBytes(net.bytes_sent)} up`} />
      </motion.div>

      <motion.div variants={item}>
        <Card>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Wifi className="w-5 h-5 text-accent" />
              <h2 className="text-sm font-semibold text-text">Network Adapters</h2>
            </div>
            <Button variant="ghost" size="sm" icon={<RefreshCw className="w-4 h-4" />} loading={adaptersLoading} onClick={loadAdapters}>Refresh</Button>
          </div>
          {adaptersLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} variant="rectangular" height="52px" />)}
            </div>
          ) : adapters.length === 0 ? (
            <p className="text-xs text-text-tertiary py-4 text-center">No adapters detected</p>
          ) : (
            <div className="divide-y divide-border">
              {adapters.map((a) => (
                <div key={a.name} className="flex items-center justify-between py-3 first:pt-0 last:pb-0">
                  <div className="flex items-center gap-3">
                    <div className={cn('w-2 h-2 rounded-full', a.enabled ? 'bg-green' : 'bg-text-tertiary')} />
                    <div>
                      <p className="text-sm font-medium text-text">{a.name}</p>
                      <p className="text-xs text-text-tertiary">{a.description}</p>
                    </div>
                  </div>
                  <span className="text-xs text-text-secondary">{a.speed}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <ActionCard
          icon={<Globe className="w-5 h-5" />}
          title="DNS Optimizer"
          desc="Switch to fastest DNS providers for reduced latency"
          tags={['Network', 'Latency']}
          onClick={() => runAction('dns', () => api.dns('cloudflare'), 'DNS optimized to Cloudflare')}
        />
        <ActionCard
          icon={<RefreshCw className="w-5 h-5" />}
          title="Flush DNS"
          desc="Clear DNS cache to resolve connectivity issues"
          tags={['Maintenance']}
          onClick={() => runAction('flush', () => api.flushDns(), 'DNS cache flushed')}
        />
        <ActionCard
          icon={<Zap className="w-5 h-5" />}
          title="QoS Toggle"
          desc="Enable Quality of Service for traffic prioritization"
          tags={['Optimization']}
          onClick={() => runAction('qos', () => api.qos(true), 'QoS enabled')}
        />
        <ActionCard
          icon={<Gauge className="w-5 h-5" />}
          title="Bufferbloat Control"
          desc="Reduce latency spikes under load"
          tags={['Latency']}
          onClick={() => runAction('bufferbloat', () => api.bufferbloat('low-latency'), 'Bufferbloat set to low-latency')}
        />
        <ActionCard
          icon={<SlidersHorizontal className="w-5 h-5" />}
          title="Advanced TCP Tweaks"
          desc="Apply TCP optimizations for better throughput"
          tags={['Advanced']}
          onClick={() => runAction('tcp', () => api.advancedNetwork(), 'TCP tweaks applied')}
        />
      </motion.div>

      <motion.div variants={item}>
        <Card padding="lg">
          <h2 className="text-sm font-semibold text-text mb-4 flex items-center gap-2"><Globe className="w-4 h-4 text-accent" />DNS Provider</h2>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
            {dnsProviders.map((provider, i) => (
              <motion.button
                key={provider.id}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.05 }}
                onClick={() => setDNS(provider)}
                disabled={!!dnsLoading}
                className="relative p-3 rounded-xl bg-surface-2 border border-border text-left hover:bg-surface-3 hover:border-accent/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
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

      <motion.div variants={item}>
        <Card padding="lg">
          <h2 className="text-sm font-semibold text-text mb-4 flex items-center gap-2"><Wifi className="w-4 h-4 text-accent" />Ping Test</h2>
          <div className="flex items-center gap-3">
            <input
              type="text"
              value={pingHost}
              onChange={(e) => setPingHost(e.target.value)}
              placeholder="Hostname or IP"
              className="flex-1 px-3 py-2 text-sm rounded-xl bg-surface-2 border border-border text-text placeholder-text-tertiary focus:outline-none focus:border-accent/50"
            />
            <Button variant="default" size="sm" icon={<Zap className="w-4 h-4" />} loading={pingLoading} onClick={runCustomPing}>
              Ping
            </Button>
          </div>
          {pingResult && (
            <p className="mt-3 text-xs text-text-secondary">{pingResult}</p>
          )}
        </Card>
      </motion.div>

      {result && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className={cn('p-4 rounded-xl border', result.success ? 'bg-green-dim border-green/30' : 'bg-red-dim border-red/30')}>
          <div className="flex items-center gap-3">
            <div className={cn('w-2 h-2 rounded-full', result.success ? 'bg-green' : 'bg-red')} />
            <p className={cn('text-sm font-medium', result.success ? 'text-green' : 'text-red')}>{result.message}</p>
          </div>
        </motion.div>
      )}

      {loadingAction && (
        <div className="flex items-center gap-2 text-xs text-text-secondary">
          <svg className="animate-spin h-3 w-3 text-accent" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
          Running optimization...
        </div>
      )}
    </motion.div>
  )
}
