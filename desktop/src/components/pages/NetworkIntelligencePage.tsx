import { useState, useEffect, useCallback, useMemo } from 'react'
import { motion } from 'framer-motion'
import { Activity, Globe, Route, ShieldCheck, CircleAlert, RefreshCw, Loader2, Server, Clock } from 'lucide-react'
import { Card } from '../ui/Card'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { Skeleton } from '../ui/Skeleton'
import { PageHero } from '../ui/PageHero'
import { StreamArea } from '../ui/charts/StreamArea'
import { api } from '../../lib/api'
import { formatChartTick } from '../../lib/utils'
import type { NetworkAnalyzeResult, NetworkTraceResult, NetworkTarget, NetworkDnsServers } from '../../types'

/* Series colours come from tokens so the chart follows the accent preset and
   the light theme instead of pinning three dark-mode hexes. */
const COLORS = { latency: 'var(--chart-1)', jitter: 'var(--chart-2)', loss: 'var(--color-red)' }

const containerVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.06 } },
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { type: 'spring' as const, stiffness: 260, damping: 24 } },
}

/** One row appended to session history after each completed measurement. */
interface HistoryRow {
  ts: number
  target: string
  avg_ms: number | null
  jitter_ms: number | null
  loss_pct: number | null
  ok: boolean
}

/**
 * Subjective label for a latency/jitter pair. These thresholds are ordinary
 * gaming guidance, not an official measurement — the raw numbers are always
 * shown next to them so the user can judge for themselves.
 */
function grade(avg: number | null, jitter: number | null, loss: number | null): { label: string; tone: 'success' | 'warning' | 'danger' | 'default' } {
  if (avg == null) return { label: 'Unreachable', tone: 'danger' }
  if (loss != null && loss >= 5) return { label: 'Lossy', tone: 'danger' }
  if (avg <= 40 && (jitter ?? 0) <= 15) return { label: 'Excellent', tone: 'success' }
  if (avg <= 80 && (jitter ?? 0) <= 30) return { label: 'Good', tone: 'success' }
  if (avg <= 150 && (jitter ?? 0) <= 60) return { label: 'Fair', tone: 'warning' }
  return { label: 'Poor', tone: 'danger' }
}

/** Metric cell that renders "--" rather than a fake 0 when the value is absent. */
function Metric({ label, value, unit, tone }: { label: string; value: number | null | undefined; unit?: string; tone?: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[10.5px] font-semibold uppercase tracking-[0.04em] text-text-tertiary">{label}</span>
      <span className="text-xl font-semibold tnum" style={{ color: tone }}>
        {value != null ? `${value}${unit ?? ''}` : '--'}
      </span>
    </div>
  )
}

export function NetworkIntelligencePage() {
  const [targets, setTargets] = useState<NetworkTarget[]>([])
  const [dnsServers, setDnsServers] = useState<NetworkDnsServers | null>(null)
  const [selectedHost, setSelectedHost] = useState<string>('')
  const [customHost, setCustomHost] = useState('')
  const [count, setCount] = useState(10)

  const [analyzing, setAnalyzing] = useState(false)
  const [result, setResult] = useState<NetworkAnalyzeResult | null>(null)
  const [analyzeError, setAnalyzeError] = useState<string | null>(null)

  const [tracing, setTracing] = useState(false)
  const [trace, setTrace] = useState<NetworkTraceResult | null>(null)
  const [traceError, setTraceError] = useState<string | null>(null)

  const [history, setHistory] = useState<HistoryRow[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)

  /* Preset targets + the machine's configured DNS servers. Both are optional
     context: if they fail the page still works with a custom host. */
  useEffect(() => {
    let alive = true
    api.networkTargets()
      .then((r) => {
        if (!alive) return
        setTargets(r.targets ?? [])
        if (r.targets?.length) setSelectedHost((prev) => prev || r.targets[0].host)
      })
      .catch((e) => alive && setLoadError((e as Error).message))
    api.networkDnsServers()
      .then((r) => alive && setDnsServers(r))
      .catch(() => { /* non-fatal; the card renders an unavailable state */ })
    return () => { alive = false }
  }, [])

  const activeHost = customHost.trim() || selectedHost

  const runAnalyze = useCallback(async () => {
    const host = activeHost.trim()
    if (!host || analyzing) return
    setAnalyzing(true)
    setAnalyzeError(null)
    // Drop the previous result so the header never credits a stale target
    // with a measurement that belongs to a different one.
    setResult(null)
    try {
      const res = await api.networkAnalyze(host, count)
      setResult(res)
      const lat = res.latency
      setHistory((prev) => [{
        ts: (res.timestamp ?? Date.now() / 1000) * 1000,
        target: res.target,
        avg_ms: lat.avg_ms ?? null,
        jitter_ms: lat.jitter_ms ?? null,
        loss_pct: lat.packet_loss_pct ?? null,
        ok: !!lat.ok,
      }, ...prev].slice(0, 60))
    } catch (e) {
      setAnalyzeError((e as Error).message)
    } finally {
      setAnalyzing(false)
    }
  }, [activeHost, count, analyzing])

  const runTrace = useCallback(async () => {
    const host = activeHost.trim()
    if (!host || tracing) return
    setTracing(true)
    setTraceError(null)
    setTrace(null)
    try {
      setTrace(await api.networkTrace(host))
    } catch (e) {
      setTraceError((e as Error).message)
    } finally {
      setTracing(false)
    }
  }, [activeHost, tracing])

  const lat = result?.latency
  const g = useMemo(() => grade(lat?.avg_ms ?? null, lat?.jitter_ms ?? null, lat?.packet_loss_pct ?? null), [lat])

  /* Sparkline series for the session: one point per completed measurement. */
  const chartData = useMemo(() => history
    .filter((h) => h.ok && h.avg_ms != null)
    .slice()
    .reverse()
    .map((h) => ({ ts: h.ts, latency: h.avg_ms, jitter: h.jitter_ms })), [history])

  /* Chart shape: y-domain follows the measured peak (never below the 40 ms
     reference), and the reference is expressed as a guide so the d3 chart
     keeps the same reader aid the old recharts one had. */
  const trend = useMemo(() => {
    const peak = Math.max(40, ...chartData.flatMap((d) => [d.latency ?? 0, d.jitter ?? 0]), 1)
    const yMax = Math.ceil((peak * 1.15) / 10) * 10
    return {
      yMax,
      guides: [Math.round((40 / yMax) * 100)],
      labels: chartData.map((d) => formatChartTick(d.ts)),
      series: [
        { key: 'latency', label: 'Avg latency', color: COLORS.latency, values: chartData.map((d) => d.latency ?? 0) },
        { key: 'jitter', label: 'Jitter (σ)', color: COLORS.jitter, values: chartData.map((d) => d.jitter ?? 0), fill: false },
      ],
    }
  }, [chartData])

  if (loadError && targets.length === 0 && !dnsServers) {
    return (
      <div className="page space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-text flex items-center gap-3">
            <Globe className="text-accent" size={28} />
            Network Intelligence
          </h1>
          <p className="text-sm text-text-secondary mt-1">Latency, jitter, packet loss and route diagnostics</p>
        </div>
        <div className="surface-card p-5 flex items-start gap-3">
          <CircleAlert size={18} className="text-red shrink-0 mt-0.5" />
          <div>
            <h2 className="text-[15px] font-medium">Could not reach the Optinix service</h2>
            <p className="text-[12.5px] text-text-secondary mt-1">{loadError}</p>
            <p className="text-[12px] text-text-tertiary mt-2">
              Measurements stay blank until the backend responds — Optinix never fills them with placeholder values.
            </p>
            <Button size="sm" variant="secondary" icon={<RefreshCw size={13} />} className="mt-3" onClick={() => window.location.reload()}>
              Try again
            </Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <motion.div variants={containerVariants} initial="hidden" animate="show" className="page space-y-5">
      <motion.div variants={itemVariants}>
        <PageHero
          eyebrow="Network · Measure"
          title="Network Intelligence"
          subtitle="Real latency, jitter and packet-loss measurements to a target you choose."
          icon={<Globe size={19} />}
          badges={lat ? <Badge variant={g.tone === 'default' ? 'default' : g.tone}>{g.label}</Badge> : undefined}
          stats={[
            { label: 'Target', value: (result?.target ?? activeHost) || 'none', hint: 'ICMP echo' },
            { label: 'Avg latency', value: lat?.avg_ms != null ? `${lat.avg_ms} ms` : '--', tone: 'accent', hint: `min ${lat?.min_ms ?? '--'} ms` },
            { label: 'Jitter', value: lat?.jitter_ms != null ? `${lat.jitter_ms} ms` : '--', hint: 'deviation between probes' },
            { label: 'Loss', value: lat?.packet_loss_pct != null ? `${lat.packet_loss_pct}%` : '--', tone: lat?.packet_loss_pct ? 'bad' : 'good', hint: 'of sent probes' },
          ]}
        />
      </motion.div>

      {/* Honest scope statement: these are diagnostics, not traffic routing. */}
      <motion.div variants={itemVariants} className="card-depth surface-card p-4 flex items-start gap-3">
        <ShieldCheck size={16} className="text-accent shrink-0 mt-0.5" />
        <p className="text-[12.5px] leading-[1.55] text-text-secondary">
          <span className="font-medium text-text">Diagnostics only.</span>{' '}
          Optinix measures the connection you already have; it does not reroute your traffic. It runs no relay
          infrastructure, so features like multipath or &ldquo;optimized routes&rdquo; are not offered. Every number on
          this page comes from an actual probe — if a probe fails, the value is left blank rather than estimated.
        </p>
      </motion.div>

      {/* Target picker */}
      <motion.div variants={itemVariants}>
        <Card padding="lg">
          <h2 className="text-sm font-semibold text-text flex items-center gap-2 mb-4">
            <Server size={16} className="text-accent" />
            Target
          </h2>
          <div className="flex flex-wrap items-end gap-3">
            <div className="flex flex-wrap gap-2">
              {targets.map((t) => (
                <Button
                  key={t.id}
                  size="sm"
                  variant={selectedHost === t.host && !customHost.trim() ? 'primary' : 'secondary'}
                  onClick={() => { setSelectedHost(t.host); setCustomHost('') }}
                  title={t.note}
                >
                  {t.label}
                </Button>
              ))}
            </div>
            <label className="flex flex-col gap-1 ml-auto">
              <span className="text-[10.5px] font-semibold uppercase tracking-[0.04em] text-text-tertiary">Custom host</span>
              <input
                value={customHost}
                onChange={(e) => setCustomHost(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') runAnalyze() }}
                placeholder="e.g. 1.1.1.1 or a game server"
                className="h-9 w-64 rounded-lg bg-surface-2 border border-border px-3 text-[13px] text-text
                  placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent/40"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-[10.5px] font-semibold uppercase tracking-[0.04em] text-text-tertiary">Probes</span>
              <select
                value={count}
                onChange={(e) => setCount(Number(e.target.value))}
                className="h-9 rounded-lg bg-surface-2 border border-border px-2 text-[13px] text-text focus:outline-none focus:ring-2 focus:ring-accent/40"
              >
                {[5, 10, 20, 40].map((n) => <option key={n} value={n}>{n}</option>)}
              </select>
            </label>
            <Button size="md" variant="primary" disabled={analyzing || !activeHost.trim()} onClick={runAnalyze}>
              {analyzing ? <Loader2 size={16} className="animate-spin" /> : <Activity size={16} />}
              {analyzing ? 'Measuring…' : 'Measure'}
            </Button>
          </div>
          {dnsServers && (
            <p className="text-[11.5px] text-text-tertiary mt-3">
              {dnsServers.ok && dnsServers.servers.length > 0
                ? `System DNS: ${dnsServers.servers.join(', ')}`
                : 'System DNS: unavailable'}
            </p>
          )}
        </Card>
      </motion.div>

      {/* Result metrics */}
      <motion.div variants={itemVariants}>
        <Card padding="lg">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-text flex items-center gap-2">
              <Activity size={16} className="text-accent" />
              Measurement
              {result && <span className="text-text-tertiary font-normal">— {result.target}</span>}
            </h2>
            {lat && <Badge variant={g.tone === 'default' ? 'default' : g.tone}>{g.label}</Badge>}
          </div>

          {analyzing && !lat ? (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-16 rounded-xl" />)}
            </div>
          ) : analyzeError ? (
            <div className="flex items-start gap-3">
              <CircleAlert size={16} className="text-red shrink-0 mt-0.5" />
              <div>
                <p className="text-[13px] text-text">Measurement failed</p>
                <p className="text-[12px] text-text-secondary mt-0.5">{analyzeError}</p>
                <p className="text-[12px] text-text-secondary mt-0.5">
                  Could not measure <span className="font-mono">{activeHost}</span>.
                </p>
              </div>
            </div>
          ) : lat && !lat.ok ? (
            <div className="flex items-start gap-3">
              <CircleAlert size={16} className="text-red shrink-0 mt-0.5" />
              <div>
                <p className="text-[13px] text-text">No reply from {lat.host}</p>
                <p className="text-[12px] text-text-secondary mt-0.5">{lat.error ?? 'The target did not answer the probes.'}</p>
                <p className="text-[11.5px] text-text-tertiary mt-2">
                  Values are left blank rather than shown as zero, because &ldquo;0 ms&rdquo; and &ldquo;no data&rdquo; are different things.
                </p>
              </div>
            </div>
          ) : lat ? (
            <>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <Metric label="Avg latency" value={lat.avg_ms} unit=" ms" tone={COLORS.latency} />
                <Metric label="Jitter (σ)" value={lat.jitter_ms} unit=" ms" tone={COLORS.jitter} />
                <Metric label="Packet loss" value={lat.packet_loss_pct} unit=" %" tone={lat.packet_loss_pct ? COLORS.loss : undefined} />
                <Metric label="Min / Max" value={lat.min_ms} unit={lat.max_ms != null ? ` / ${lat.max_ms} ms` : ' ms'} />
              </div>
              {lat.sub_ms && (
                <p className="text-[11.5px] text-text-tertiary mt-3">
                  Some replies were faster than 1 ms and are counted at 0.5 ms (the OS reports them as &ldquo;&lt;1ms&rdquo;).
                </p>
              )}
              {result?.methodology && (
                <p className="text-[11.5px] text-text-tertiary mt-3">
                  Jitter is the {result.methodology.jitter}. Packet loss is the {result.methodology.packet_loss}.
                </p>
              )}
              {/* DNS resolution diagnostics for the same target: a separate
                  measurement from the ICMP probes, so a hostname that fails to
                  resolve is distinguishable from a host that is simply down. */}
              {result?.dns && (
                <div className="mt-4 pt-3 border-t border-border" data-testid="dns-diagnostics">
                  <div className="flex items-center gap-2 mb-1.5">
                    <Globe size={13} className="text-accent" />
                    <span className="text-[11px] font-semibold uppercase tracking-[0.04em] text-text-tertiary">
                      DNS resolution
                    </span>
                  </div>
                  {result.dns.ok ? (
                    <p className="text-[12px] text-text-secondary">
                      <span className="font-mono text-text">{result.dns.host}</span>
                      {' '}resolves to{' '}
                      <span className="font-mono text-text">
                        {(result.dns.addresses ?? []).join(', ') || 'no addresses'}
                      </span>
                      {result.dns.resolve_ms != null && (
                        <span className="text-text-tertiary"> in {result.dns.resolve_ms} ms</span>
                      )}
                    </p>
                  ) : (
                    <p className="text-[12px] text-text-secondary">
                      <span className="font-mono text-text">{result.dns.host}</span>
                      {' '}&mdash; {result.dns.error ?? 'could not be resolved'}
                      <span className="text-text-tertiary">
                        {' '}(ICMP probes to an IP address can still succeed when DNS fails.)
                      </span>
                    </p>
                  )}
                </div>
              )}
            </>
          ) : (
            <div className="h-24 flex flex-col items-center justify-center text-center gap-1.5">
              <p className="text-sm text-text-secondary">No measurement yet</p>
              <p className="text-xs text-text-tertiary max-w-[46ch]">
                Pick a target and press Measure. Each probe is a real ICMP echo; nothing here is simulated.
              </p>
            </div>
          )}
        </Card>
      </motion.div>

      {/* Session latency chart */}
      {chartData.length > 1 && (
        <motion.div variants={itemVariants}>
          <Card padding="lg">
            <h2 className="text-sm font-semibold text-text flex items-center gap-2 mb-4">
              <Clock size={16} className="text-accent" />
              Session trend
            </h2>
            <div className="mt-1">
              <StreamArea
                series={trend.series}
                height={224}
                yMax={trend.yMax}
                guides={trend.guides}
                unit=" ms"
                labels={trend.labels}
                ariaLabel={`Session latency trend over ${chartData.length} measurements`}
              />
            </div>
            <div className="flex items-center gap-4 mt-3 pt-3 border-t border-border">
              <div className="flex items-center gap-1.5 text-[11px] text-text-secondary">
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: COLORS.latency }} /> Latency
              </div>
              <div className="flex items-center gap-1.5 text-[11px] text-text-secondary">
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: COLORS.jitter }} /> Jitter
              </div>
              <span className="text-[11px] text-text-tertiary ml-auto">Dashed line: 40 ms reference</span>
            </div>
          </Card>
        </motion.div>
      )}

      {/* Route trace */}
      <motion.div variants={itemVariants}>
        <Card padding="lg">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-text flex items-center gap-2">
              <Route size={16} className="text-accent" />
              Route trace
              {trace && <span className="text-text-tertiary font-normal">— {trace.hops.length} hops</span>}
            </h2>
            <Button size="sm" variant="secondary" disabled={tracing || !activeHost.trim()} onClick={runTrace}>
              {tracing ? <Loader2 size={14} className="animate-spin" /> : <Route size={14} />}
              {tracing ? 'Tracing…' : 'Trace route'}
            </Button>
          </div>
          {traceError ? (
            <p className="text-[12.5px] text-text-secondary">{traceError}</p>
          ) : tracing ? (
            <Skeleton className="h-40 w-full rounded-xl" />
          ) : trace && !trace.ok ? (
            <p className="text-[12.5px] text-text-secondary">{trace.error}</p>
          ) : trace && trace.hops.length > 0 ? (
            <ol className="space-y-1 max-h-72 overflow-y-auto pr-1">
              {trace.hops.map((hop, i) => (
                <li key={`${hop.ip}-${i}`} className="flex items-center gap-3 text-[12.5px] py-1 px-2 rounded-md hover:bg-surface-2">
                  <span className="w-6 text-right text-text-tertiary tnum">{i + 1}</span>
                  <span className="font-mono text-text w-40 truncate">{hop.ip}</span>
                  {hop.ok ? (
                    <span className="text-text-secondary tnum">{hop.avg_ms?.toFixed(1)} ms</span>
                  ) : (
                    <Badge variant="default">timed out</Badge>
                  )}
                </li>
              ))}
            </ol>
          ) : (
            <div className="h-24 flex flex-col items-center justify-center text-center gap-1.5">
              <p className="text-sm text-text-secondary">No trace yet</p>
              <p className="text-xs text-text-tertiary max-w-[46ch]">
                A trace shows each router between you and the target. It can take up to a minute on a slow path.
              </p>
            </div>
          )}
        </Card>
      </motion.div>

      {/* Session history */}
      {history.length > 0 && (
        <motion.div variants={itemVariants}>
          <Card padding="lg">
            <h2 className="text-sm font-semibold text-text mb-4">Session history</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-[12.5px]">
                <thead>
                  <tr className="text-left text-text-tertiary border-b border-border">
                    <th className="py-2 pr-4 font-medium">Time</th>
                    <th className="py-2 pr-4 font-medium">Target</th>
                    <th className="py-2 pr-4 font-medium text-right">Avg</th>
                    <th className="py-2 pr-4 font-medium text-right">Jitter</th>
                    <th className="py-2 font-medium text-right">Loss</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((h) => (
                    <tr key={h.ts} className="border-b border-border/50 last:border-0">
                      <td className="py-2 pr-4 text-text-secondary tnum">{formatChartTick(h.ts)}</td>
                      <td className="py-2 pr-4 text-text">{h.target}</td>
                      <td className="py-2 pr-4 text-right tnum">{h.avg_ms != null ? `${h.avg_ms} ms` : '--'}</td>
                      <td className="py-2 pr-4 text-right tnum">{h.jitter_ms != null ? `${h.jitter_ms} ms` : '--'}</td>
                      <td className="py-2 text-right tnum">{h.loss_pct != null ? `${h.loss_pct}%` : '--'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-[11px] text-text-tertiary mt-3">
              History lives in this session only and is cleared when the app closes.
            </p>
          </Card>
        </motion.div>
      )}
    </motion.div>
  )
}
