import { useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  Activity,
  Gauge,
  ArrowDown,
  ArrowUp,
  Wifi,
  Clock,
  AlertTriangle,
  RefreshCw,
  Play,
} from 'lucide-react'
import { Card } from '../ui/Card'

import { Badge } from '../ui/Badge'
import { MetricCard } from '../ui/MetricCard'
import { cn } from '../../lib/utils'
import { api } from '../../lib/api'

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.05 } },
}

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
}

interface PingResult {
  avg_ms: number
  min_ms: number
  max_ms: number
  packet_loss: number
}

interface SpeedResult {
  download_mbps?: number
  upload_mbps?: number
}

export function SpeedTestPage() {
  const [testing, setTesting] = useState(false)
  const [phase, setPhase] = useState<'idle' | 'ping' | 'download' | 'upload' | 'done'>('idle')
  const [pingResult, setPingResult] = useState<PingResult | null>(null)
  const [downloadResult, setDownloadResult] = useState<SpeedResult | null>(null)
  const [uploadResult, setUploadResult] = useState<SpeedResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [history, setHistory] = useState<{ time: string; ping: number; download: number; upload: number }[]>([])

  const startTest = useCallback(async () => {
    setTesting(true)
    setError(null)
    setPhase('ping')
    try {
      const res = await api.speedTestAll()
      setPingResult(res.ping)
      setPhase('download')
      setDownloadResult(res.download as SpeedResult)
      setPhase('upload')
      setUploadResult(res.upload as SpeedResult)
      setPhase('done')
      const now = new Date().toLocaleTimeString()
      setHistory(prev => [{
        time: now,
        ping: res.ping.avg_ms,
        download: res.download.download_mbps,
        upload: res.upload.upload_mbps,
      }, ...prev].slice(0, 10))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Speed test failed')
      setPhase('idle')
    }
    setTesting(false)
  }, [])

  const gaugePercent = (mbps: number, max: number) => Math.min(100, Math.round((mbps / max) * 100))

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-6">
      <motion.div variants={item}>
        <div className="flex items-center gap-3 mb-1">
          <Activity className="w-6 h-6 text-accent" />
          <h1 className="text-2xl font-bold tracking-tight text-text">Speed Test</h1>
        </div>
        <p className="text-sm text-text-secondary ml-9">Measure your internet connection speed</p>
      </motion.div>

      <motion.div variants={item} className="flex flex-col items-center gap-4 py-6">
        <div className="relative">
          <div className={cn(
            'w-32 h-32 rounded-full flex items-center justify-center border-4 transition-all duration-500',
            phase === 'idle' ? 'border-accent/40 bg-accent-dim/20' :
            phase === 'done' ? 'border-green bg-green-dim/20' :
            'border-accent bg-accent-dim/20 animate-pulse'
          )}>
            <button
              onClick={startTest}
              disabled={testing}
              className="w-full h-full rounded-full flex flex-col items-center justify-center cursor-pointer disabled:opacity-50"
            >
              {testing ? (
                <svg className="animate-spin w-8 h-8 text-accent" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25" />
                  <path d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" fill="currentColor" className="opacity-75" />
                </svg>
              ) : (
                <Play className="w-8 h-8 text-accent" />
              )}
              <span className="text-[10px] text-text-secondary mt-1">Start Test</span>
            </button>
          </div>
          {testing && (
            <div className="absolute -bottom-6 left-1/2 -translate-x-1/2 whitespace-nowrap">
              <Badge variant="accent">
                {phase === 'ping' ? 'Testing Ping...' :
                 phase === 'download' ? 'Testing Download...' :
                 phase === 'upload' ? 'Testing Upload...' : ''}
              </Badge>
            </div>
          )}
        </div>
      </motion.div>

      {error && (
        <motion.div variants={item} className="p-4 rounded-xl border bg-red-dim border-red/30">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-4 h-4 text-red" />
            <p className="text-sm font-medium text-red">{error}</p>
          </div>
        </motion.div>
      )}

      {(pingResult || downloadResult || uploadResult) && (
        <>
          <motion.div variants={item} className="grid grid-cols-3 gap-4">
            <MetricCard
              icon={<Clock className="w-5 h-5" />}
              label="Ping"
              value={pingResult ? `${pingResult.avg_ms.toFixed(1)} ms` : '--'}
              sub={pingResult ? `min: ${pingResult.min_ms}ms / max: ${pingResult.max_ms}ms` : undefined}
            />
            <MetricCard
              icon={<ArrowDown className="w-5 h-5" />}
              label="Download"
              value={downloadResult?.download_mbps != null ? `${downloadResult.download_mbps.toFixed(1)} Mbps` : '--'}
              progress={downloadResult?.download_mbps != null ? gaugePercent(downloadResult.download_mbps, 1000) : 0}
            />
            <MetricCard
              icon={<ArrowUp className="w-5 h-5" />}
              label="Upload"
              value={uploadResult?.upload_mbps != null ? `${uploadResult.upload_mbps.toFixed(1)} Mbps` : '--'}
              progress={uploadResult?.upload_mbps != null ? gaugePercent(uploadResult.upload_mbps, 100) : 0}
            />
          </motion.div>

          {pingResult && (
            <motion.div variants={item}>
              <Card padding="lg">
                <div className="flex items-center gap-2 mb-3">
                  <Wifi className="w-5 h-5 text-accent" />
                  <h2 className="text-sm font-semibold text-text">Ping Details</h2>
                </div>
                <div className="grid grid-cols-4 gap-3">
                  <div className="p-3 rounded-xl bg-surface-2 text-center">
                    <p className="text-[11px] text-text-tertiary">Average</p>
                    <p className="text-lg font-semibold text-text">{pingResult.avg_ms.toFixed(1)} ms</p>
                  </div>
                  <div className="p-3 rounded-xl bg-surface-2 text-center">
                    <p className="text-[11px] text-text-tertiary">Minimum</p>
                    <p className="text-lg font-semibold text-text">{pingResult.min_ms.toFixed(1)} ms</p>
                  </div>
                  <div className="p-3 rounded-xl bg-surface-2 text-center">
                    <p className="text-[11px] text-text-tertiary">Maximum</p>
                    <p className="text-lg font-semibold text-text">{pingResult.max_ms.toFixed(1)} ms</p>
                  </div>
                  <div className="p-3 rounded-xl bg-surface-2 text-center">
                    <p className="text-[11px] text-text-tertiary">Packet Loss</p>
                    <p className={cn('text-lg font-semibold', pingResult.packet_loss > 0 ? 'text-red' : 'text-green')}>
                      {pingResult.packet_loss}%
                    </p>
                  </div>
                </div>
              </Card>
            </motion.div>
          )}

          {history.length > 0 && (
            <motion.div variants={item}>
              <Card padding="lg">
                <div className="flex items-center gap-2 mb-3">
                  <RefreshCw className="w-5 h-5 text-accent" />
                  <h2 className="text-sm font-semibold text-text">Test History</h2>
                </div>
                <div className="divide-y divide-border">
                  {history.map((h, i) => (
                    <div key={i} className="flex items-center justify-between py-2 text-xs text-text-secondary">
                      <span>{h.time}</span>
                      <div className="flex gap-4">
                        <span><Clock className="w-3 h-3 inline mr-1" />{h.ping} ms</span>
                        <span><ArrowDown className="w-3 h-3 inline mr-1" />{h.download.toFixed(1)} Mbps</span>
                        <span><ArrowUp className="w-3 h-3 inline mr-1" />{h.upload.toFixed(1)} Mbps</span>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            </motion.div>
          )}
        </>
      )}

      {phase === 'idle' && !error && (
        <motion.div variants={item}>
          <Card padding="lg" className="text-center">
            <Gauge className="w-12 h-12 text-text-tertiary mx-auto mb-3" />
            <p className="text-sm text-text-secondary">Press the Start Test button to measure your connection speed.</p>
            <p className="text-xs text-text-tertiary mt-1">Tests ping, download, and upload speeds sequentially.</p>
          </Card>
        </motion.div>
      )}
    </motion.div>
  )
}
