import { useState, useEffect, useMemo } from 'react'
import { motion } from 'framer-motion'
import { Area, AreaChart, ResponsiveContainer } from 'recharts'
import {
  Cpu, Monitor, MemoryStick as MemoryIcon, HardDrive, Wifi,
  Gauge, Zap, Gamepad2, Eraser, Sparkles, Shield,
  Clock, Activity, AlertCircle, CheckCircle2, Rocket,
} from 'lucide-react'
import { Card } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { ProgressBar } from '../ui/ProgressBar'
import { Skeleton } from '../ui/Skeleton'
import { MiniChart } from '../ui/MiniChart'
import { cn, healthScore, formatBytes, formatSpeed } from '../../lib/utils'
import { api } from '../../lib/api'
import type { SystemInfo, SmartDetect } from '../../types'

export function Dashboard({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const [smartDetect, setSmartDetect] = useState<SmartDetect | null>(null)
  const [loadingSmart, setLoadingSmart] = useState(true)
  const [activeAction, setActiveAction] = useState<string | null>(null)
  const [actionResult, setActionResult] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/smart-detect')
      .then(r => r.json())
      .then(d => { setSmartDetect(d); setLoadingSmart(false) })
      .catch(() => setLoadingSmart(false))
  }, [])

  const actionHandlers: Record<string, () => Promise<Record<string, unknown>>> = {
    'Optimize Everything': () => api.optimizeAll(),
    'Game Mode': () => api.gameModeEnable() as Promise<Record<string, unknown>>,
    'RAM Boost': () => api.ramBoost(),
    'Disk Clean': () => api.optimize('disk') as Promise<Record<string, unknown>>,
    'Internet Boost': () => api.optimize('network') as Promise<Record<string, unknown>>,
    'Extreme Mode': () => api.extreme() as Promise<Record<string, unknown>>,
  }

  const performAction = async (name: string) => {
    setActiveAction(name)
    setActionResult(null)
    try {
      const d = await actionHandlers[name]()
      setActionResult(`${name}|||${(d.message as string) || 'Completed'}`)
    } catch {
      setActionResult(`${name}|||Failed`)
    }
    setActiveAction(null)
  }

  const sparkCpu = useMemo(() => Array.from({ length: 20 }, () => Math.floor(Math.random() * 100)), [])
  const sparkGpu = useMemo(() => Array.from({ length: 20 }, () => Math.floor(Math.random() * 100)), [])
  const sparkRam = useMemo(() => Array.from({ length: 20 }, () => Math.floor(Math.random() * 100)), [])
  const sparkVram = useMemo(() => Array.from({ length: 20 }, () => Math.floor(Math.random() * 100)), [])
  const sparkDisk = useMemo(() => Array.from({ length: 20 }, () => Math.floor(Math.random() * 100)), [])
  const sparkNet = useMemo(() => Array.from({ length: 20 }, () => Math.floor(Math.random() * 100)), [])

  const trendData = useMemo(() =>
    Array.from({ length: 24 }, (_, i) => ({
      time: `${i}:00`,
      cpu: Math.floor(Math.random() * 50 + 20),
      ram: Math.floor(Math.random() * 40 + 30),
      gpu: Math.floor(Math.random() * 60 + 10)
    })), [])

  const recIcons: Record<string, React.ReactNode> = {
    performance: <Zap size={16} />,
    disk: <HardDrive size={16} />,
    memory: <MemoryIcon size={16} />,
    network: <Wifi size={16} />,
    security: <Shield size={16} />,
    tweak: <Sparkles size={16} />,
    driver: <Monitor size={16} />
  }

  const priorityVariant: Record<string, 'warning' | 'danger' | 'info' | 'accent'> = {
    high: 'danger',
    medium: 'warning',
    low: 'info'
  }

  const actions = [
    { name: 'Optimize Everything', desc: 'Run full system optimization sweep', icon: <Zap size={20} />, variant: 'default' as const },
    { name: 'Game Mode', desc: 'Maximize gaming performance', icon: <Gamepad2 size={20} />, variant: 'success' as const },
    { name: 'RAM Boost', desc: 'Free up memory instantly', icon: <MemoryIcon size={20} />, variant: 'default' as const },
    { name: 'Disk Clean', desc: 'Remove junk & temporary files', icon: <Eraser size={20} />, variant: 'danger' as const },
    { name: 'Internet Boost', desc: 'Optimize network settings', icon: <Wifi size={20} />, variant: 'default' as const },
    { name: 'Extreme Mode', desc: 'Unlock maximum performance', icon: <Rocket size={20} />, variant: 'success' as const },
  ]

  const actionVariantBg: Record<string, string> = {
    default: 'border-border hover:border-accent/50',
    danger: 'border-red/30 hover:border-red/60',
    success: 'border-green/30 hover:border-green/60',
  }

  const actionIconVariant: Record<string, string> = {
    default: 'text-accent',
    danger: 'text-red',
    success: 'text-green',
  }

  if (!systemInfo) {
    return (
      <div className="space-y-6 p-6 max-w-7xl mx-auto">
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-4 w-72" />
          </div>
          <Skeleton variant="circular" className="h-32 w-32" />
        </div>
        <Card padding="lg">
          <div className="space-y-3">
            <Skeleton className="h-5 w-40" />
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-3/4" />
          </div>
        </Card>
        <Skeleton className="h-6 w-36" />
        <div className="grid grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} variant="rectangular" className="h-32 w-full" />
          ))}
        </div>
        <Skeleton variant="rectangular" className="h-52 w-full" />
        <Skeleton variant="rectangular" className="h-40 w-full" />
      </div>
    )
  }

  const health = healthScore({
    cpu: systemInfo.cpu,
    memory: systemInfo.memory,
    gpu: { usage: systemInfo.gpu.usage },
    disk: { percent: systemInfo.disk[0]?.percent ?? 0 }
  })

  const circumference = 2 * Math.PI * 52
  const disk = systemInfo.disk[0]
  const resultName = actionResult?.split('|||')[0]
  const resultMsg = actionResult?.split('|||')[1]

  return (
    <div className="space-y-6 p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text flex items-center gap-3">
            <Gauge className="text-accent" size={28} />
            Dashboard
          </h1>
          <p className="text-sm text-text-secondary mt-1">
            {systemInfo.os.os_name} {systemInfo.os.release} &mdash; {systemInfo.system.processor}
          </p>
        </div>
        <div className="relative flex items-center justify-center shrink-0" style={{ width: 130, height: 130 }}>
          <svg width="130" height="130" viewBox="0 0 130 130" className="absolute inset-0">
            <circle cx="65" cy="65" r="52" fill="none" stroke="currentColor" strokeWidth="8" className="text-surface-3" />
            <motion.circle
              cx="65" cy="65" r="52"
              fill="none"
              stroke={health.color}
              strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray={circumference}
              initial={{ strokeDashoffset: circumference }}
              animate={{ strokeDashoffset: circumference * (1 - health.score / 100) }}
              transition={{ duration: 1.5, ease: 'easeOut' }}
              transform="rotate(-90 65 65)"
              style={{ filter: `drop-shadow(0 0 6px ${health.color}40)` }}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <motion.span
              initial={{ opacity: 0, scale: 0.5 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.8, type: 'spring', stiffness: 200 }}
              className="text-2xl font-bold"
              style={{ color: health.color }}
            >
              {health.score}
            </motion.span>
            <span className="text-[10px] text-text-tertiary -mt-0.5">/ 100</span>
            <span className="text-[11px] font-medium mt-0.5" style={{ color: health.color }}>{health.label}</span>
          </div>
        </div>
      </div>

      <Card padding="lg" glass>
        <div className="flex items-center gap-2 mb-4">
          <Sparkles size={18} className="text-accent" />
          <h2 className="text-sm font-semibold text-text">AI Recommendations</h2>
          {loadingSmart && (
            <div className="ml-auto flex items-center gap-2">
              <div className="animate-spin h-3 w-3 border-2 border-accent border-t-transparent rounded-full" />
              <span className="text-[11px] text-text-tertiary">Scanning system...</span>
            </div>
          )}
        </div>
        {loadingSmart ? (
          <div className="space-y-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="flex items-center gap-3 p-2.5 rounded-xl bg-surface-2/40 animate-pulse">
                <Skeleton variant="circular" className="h-8 w-8" />
                <Skeleton className="h-4 flex-1" />
                <Skeleton className="h-5 w-14 rounded-md" />
              </div>
            ))}
          </div>
        ) : smartDetect?.recommendations?.length ? (
          <div className="space-y-2">
            {smartDetect.recommendations.slice(0, 4).map((rec, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className="flex items-center gap-3 p-2.5 rounded-xl bg-surface-2/60 hover:bg-surface-2 transition-colors"
              >
                <div className="p-1.5 rounded-lg bg-surface-3 text-accent shrink-0">
                  {recIcons[rec.type] ?? <AlertCircle size={16} />}
                </div>
                <p className="text-xs text-text-secondary flex-1 leading-relaxed">{rec.message}</p>
                <Badge variant={priorityVariant[rec.priority] ?? 'default'}>{rec.priority}</Badge>
              </motion.div>
            ))}
            {smartDetect.recommendations.length > 4 && (
              <p className="text-[11px] text-text-tertiary text-center pt-1 border-t border-border mt-2">
                +{smartDetect.recommendations.length - 4} more recommendation{smartDetect.recommendations.length - 4 > 1 ? 's' : ''}
              </p>
            )}
          </div>
        ) : (
          <div className="flex items-center gap-2 py-2">
            <CheckCircle2 size={16} className="text-green shrink-0" />
            <span className="text-xs text-text-secondary">System is in great shape — no recommendations at this time.</span>
          </div>
        )}
      </Card>

      <div>
        <h2 className="text-sm font-semibold text-text mb-3 flex items-center gap-2">
          <Activity size={16} className="text-accent" />
          Live Resources
        </h2>
        <div className="grid grid-cols-3 gap-4">
          <Card hover padding="md" className="relative overflow-hidden">
            <div className="flex items-start justify-between mb-3">
              <div className="p-2 rounded-lg bg-surface-2 text-accent">
                <Cpu size={18} />
              </div>
              <MiniChart data={sparkCpu} color="#7c3aed" />
            </div>
            <div className="text-2xl font-semibold tracking-tight text-text">{systemInfo.cpu.percent}%</div>
            <div className="text-xs text-text-secondary mt-0.5">CPU Usage</div>
            <ProgressBar value={systemInfo.cpu.percent} className="mt-2" size="sm" />
            <div className="text-[11px] text-text-tertiary mt-1">
              {systemInfo.cpu.temperature != null ? `${systemInfo.cpu.temperature}°C · ` : ''}{systemInfo.cpu.physical}C / {systemInfo.cpu.logical}T
            </div>
          </Card>

          <Card hover padding="md" className="relative overflow-hidden">
            <div className="flex items-start justify-between mb-3">
              <div className="p-2 rounded-lg bg-surface-2 text-[#f59e0b]">
                <Monitor size={18} />
              </div>
              <MiniChart data={sparkGpu} color="#f59e0b" />
            </div>
            <div className="text-2xl font-semibold tracking-tight text-text">{systemInfo.gpu.usage}%</div>
            <div className="text-xs text-text-secondary mt-0.5">GPU Usage</div>
            <ProgressBar value={systemInfo.gpu.usage} className="mt-2" size="sm" color="#f59e0b" />
            <div className="text-[11px] text-text-tertiary mt-1">
              {systemInfo.gpu.name ? systemInfo.gpu.name.split(' ').slice(0, 2).join(' ') : 'GPU'} &middot; {systemInfo.gpu.temperature}°C
            </div>
          </Card>

          <Card hover padding="md" className="relative overflow-hidden">
            <div className="flex items-start justify-between mb-3">
              <div className="p-2 rounded-lg bg-surface-2 text-[#06b6d4]">
                <MemoryIcon size={18} />
              </div>
              <MiniChart data={sparkRam} color="#06b6d4" />
            </div>
            <div className="text-2xl font-semibold tracking-tight text-text">
              {systemInfo.memory.used_gb.toFixed(1)}
              <span className="text-sm text-text-tertiary font-normal"> / {systemInfo.memory.total_gb} GB</span>
            </div>
            <div className="text-xs text-text-secondary mt-0.5">RAM Usage</div>
            <ProgressBar value={systemInfo.memory.percent} className="mt-2" size="sm" />
            <div className="text-[11px] text-text-tertiary mt-1">{formatBytes(systemInfo.memory.available_gb * 1073741824)} available</div>
          </Card>

          <Card hover padding="md" className="relative overflow-hidden">
            <div className="flex items-start justify-between mb-3">
              <div className="p-2 rounded-lg bg-surface-2 text-[#8b5cf6]">
                <MemoryIcon size={18} />
              </div>
              <MiniChart data={sparkVram} color="#8b5cf6" />
            </div>
            <div className="text-2xl font-semibold tracking-tight text-text">
              {systemInfo.gpu.memory_used}
              <span className="text-sm text-text-tertiary font-normal"> / {systemInfo.gpu.memory_total} GB</span>
            </div>
            <div className="text-xs text-text-secondary mt-0.5">VRAM</div>
            <ProgressBar
              value={systemInfo.gpu.memory_total ? (systemInfo.gpu.memory_used / systemInfo.gpu.memory_total) * 100 : 0}
              className="mt-2"
              size="sm"
              color="#8b5cf6"
            />
            <div className="text-[11px] text-text-tertiary mt-1">{systemInfo.gpu.driver || systemInfo.gpu.name}</div>
          </Card>

          <Card hover padding="md" className="relative overflow-hidden">
            <div className="flex items-start justify-between mb-3">
              <div className="p-2 rounded-lg bg-surface-2 text-[#10b981]">
                <HardDrive size={18} />
              </div>
              <MiniChart data={sparkDisk} color="#10b981" />
            </div>
            {disk ? (
              <>
                <div className="text-2xl font-semibold tracking-tight text-text">
                  {formatBytes(disk.used)}
                  <span className="text-sm text-text-tertiary font-normal"> / {formatBytes(disk.total)}</span>
                </div>
                <div className="text-xs text-text-secondary mt-0.5">{disk.mountpoint} &middot; {disk.device}</div>
                <ProgressBar value={disk.percent} className="mt-2" size="sm" />
                <div className="text-[11px] text-text-tertiary mt-1">
                  {disk.fstype.toUpperCase()} &middot; {disk.is_ssd ? 'SSD' : disk.is_ssd === false ? 'HDD' : 'Drive'}
                </div>
              </>
            ) : (
              <div className="text-sm text-text-tertiary py-4">No disk data available</div>
            )}
          </Card>

          <Card hover padding="md" className="relative overflow-hidden">
            <div className="flex items-start justify-between mb-3">
              <div className="p-2 rounded-lg bg-surface-2 text-[#3b82f6]">
                <Wifi size={18} />
              </div>
              <MiniChart data={sparkNet} color="#3b82f6" />
            </div>
            <div className="text-2xl font-semibold tracking-tight text-text">{formatSpeed(systemInfo.network.speed_down)}</div>
            <div className="text-xs text-text-secondary mt-0.5">Download Speed</div>
            <div className="flex items-center gap-3 mt-2">
              <div className="flex-1 space-y-0.5">
                <div className="flex justify-between text-[11px] text-text-tertiary">
                  <span>↓ Down</span>
                  <span>{formatSpeed(systemInfo.network.speed_down)}</span>
                </div>
                <div className="flex justify-between text-[11px] text-text-tertiary">
                  <span>↑ Up</span>
                  <span>{formatSpeed(systemInfo.network.speed_up)}</span>
                </div>
              </div>
            </div>
            <div className="text-[11px] text-text-tertiary mt-1">
              {formatBytes(systemInfo.network.bytes_recv)} received
            </div>
          </Card>
        </div>
      </div>

      <Card padding="lg" glass>
        <div className="flex items-center gap-2 mb-4">
          <Activity size={16} className="text-accent" />
          <h2 className="text-sm font-semibold text-text">Performance Trend</h2>
          <span className="text-[10px] text-text-tertiary ml-auto">Last 24 hours</span>
        </div>
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={trendData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="cpuGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#7c3aed" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#7c3aed" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="ramGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#06b6d4" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#06b6d4" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gpuGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#f59e0b" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#f59e0b" stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area type="monotone" dataKey="cpu" stroke="#7c3aed" strokeWidth={2} fill="url(#cpuGrad)" />
              <Area type="monotone" dataKey="ram" stroke="#06b6d4" strokeWidth={2} fill="url(#ramGrad)" />
              <Area type="monotone" dataKey="gpu" stroke="#f59e0b" strokeWidth={2} fill="url(#gpuGrad)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <div className="flex items-center gap-4 mt-3 pt-3 border-t border-border">
          {[{ label: 'CPU', color: '#7c3aed' }, { label: 'RAM', color: '#06b6d4' }, { label: 'GPU', color: '#f59e0b' }].map(item => (
            <div key={item.label} className="flex items-center gap-1.5 text-[11px] text-text-secondary">
              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: item.color }} />
              {item.label}
            </div>
          ))}
        </div>
      </Card>

      <div>
        <h2 className="text-sm font-semibold text-text mb-3 flex items-center gap-2">
          <Zap size={16} className="text-accent" />
          Quick Actions
        </h2>
        <div className="grid grid-cols-3 gap-4">
          {actions.map((action) => (
            <div key={action.name} className="relative">
              <motion.div
                whileHover={activeAction ? undefined : { y: -3, boxShadow: '0 12px 40px rgba(0,0,0,0.4)' }}
                transition={{ type: 'spring', stiffness: 300, damping: 20 }}
                onClick={() => !activeAction && performAction(action.name)}
                className={cn(
                  'relative rounded-2xl border bg-surface-1 p-5 cursor-pointer group transition-all duration-200',
                  'hover:shadow-lg',
                  activeAction === action.name
                    ? 'opacity-60 pointer-events-none border-accent/40'
                    : actionVariantBg[action.variant],
                )}
              >
                <div className="flex items-start gap-4">
                  <div className={cn(
                    'p-3 rounded-xl bg-surface-2 shrink-0 transition-colors',
                    activeAction === action.name ? 'text-accent' : actionIconVariant[action.variant],
                    activeAction === action.name && 'animate-pulse'
                  )}>
                    {activeAction === action.name ? (
                      <svg className="animate-spin" width="20" height="20" viewBox="0 0 24 24" fill="none">
                        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25" />
                        <path d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" fill="currentColor" className="opacity-75" />
                      </svg>
                    ) : action.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-semibold text-text group-hover:text-accent transition-colors">
                      {action.name}
                    </h3>
                    <p className="text-xs text-text-secondary mt-1 leading-relaxed">{action.desc}</p>
                    {activeAction === action.name && (
                      <span className="inline-flex items-center gap-1.5 mt-2 text-[11px] text-accent font-medium">
                        <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24" fill="none">
                          <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25" />
                          <path d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" fill="currentColor" className="opacity-75" />
                        </svg>
                        Running...
                      </span>
                    )}
                    {resultName === action.name && !activeAction && (
                      <motion.span
                        initial={{ opacity: 0, y: 4 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="inline-flex items-center gap-1 mt-2 text-[11px] text-green font-medium"
                      >
                        <CheckCircle2 size={12} />
                        {resultMsg || 'Completed'}
                      </motion.span>
                    )}
                  </div>
                </div>
              </motion.div>
            </div>
          ))}
        </div>
      </div>

      <Card padding="lg">
        <div className="flex items-center gap-2 mb-4">
          <Clock size={16} className="text-accent" />
          <h2 className="text-sm font-semibold text-text">System Information</h2>
        </div>
        <div className="grid grid-cols-3 gap-6">
          <div>
            <span className="text-[11px] text-text-tertiary uppercase tracking-wider font-medium">Operating System</span>
            <p className="text-sm text-text mt-1">{systemInfo.os.os_name} {systemInfo.os.release}</p>
          </div>
          <div>
            <span className="text-[11px] text-text-tertiary uppercase tracking-wider font-medium">Processor</span>
            <p className="text-sm text-text mt-1 truncate" title={systemInfo.system.processor}>{systemInfo.system.processor}</p>
          </div>
          <div>
            <span className="text-[11px] text-text-tertiary uppercase tracking-wider font-medium">Uptime</span>
            <p className="text-sm text-text mt-1">{systemInfo.system.uptime}</p>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-6 mt-4 pt-4 border-t border-border">
          <div>
            <span className="text-[11px] text-text-tertiary uppercase tracking-wider font-medium">Total Memory</span>
            <p className="text-sm text-text mt-1">{systemInfo.memory.total_gb} GB</p>
          </div>
          <div>
            <span className="text-[11px] text-text-tertiary uppercase tracking-wider font-medium">GPU</span>
            <p className="text-sm text-text mt-1 truncate" title={systemInfo.gpu.name}>{systemInfo.gpu.name || 'Not detected'}</p>
          </div>
          <div>
            <span className="text-[11px] text-text-tertiary uppercase tracking-wider font-medium">Disk</span>
            <p className="text-sm text-text mt-1">
              {disk ? `${formatBytes(disk.total)} · ${disk.is_ssd ? 'SSD' : disk.is_ssd === false ? 'HDD' : 'Drive'}` : 'N/A'}
            </p>
          </div>
        </div>
      </Card>
    </div>
  )
}
