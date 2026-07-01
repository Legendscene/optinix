import { motion } from 'framer-motion'
import {
  Settings, Palette, Image, Circle, SidebarClose, Sidebar, Monitor,
  Sun, Moon, Droplets, Trees, Sunset, Sparkles, Video, Wind, Blend,
  Droplet, Eye,
} from 'lucide-react'
import { Card } from '../ui/Card'
import { Skeleton } from '../ui/Skeleton'
import { cn } from '../../lib/utils'
import { usePreferences } from '../../contexts/PreferencesContext'
import type { SystemInfo } from '../../types'

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.05 } } }
const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }

const THEMES = [
  { id: 'dark', label: 'Dark', icon: <Moon size={16} />, cls: 'bg-surface-1 text-text border-border' },
  { id: 'midnight', label: 'Midnight', icon: <Moon size={16} />, cls: 'bg-[#0a0a1a] text-text border-[#1e1e3a]' },
  { id: 'purple', label: 'Purple', icon: <Sparkles size={16} />, cls: 'bg-[#0f0a1a] text-text border-[#2d1a4a]' },
  { id: 'ocean', label: 'Ocean', icon: <Droplets size={16} />, cls: 'bg-[#0a121a] text-text border-[#1a2a3a]' },
  { id: 'forest', label: 'Forest', icon: <Trees size={16} />, cls: 'bg-[#0a120a] text-text border-[#1a2a1a]' },
  { id: 'sunset', label: 'Sunset', icon: <Sunset size={16} />, cls: 'bg-[#1a100a] text-text border-[#3a2a1a]' },
  { id: 'glassy', label: 'Glassy', icon: <Eye size={16} />, cls: 'bg-white/5 text-text backdrop-blur-xl border-white/10' },
  { id: 'neon', label: 'Neon', icon: <Sun size={16} />, cls: 'bg-[#0a0a0a] text-[#00ff88] border-[#00ff88]/30' },
]

const BACKGROUNDS = [
  { id: 'none', label: 'None', icon: <Circle size={16} />, desc: 'Solid color' },
  { id: 'gradient', label: 'Gradient', icon: <Sun size={16} />, desc: 'Accent gradient' },
  { id: 'image', label: 'Image', icon: <Image size={16} />, desc: 'Custom image URL' },
  { id: 'video', label: 'Video', icon: <Video size={16} />, desc: 'MP4 video background' },
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

export function SettingsPage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const { prefs, update } = usePreferences()

  if (!systemInfo) {
    return (
      <div className="space-y-6">
        <div><Skeleton className="h-8 w-40 mb-1" /><Skeleton className="h-4 w-64" /></div>
        {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-32 rounded-xl" />)}
      </div>
    )
  }

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-6">
      <motion.div variants={item}>
        <div className="flex items-center gap-3 mb-1">
          <Settings className="w-6 h-6" style={{ color: prefs.accent }} />
          <h1 className="text-2xl font-bold tracking-tight text-text">Settings</h1>
        </div>
        <p className="text-sm text-text-secondary ml-9">Customize appearance, backgrounds, and effects</p>
      </motion.div>

      <motion.div variants={item}>
        <Card padding="lg">
          <div className="flex items-center gap-2 mb-4">
            <Palette className="w-5 h-5" style={{ color: prefs.accent }} />
            <h2 className="text-sm font-semibold text-text">Theme</h2>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {THEMES.map(t => (
              <button key={t.id} onClick={() => update('theme', t.id)}
                className={cn('flex items-center gap-2 px-3 py-2.5 rounded-xl border text-sm font-medium transition-all', t.cls,
                  prefs.theme === t.id ? 'ring-2 ring-offset-2 ring-offset-surface-0 scale-[1.02]' : 'opacity-70 hover:opacity-100'
                )}
                style={prefs.theme === t.id ? { borderColor: prefs.accent } : {}}
              >
                {t.icon}{t.label}
              </button>
            ))}
          </div>
        </Card>
      </motion.div>

      <motion.div variants={item}>
        <Card padding="lg">
          <div className="flex items-center gap-2 mb-4">
            <Image className="w-5 h-5" style={{ color: prefs.accent }} />
            <h2 className="text-sm font-semibold text-text">Background</h2>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-4">
            {BACKGROUNDS.map(b => (
              <button key={b.id} onClick={() => update('background', b.id)}
                className={cn('flex flex-col items-center gap-1 px-3 py-3 rounded-xl border text-sm font-medium transition-all',
                  prefs.background === b.id ? 'border-accent/50 ring-2 ring-offset-2 ring-offset-surface-0' : 'border-border bg-surface-2 hover:bg-surface-3'
                )}
                style={prefs.background === b.id ? { borderColor: `${prefs.accent}80` } : {}}
              >
                {b.icon}<span className="text-text">{b.label}</span>
                <span className="text-[10px] text-text-tertiary">{b.desc}</span>
              </button>
            ))}
          </div>
          {(prefs.background === 'image' || prefs.background === 'video') && (
            <div>
              <label className="text-xs text-text-secondary mb-1.5 block">
                {prefs.background === 'image' ? 'Image URL' : 'Video URL (MP4)'}
              </label>
              <input
                type="text"
                value={prefs.bgUrl}
                onChange={e => update('bgUrl', e.target.value)}
                placeholder={prefs.background === 'image' ? 'https://example.com/background.jpg' : 'https://example.com/background.mp4'}
                className="w-full px-3 py-2 rounded-lg bg-surface-2 border border-border text-sm text-text placeholder:text-text-tertiary outline-none focus:border-accent/50 transition-colors"
              />
            </div>
          )}
        </Card>
      </motion.div>

      <motion.div variants={item}>
        <Card padding="lg">
          <div className="flex items-center gap-2 mb-4">
            <Circle className="w-5 h-5" style={{ color: prefs.accent }} />
            <h2 className="text-sm font-semibold text-text">Accent Color</h2>
          </div>
          <div className="flex flex-wrap gap-3">
            {ACCENTS.map(a => (
              <button key={a.id} onClick={() => update('accent', a.id)}
                className={cn('relative w-10 h-10 rounded-full transition-all',
                  prefs.accent === a.id && 'ring-2 ring-white ring-offset-2 ring-offset-surface-0 scale-110'
                )}
                style={{ backgroundColor: a.id }} title={a.label}
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
            <Blend className="w-5 h-5" style={{ color: prefs.accent }} />
            <h2 className="text-sm font-semibold text-text">Visual Effects</h2>
          </div>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Wind className="w-4 h-4 text-text-secondary" />
                <span className="text-sm text-text">Glass Effect</span>
              </div>
              <button
                onClick={() => update('glassEffect', !prefs.glassEffect)}
                className={cn('w-10 h-5 rounded-full transition-colors relative', prefs.glassEffect ? 'bg-accent' : 'bg-surface-4')}
              >
                <span className={cn('absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform', prefs.glassEffect ? 'translate-x-[22px]' : 'translate-x-0.5')} />
              </button>
            </div>
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2">
                  <Droplet className="w-4 h-4 text-text-secondary" />
                  <span className="text-sm text-text">Background Opacity</span>
                </div>
                <span className="text-xs font-mono text-text-secondary">{prefs.bgOpacity}%</span>
              </div>
              <input type="range" min="10" max="100" value={prefs.bgOpacity}
                onChange={e => update('bgOpacity', parseInt(e.target.value))}
                className="w-full h-1.5 rounded-full appearance-none cursor-pointer bg-surface-3 accent-[var(--accent-color)]"
                style={{ accentColor: prefs.accent }}
              />
              <div className="flex justify-between text-[10px] text-text-tertiary mt-0.5"><span>Transparent</span><span>Opaque</span></div>
            </div>
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2">
                  <Wind className="w-4 h-4 text-text-secondary" />
                  <span className="text-sm text-text">Blur Intensity</span>
                </div>
                <span className="text-xs font-mono text-text-secondary">{prefs.blurIntensity}px</span>
              </div>
              <input type="range" min="0" max="50" value={prefs.blurIntensity}
                onChange={e => update('blurIntensity', parseInt(e.target.value))}
                className="w-full h-1.5 rounded-full appearance-none cursor-pointer bg-surface-3"
                style={{ accentColor: prefs.accent }}
              />
              <div className="flex justify-between text-[10px] text-text-tertiary mt-0.5"><span>Sharp</span><span>Max Blur</span></div>
            </div>
          </div>
        </Card>
      </motion.div>

      <motion.div variants={item}>
        <Card padding="lg">
          <div className="flex items-center gap-2 mb-4">
            <Sidebar className="w-5 h-5" style={{ color: prefs.accent }} />
            <h2 className="text-sm font-semibold text-text">Sidebar Mode</h2>
          </div>
          <div className="grid grid-cols-3 gap-2">
            {SIDEBAR_MODES.map(m => (
              <button key={m.id} onClick={() => update('sidebarMode', m.id)}
                className={cn('flex flex-col items-center gap-1.5 px-3 py-3 rounded-xl border text-sm font-medium transition-all bg-surface-2',
                  prefs.sidebarMode === m.id ? 'ring-2 ring-offset-2 ring-offset-surface-0' : 'border-border hover:bg-surface-3'
                )}
                style={prefs.sidebarMode === m.id ? { borderColor: `${prefs.accent}80` } : {}}
              >
                {m.icon}<span className="text-text">{m.label}</span>
                <span className="text-[10px] text-text-tertiary">{m.desc}</span>
              </button>
            ))}
          </div>
        </Card>
      </motion.div>
    </motion.div>
  )
}
