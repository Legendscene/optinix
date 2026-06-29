import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  Settings,
  Palette,
  Image,
  Circle,
  SidebarClose,
  Sidebar,
  Monitor,
  Sun,
  Moon,
  Droplets,
  Trees,
  Sunset,
  Sparkles,
} from 'lucide-react'
import { Card } from '../ui/Card'
import { Skeleton } from '../ui/Skeleton'
import { cn } from '../../lib/utils'
import type { SystemInfo } from '../../types'

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.05 } },
}

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
}

const THEMES = [
  { id: 'dark', label: 'Dark', icon: <Moon size={16} />, cls: 'bg-surface-1 text-text border-border' },
  { id: 'midnight', label: 'Midnight', icon: <Moon size={16} />, cls: 'bg-[#0a0a1a] text-text border-[#1e1e3a]' },
  { id: 'purple', label: 'Purple', icon: <Sparkles size={16} />, cls: 'bg-[#0f0a1a] text-text border-[#2d1a4a]' },
  { id: 'ocean', label: 'Ocean', icon: <Droplets size={16} />, cls: 'bg-[#0a121a] text-text border-[#1a2a3a]' },
  { id: 'forest', label: 'Forest', icon: <Trees size={16} />, cls: 'bg-[#0a120a] text-text border-[#1a2a1a]' },
  { id: 'sunset', label: 'Sunset', icon: <Sunset size={16} />, cls: 'bg-[#1a100a] text-text border-[#3a2a1a]' },
  { id: 'glassy', label: 'Glassy', icon: <Monitor size={16} />, cls: 'bg-white/5 text-text backdrop-blur-xl border-white/10' },
  { id: 'neon', label: 'Neon', icon: <Sun size={16} />, cls: 'bg-[#0a0a0a] text-[#00ff88] border-[#00ff88]/30' },
]

const BACKGROUNDS = [
  { id: 'none', label: 'None', icon: <Circle size={16} /> },
  { id: 'gradient', label: 'Gradient', icon: <Sun size={16} /> },
  { id: 'mesh', label: 'Mesh', icon: <Sparkles size={16} /> },
  { id: 'particles', label: 'Particles', icon: <Circle size={16} /> },
]

const ACCENTS = [
  { id: '#7c3aed', label: 'Purple' },
  { id: '#3b82f6', label: 'Blue' },
  { id: '#06b6d4', label: 'Cyan' },
  { id: '#22c55e', label: 'Green' },
  { id: '#eab308', label: 'Yellow' },
  { id: '#f97316', label: 'Orange' },
  { id: '#ef4444', label: 'Red' },
  { id: '#ec4899', label: 'Pink' },
]

const SIDEBAR_MODES = [
  { id: 'compact', label: 'Compact', icon: <SidebarClose size={16} />, desc: 'Icons only' },
  { id: 'full', label: 'Full', icon: <Sidebar size={16} />, desc: 'Icons + labels' },
  { id: 'hidden', label: 'Hidden', icon: <Monitor size={16} />, desc: 'Auto hide' },
]

interface Preferences {
  theme: string
  background: string
  accent: string
  sidebarMode: string
}

const DEFAULTS: Preferences = {
  theme: 'dark',
  background: 'none',
  accent: '#7c3aed',
  sidebarMode: 'full',
}

function loadPrefs(): Preferences {
  try {
    const raw = localStorage.getItem('optinix-prefs')
    return raw ? { ...DEFAULTS, ...JSON.parse(raw) } : DEFAULTS
  } catch {
    return DEFAULTS
  }
}

function savePrefs(prefs: Preferences) {
  localStorage.setItem('optinix-prefs', JSON.stringify(prefs))
}

export function SettingsPage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const [prefs, setPrefs] = useState<Preferences>(DEFAULTS)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    setPrefs(loadPrefs())
    setReady(true)
  }, [])

  function update(key: keyof Preferences, value: string) {
    const next = { ...prefs, [key]: value }
    setPrefs(next)
    savePrefs(next)
  }

  if (!systemInfo || !ready) {
    return (
      <div className="space-y-6">
        <div><Skeleton className="h-8 w-40 mb-1" /><Skeleton className="h-4 w-64" /></div>
        {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-32 rounded-xl" />)}
      </div>
    )
  }

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-6">
      <motion.div variants={item}>
        <div className="flex items-center gap-3 mb-1">
          <Settings className="w-6 h-6 text-accent" />
          <h1 className="text-2xl font-bold tracking-tight text-text">Settings</h1>
        </div>
        <p className="text-sm text-text-secondary ml-9">Customize appearance and preferences</p>
      </motion.div>

      <motion.div variants={item}>
        <Card padding="lg">
          <div className="flex items-center gap-2 mb-4">
            <Palette className="w-5 h-5 text-accent" />
            <h2 className="text-sm font-semibold text-text">Theme</h2>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {THEMES.map(t => (
              <button
                key={t.id}
                onClick={() => update('theme', t.id)}
                className={cn(
                  'flex items-center gap-2 px-3 py-2.5 rounded-xl border text-sm font-medium transition-all',
                  t.cls,
                  prefs.theme === t.id
                    ? 'ring-2 ring-accent ring-offset-2 ring-offset-surface-0 scale-[1.02]'
                    : 'opacity-70 hover:opacity-100'
                )}
              >
                {t.icon}
                {t.label}
              </button>
            ))}
          </div>
        </Card>
      </motion.div>

      <motion.div variants={item}>
        <Card padding="lg">
          <div className="flex items-center gap-2 mb-4">
            <Image className="w-5 h-5 text-accent" />
            <h2 className="text-sm font-semibold text-text">Background</h2>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {BACKGROUNDS.map(b => (
              <button
                key={b.id}
                onClick={() => update('background', b.id)}
                className={cn(
                  'flex items-center gap-2 px-3 py-2.5 rounded-xl border border-border text-sm font-medium transition-all bg-surface-2',
                  prefs.background === b.id
                    ? 'ring-2 ring-accent ring-offset-2 ring-offset-surface-0 border-accent/50'
                    : 'hover:bg-surface-3'
                )}
              >
                {b.icon}
                {b.label}
              </button>
            ))}
          </div>
        </Card>
      </motion.div>

      <motion.div variants={item}>
        <Card padding="lg">
          <div className="flex items-center gap-2 mb-4">
            <Circle className="w-5 h-5 text-accent" />
            <h2 className="text-sm font-semibold text-text">Accent Color</h2>
          </div>
          <div className="flex flex-wrap gap-3">
            {ACCENTS.map(a => (
              <button
                key={a.id}
                onClick={() => update('accent', a.id)}
                className={cn(
                  'relative w-10 h-10 rounded-full transition-all',
                  prefs.accent === a.id && 'ring-2 ring-white ring-offset-2 ring-offset-surface-0 scale-110'
                )}
                style={{ backgroundColor: a.id }}
                title={a.label}
              >
                {prefs.accent === a.id && (
                  <span className="absolute inset-0 flex items-center justify-center">
                    <span className="w-2 h-2 rounded-full bg-white" />
                  </span>
                )}
              </button>
            ))}
          </div>
        </Card>
      </motion.div>

      <motion.div variants={item}>
        <Card padding="lg">
          <div className="flex items-center gap-2 mb-4">
            <Sidebar className="w-5 h-5 text-accent" />
            <h2 className="text-sm font-semibold text-text">Sidebar Mode</h2>
          </div>
          <div className="grid grid-cols-3 gap-2">
            {SIDEBAR_MODES.map(m => (
              <button
                key={m.id}
                onClick={() => update('sidebarMode', m.id)}
                className={cn(
                  'flex flex-col items-center gap-1.5 px-3 py-3 rounded-xl border text-sm font-medium transition-all bg-surface-2',
                  prefs.sidebarMode === m.id
                    ? 'ring-2 ring-accent ring-offset-2 ring-offset-surface-0 border-accent/50'
                    : 'border-border hover:bg-surface-3'
                )}
              >
                {m.icon}
                <span className="text-text">{m.label}</span>
                <span className="text-[10px] text-text-tertiary">{m.desc}</span>
              </button>
            ))}
          </div>
        </Card>
      </motion.div>
    </motion.div>
  )
}
