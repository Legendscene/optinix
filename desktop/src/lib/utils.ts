export function formatBytes(b: number): string {
  if (!b || b < 0) return '--'
  const k = 1024
  const s = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.min(Math.floor(Math.log(b) / Math.log(k)), s.length - 1)
  return `${parseFloat((b / Math.pow(k, i)).toFixed(1))} ${s[i]}`
}

export function formatSpeed(bps: number): string {
  if (!bps || bps < 1) return '0 B/s'
  return formatBytes(bps) + '/s'
}

export function formatUptime(seconds: number): string {
  const d = Math.floor(seconds / 86400)
  const h = Math.floor((seconds % 86400) / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (d > 0) return `${d}d ${h}h ${m}m`
  if (h > 0) return `${h}h ${m}m`
  return `${m}m`
}

export function healthScore(info: { cpu?: { percent: number }; memory?: { percent: number }; disk?: { percent: number } | { percent: number }[]; gpu?: { usage: number } }): { score: number; label: string; color: string } {
  const cpu = 100 - (info.cpu?.percent ?? 0)
  const mem = 100 - (info.memory?.percent ?? 0)
  const diskPct = Array.isArray(info.disk) ? info.disk[0]?.percent ?? 0 : info.disk?.percent ?? 0
  const dsk = 100 - diskPct
  const gpu = 100 - (info.gpu?.usage ?? 0)
  const avg = (cpu + mem + dsk + gpu) / 4
  const s = Math.round(avg)
  /* Tokens, not hexes: the score badge has to follow the light theme and the
     accent presets like every other surface in the app. */
  if (s >= 85) return { score: s, label: 'Excellent', color: 'var(--color-green)' }
  if (s >= 65) return { score: s, label: 'Good', color: 'var(--color-yellow)' }
  if (s >= 45) return { score: s, label: 'Fair', color: 'var(--color-yellow)' }
  return { score: s, label: 'Poor', color: 'var(--color-red)' }
}

export function cn(...classes: (string | false | undefined | null)[]): string {
  return classes.filter(Boolean).join(' ')
}

/** "just now", "4m ago", "3d ago". Returns null for missing or unparseable input. */
export function formatRelative(iso: string | number | null | undefined): string | null {
  if (iso == null || iso === '') return null
  const then = typeof iso === 'number' ? (iso < 1e12 ? iso * 1000 : iso) : Date.parse(iso)
  if (Number.isNaN(then)) return null
  const secs = Math.max(0, Math.round((Date.now() - then) / 1000))
  if (secs < 45) return 'just now'
  const mins = Math.round(secs / 60)
  if (mins < 60) return `${mins}m ago`
  const hours = Math.round(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.round(hours / 24)
  if (days < 30) return `${days}d ago`
  const months = Math.round(days / 30)
  if (months < 12) return `${months}mo ago`
  return `${Math.round(months / 12)}y ago`
}

export function formatDuration(ms: number | null | undefined): string {
  if (ms == null) return '--'
  if (ms < 1000) return `${Math.round(ms)}ms`
  const s = ms / 1000
  if (s < 60) return `${s.toFixed(1)}s`
  return `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`
}

/**
 * Chart axis label for a millisecond timestamp. Includes seconds because
 * monitor samples can be seconds apart; formatting to hour+minute alone
 * collapses distinct samples onto the same repeated label. The exact value is
 * still surfaced via the chart tooltip, which formats the same timestamp.
 */
export function formatChartTick(ts: number): string {
  return new Date(ts).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}
