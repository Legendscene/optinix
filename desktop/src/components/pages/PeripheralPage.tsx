import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Mouse,
  Keyboard,
  Usb,
  Zap,
  RotateCcw,
  Gauge,
  MousePointer2,
  TimerReset,
  RefreshCw,
  Type,
} from 'lucide-react'
import { Card } from '../ui/Card'
import { MetricCard } from '../ui/MetricCard'
import { ActionCard } from '../ui/ActionCard'
import { cn } from '../../lib/utils'
import type { SystemInfo } from '../../types'
import { api } from '../../lib/api'

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.05 } },
}

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
}

export function PeripheralPage(_props: { systemInfo: SystemInfo | null }) {
  const [loadingAction, setLoadingAction] = useState<string | null>(null)
  const [result, setResult] = useState<{ key: string; message: string; success: boolean } | null>(null)
  const [toggles, setToggles] = useState({
    pointerPrecision: false,
    usbSelectiveSuspend: false,
  })
  const [dpi, setDpi] = useState(800)
  const [scrollLines, setScrollLines] = useState(3)
  const [repeatDelay, setRepeatDelay] = useState(500)
  const [repeatRate, setRepeatRate] = useState(31)
  const [cursorBlink, setCursorBlink] = useState(530)

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

  const toggleSwitch = async (key: keyof typeof toggles, apiKey: string) => {
    const next = !toggles[key]
    setToggles((prev) => ({ ...prev, [key]: next }))
    try {
      await api.tweakStateSet({ [apiKey]: next })
    } catch {
      setToggles((prev) => ({ ...prev, [key]: !next }))
    }
  }

  const applySetting = async (key: string, value: number | boolean) => {
    setLoadingAction(key)
    setResult(null)
    try {
      await api.tweakStateSet({ [key]: value } as Record<string, boolean>)
      setResult({ key, message: `${key.replace(/_/g, ' ')} updated`, success: true })
    } catch (e) {
      setResult({ key, message: e instanceof Error ? e.message : 'Failed to apply', success: false })
    } finally {
      setLoadingAction(null)
    }
  }

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="p-6 space-y-6">
      <motion.div variants={item}>
        <div className="flex items-center gap-3 mb-1">
          <div className="p-2 rounded-xl bg-accent-dim text-accent"><Mouse className="w-6 h-6" /></div>
          <h1 className="text-2xl font-bold text-text">Peripheral Optimization</h1>
        </div>
        <p className="text-sm text-text-secondary ml-11">Fine-tune mouse, keyboard, and USB settings</p>
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-3 gap-4">
        <MetricCard icon={<Gauge className="w-5 h-5" />} label="DPI" value={String(dpi)} sub="Current sensitivity" />
        <MetricCard icon={<TimerReset className="w-5 h-5" />} label="Repeat Rate" value={`${repeatRate} chars/s`} sub="Keyboard repeat" />
        <MetricCard icon={<MousePointer2 className="w-5 h-5" />} label="Scroll" value={`${scrollLines} lines`} sub="Per notch" />
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <ActionCard
          icon={<Zap className="w-5 h-5" />}
          title="Optimize Peripherals"
          desc="Apply optimal mouse, keyboard, and USB settings"
          tags={['Recommended']}
          onClick={() => runAction('optimize', () => api.tweakStateSet({ mouse_optimized: true, keyboard_optimized: true, usb_optimized: true }), 'Peripherals optimized')}
        />
        <ActionCard
          icon={<RotateCcw className="w-5 h-5" />}
          title="Reset to Defaults"
          desc="Restore peripheral settings to Windows defaults"
          variant="default"
          onClick={() => runAction('reset', () => api.tweakStateSet({ mouse_optimized: false, keyboard_optimized: false, usb_optimized: false }), 'Peripheral defaults restored')}
        />
        <ActionCard
          icon={<RefreshCw className="w-5 h-5" />}
          title="Benchmark Input"
          desc="Test input latency and polling rate"
          tags={['Diagnostic']}
          onClick={() => runAction('bench', () => api.tweakStateSet({ input_benchmark: true }), 'Input benchmark started')}
        />
      </motion.div>

      <motion.div variants={item}>
        <Card>
          <h2 className="text-sm font-semibold text-text mb-4 flex items-center gap-2"><Mouse className="w-4 h-4 text-accent" /> Mouse</h2>
          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm text-text">DPI Sensitivity</label>
                <span className="text-sm font-medium text-accent">{dpi} DPI</span>
              </div>
              <input
                type="range"
                min="400"
                max="3200"
                step="100"
                value={dpi}
                onChange={(e) => setDpi(Number(e.target.value))}
                onMouseUp={() => applySetting('mouse_dpi', dpi)}
                className="w-full h-1.5 bg-surface-3 rounded-full appearance-none cursor-pointer accent-accent"
              />
              <div className="flex justify-between text-[10px] text-text-tertiary mt-1"><span>400</span><span>3200</span></div>
            </div>

            <div className="flex items-center justify-between py-2">
              <div>
                <p className="text-sm font-medium text-text">Pointer Precision</p>
                <p className="text-xs text-text-tertiary">Enhance pointer accuracy (mouse acceleration)</p>
              </div>
              <button
                onClick={() => toggleSwitch('pointerPrecision', 'pointer_precision')}
                className={cn('relative w-10 h-5 rounded-full transition-colors duration-200', toggles.pointerPrecision ? 'bg-accent' : 'bg-surface-3')}
              >
                <motion.div animate={{ x: toggles.pointerPrecision ? 20 : 2 }} transition={{ type: 'spring', stiffness: 500, damping: 30 }} className="absolute top-0.5 w-4 h-4 rounded-full bg-white shadow" />
              </button>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm text-text">Scroll Wheel — Lines per notch</label>
                <span className="text-sm font-medium text-accent">{scrollLines}</span>
              </div>
              <input
                type="range"
                min="1"
                max="100"
                value={scrollLines}
                onChange={(e) => setScrollLines(Number(e.target.value))}
                onMouseUp={() => applySetting('scroll_lines', scrollLines)}
                className="w-full h-1.5 bg-surface-3 rounded-full appearance-none cursor-pointer accent-accent"
              />
              <div className="flex justify-between text-[10px] text-text-tertiary mt-1"><span>1</span><span>100</span></div>
            </div>
          </div>
        </Card>
      </motion.div>

      <motion.div variants={item}>
        <Card>
          <h2 className="text-sm font-semibold text-text mb-4 flex items-center gap-2"><Keyboard className="w-4 h-4 text-accent" /> Keyboard</h2>
          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm text-text">Repeat Delay</label>
                <span className="text-sm font-medium text-accent">{repeatDelay} ms</span>
              </div>
              <input
                type="range"
                min="200"
                max="1000"
                step="50"
                value={repeatDelay}
                onChange={(e) => setRepeatDelay(Number(e.target.value))}
                onMouseUp={() => applySetting('keyboard_repeat_delay', repeatDelay)}
                className="w-full h-1.5 bg-surface-3 rounded-full appearance-none cursor-pointer accent-accent"
              />
              <div className="flex justify-between text-[10px] text-text-tertiary mt-1"><span>200 ms</span><span>1000 ms</span></div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm text-text">Repeat Rate</label>
                <span className="text-sm font-medium text-accent">{repeatRate} chars/s</span>
              </div>
              <input
                type="range"
                min="2"
                max="60"
                value={repeatRate}
                onChange={(e) => setRepeatRate(Number(e.target.value))}
                onMouseUp={() => applySetting('keyboard_repeat_rate', repeatRate)}
                className="w-full h-1.5 bg-surface-3 rounded-full appearance-none cursor-pointer accent-accent"
              />
              <div className="flex justify-between text-[10px] text-text-tertiary mt-1"><span>2</span><span>60</span></div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm text-text">Cursor Blink Rate</label>
                <span className="text-sm font-medium text-accent">{cursorBlink} ms</span>
              </div>
              <input
                type="range"
                min="200"
                max="1200"
                step="10"
                value={cursorBlink}
                onChange={(e) => setCursorBlink(Number(e.target.value))}
                onMouseUp={() => applySetting('cursor_blink_rate', cursorBlink)}
                className="w-full h-1.5 bg-surface-3 rounded-full appearance-none cursor-pointer accent-accent"
              />
              <div className="flex justify-between text-[10px] text-text-tertiary mt-1"><span>200 ms</span><span>1200 ms</span></div>
            </div>
          </div>
        </Card>
      </motion.div>

      <motion.div variants={item}>
        <Card>
          <h2 className="text-sm font-semibold text-text mb-4 flex items-center gap-2"><Usb className="w-4 h-4 text-accent" /> USB</h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between py-2">
              <div>
                <p className="text-sm font-medium text-text">USB Selective Suspend</p>
                <p className="text-xs text-text-tertiary">Allow USB ports to be suspended to save power</p>
              </div>
              <button
                onClick={() => toggleSwitch('usbSelectiveSuspend', 'usb_selective_suspend')}
                className={cn('relative w-10 h-5 rounded-full transition-colors duration-200', toggles.usbSelectiveSuspend ? 'bg-accent' : 'bg-surface-3')}
              >
                <motion.div animate={{ x: toggles.usbSelectiveSuspend ? 20 : 2 }} transition={{ type: 'spring', stiffness: 500, damping: 30 }} className="absolute top-0.5 w-4 h-4 rounded-full bg-white shadow" />
              </button>
            </div>

            <div className="p-3 rounded-xl bg-accent-dim/30 border border-accent/10">
              <div className="flex items-center gap-2 mb-1">
                <Type className="w-4 h-4 text-accent" />
                <span className="text-xs font-medium text-text">USB Power Settings</span>
              </div>
              <p className="text-xs text-text-secondary">Disabling selective suspend can reduce input lag on USB devices but increases power consumption.</p>
            </div>
          </div>
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
          Applying tweaks...
        </div>
      )}
    </motion.div>
  )
}
