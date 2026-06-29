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
  if (s >= 85) return { score: s, label: 'Excellent', color: '#22c55e' }
  if (s >= 65) return { score: s, label: 'Good', color: '#eab308' }
  if (s >= 45) return { score: s, label: 'Fair', color: '#f97316' }
  return { score: s, label: 'Poor', color: '#ef4444' }
}

export function cn(...classes: (string | false | undefined | null)[]): string {
  return classes.filter(Boolean).join(' ')
}
