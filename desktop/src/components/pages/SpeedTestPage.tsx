import { useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
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

import { Button } from '../ui/Button'
import { PageHero } from '../ui/PageHero'
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

  const phaseLabel = testing
    ? phase === 'ping' ? 'Testing ping…'
      : phase === 'download' ? 'Testing download…'
      : phase === 'upload' ? 'Testing upload…' : 'Running…'
    : phase === 'done' ? 'Complete' : 'Idle'

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="page space-y-6">
      {/* The hero is the readout: last measured ping, download and upload are
          already the three numbers people come here for, so repeating them in
          a tile row underneath added nothing. */}
      <motion.div variants={item}>
        <PageHero
          eyebrow="Network · Measure"
          title="Speed Test"
          subtitle="One sequential run: ICMP ping first, then download, then upload. Nothing is cached between runs."
          icon={<Gauge size={19} />}
          stats={[
            { label: 'Ping', value: pingResult ? `${pingResult.avg_ms.toFixed(1)} ms` : '—', hint: pingResult ? `min ${pingResult.min_ms} / max ${pingResult.max_ms}` : 'not measured' },
            { label: 'Download', value: downloadResult?.download_mbps != null ? `${downloadResult.download_mbps.toFixed(1)}` : '—', hint: 'Mbps' },
            { label: 'Upload', value: uploadResult?.upload_mbps != null ? `${uploadResult.upload_mbps.toFixed(1)}` : '—', hint: 'Mbps' },
            { label: 'Status', value: phaseLabel, tone: testing ? 'accent' : phase === 'done' ? 'good' : 'default', hint: history.length ? `${history.length} run(s) this session` : undefined },
          ]}
          actions={
            <Button variant="primary" size="md" icon={<Play size={14} />} onClick={startTest} loading={testing}>
              {phase === 'done' ? 'Test again' : 'Start test'}
            </Button>
          }
        />
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
          {pingResult && (
            <motion.div variants={item}>
              <Card padding="lg">
                <div className="flex items-center gap-2 mb-3">
                  <Wifi className="w-5 h-5 text-accent" />
                  <h2 className="text-sm font-semibold text-text">Ping Details</h2>
                </div>
                <div className="grid grid-cols-4 gap-3">
                  <div className="card-depth p-3 rounded-xl border border-border bg-surface-1 text-center">
                    <p className="text-[11px] text-text-tertiary">Average</p>
                    <p className="text-lg font-semibold text-text tnum">{pingResult.avg_ms.toFixed(1)} ms</p>
                  </div>
                  <div className="card-depth p-3 rounded-xl border border-border bg-surface-1 text-center">
                    <p className="text-[11px] text-text-tertiary">Minimum</p>
                    <p className="text-lg font-semibold text-text tnum">{pingResult.min_ms.toFixed(1)} ms</p>
                  </div>
                  <div className="card-depth p-3 rounded-xl border border-border bg-surface-1 text-center">
                    <p className="text-[11px] text-text-tertiary">Maximum</p>
                    <p className="text-lg font-semibold text-text tnum">{pingResult.max_ms.toFixed(1)} ms</p>
                  </div>
                  <div className="card-depth p-3 rounded-xl border border-border bg-surface-1 text-center">
                    <p className="text-[11px] text-text-tertiary">Packet Loss</p>
                    <p className={cn('text-lg font-semibold tnum', pingResult.packet_loss > 0 ? 'text-red' : 'text-green')}>
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

    </motion.div>
  )
}
