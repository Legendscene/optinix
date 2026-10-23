import { motion } from 'framer-motion'
import { useRef } from 'react'
import {
  Settings, Palette, Image, Circle, SidebarClose, Sidebar, Monitor,
  Sun, Moon, Droplets, Trees, Sunset, Sparkles, Video, Wind, Blend,
  Droplet, Eye, FileUp, Zap, Pause, Activity,
} from 'lucide-react'
import { Card } from '../ui/Card'
import { PageHero } from '../ui/PageHero'
import { Skeleton } from '../ui/Skeleton'
import { cn } from '../../lib/utils'
import { usePreferences } from '../../contexts/PreferencesContext'
import type { SystemInfo } from '../../types'

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.05 } } }
const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }

/* Theme chips preview their own palette, so their label colour is fixed to
   that palette instead of the app's ink — otherwise "Midnight" turns into
   dark-on-dark the moment the app itself is in light mode. */
const THEMES = [
  { id: 'dark', label: 'Dark', icon: <Moon size={16} />, cls: 'bg-surface-1 text-text border-border' },
  { id: 'midnight', label: 'Midnight', icon: <Moon size={16} />, cls: 'bg-[#0a0a1a] text-white/85 border-[#1e1e3a]' },
  { id: 'purple', label: 'Purple', icon: <Sparkles size={16} />, cls: 'bg-[#0f0a1a] text-white/85 border-[#2d1a4a]' },
  { id: 'ocean', label: 'Ocean', icon: <Droplets size={16} />, cls: 'bg-[#0a121a] text-white/85 border-[#1a2a3a]' },
  { id: 'forest', label: 'Forest', icon: <Trees size={16} />, cls: 'bg-[#0a120a] text-white/85 border-[#1a2a1a]' },
  { id: 'sunset', label: 'Sunset', icon: <Sunset size={16} />, cls: 'bg-[#1a100a] text-white/85 border-[#3a2a1a]' },
  { id: 'glassy', label: 'Glassy', icon: <Eye size={16} />, cls: 'bg-surface-2 text-text backdrop-blur-xl border-border' },
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

/* Animation intensity. 'system' defers to the OS reduced-motion setting;
   this switch exists because the 3D hero and page transitions are JS-driven
   and would otherwise ignore the Windows preference. */
const MOTION_MODES = [
  { id: 'system', label: 'System', icon: <Monitor size={16} />, desc: 'Follow Windows' },
  { id: 'full', label: 'Full', icon: <Zap size={16} />, desc: 'All animation' },
  { id: 'reduced', label: 'Reduced', icon: <Pause size={16} />, desc: 'Minimal motion' },
]

export function SettingsPage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const { prefs, update } = usePreferences()
  const fileInputRef = useRef<HTMLInputElement>(null)

  if (!systemInfo) {
    return (
      <div className="space-y-6">
        <div><Skeleton className="h-8 w-40 mb-1" /><Skeleton className="h-4 w-64" /></div>
        {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-32 rounded-xl" />)}
      </div>
    )
  }

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="page space-y-6">
      <motion.div variants={item}>
        <PageHero
          eyebrow="Settings"
          title="Settings"
          subtitle="Appearance, backgrounds and effects. Every change applies immediately and is remembered on this machine."
          icon={<Settings size={19} />}
        />
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
            <div className="space-y-3">
              <input ref={fileInputRef} type="file" accept={prefs.background === 'image' ? 'image/*' : 'video/mp4'} className="hidden"
                onChange={e => {
                  const f = e.target.files?.[0]
                  if (!f) return
                  update('bgUrl', URL.createObjectURL(f))
                }}
              />
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={prefs.bgUrl}
                  onChange={e => update('bgUrl', e.target.value)}
                  placeholder={prefs.background === 'image' ? 'URL ya local file select karein' : 'URL ya local MP4 select karein'}
                  className="flex-1 px-3 py-2 rounded-lg bg-surface-2 border border-border text-sm text-text placeholder:text-text-tertiary outline-none focus:border-accent/50 transition-colors"
                />
                <button onClick={() => fileInputRef.current?.click()}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-accent text-surface-0 text-sm font-medium hover:opacity-90 transition-opacity shrink-0"
                >
                  <FileUp size={14} /> Browse
                </button>
              </div>
              {prefs.bgUrl && prefs.bgUrl.startsWith('blob:') && (
                <p className="text-xs text-accent">Local file selected</p>
              )}
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
            <Activity className="w-5 h-5" style={{ color: prefs.accent }} />
            <h2 className="text-sm font-semibold text-text">Motion</h2>
          </div>
          <div className="grid grid-cols-3 gap-2">
            {MOTION_MODES.map(m => (
              <button key={m.id} onClick={() => update('motion', m.id)}
                className={cn('flex flex-col items-center gap-1.5 px-3 py-3 rounded-xl border text-sm font-medium transition-all bg-surface-2',
                  prefs.motion === m.id ? 'ring-2 ring-offset-2 ring-offset-surface-0' : 'border-border hover:bg-surface-3'
                )}
                style={prefs.motion === m.id ? { borderColor: `${prefs.accent}80` } : {}}
              >
                {m.icon}<span className="text-text">{m.label}</span>
                <span className="text-[10px] text-text-tertiary">{m.desc}</span>
              </button>
            ))}
          </div>
          <p className="text-xs text-text-tertiary mt-2.5">
            System follows the Windows reduced-motion setting. Reduced keeps
            state changes but removes page transitions, parallax and the 3D hero.
          </p>
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
