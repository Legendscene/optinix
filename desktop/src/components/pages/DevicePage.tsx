import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Monitor,
  Zap,
  RotateCcw,
  Wrench,
  Settings2,
  Usb,
  HardDrive,
  Play,
  Disc,
  Download,
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

export function DevicePage(_props: { systemInfo: SystemInfo | null }) {
  const [loadingAction, setLoadingAction] = useState<string | null>(null)
  const [result, setResult] = useState<{ key: string; message: string; success: boolean } | null>(null)
  const [toggles, setToggles] = useState({
    autoPlay: false,
    autoDownloadDrivers: false,
    autoPlayMedia: false,
  })

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

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="p-6 space-y-6">
      <motion.div variants={item}>
        <div className="flex items-center gap-3 mb-1">
          <div className="p-2 rounded-xl bg-accent-dim text-accent"><Monitor className="w-6 h-6" /></div>
          <h1 className="text-2xl font-bold text-text">Device Optimization</h1>
        </div>
        <p className="text-sm text-text-secondary ml-11">Manage device installation, AutoPlay, and hardware settings</p>
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-3 gap-4">
        <MetricCard icon={<Settings2 className="w-5 h-5" />} label="AutoPlay" value={toggles.autoPlay ? 'On' : 'Off'} sub="Media & devices" />
        <MetricCard icon={<Download className="w-5 h-5" />} label="Auto Driver Download" value={toggles.autoDownloadDrivers ? 'On' : 'Off'} sub="Windows Update" />
        <MetricCard icon={<HardDrive className="w-5 h-5" />} label="USB Drives" value={toggles.autoPlayMedia ? 'Prompt' : 'No action'} sub="Default behavior" />
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <ActionCard
          icon={<Zap className="w-5 h-5" />}
          title="Optimize Devices"
          desc="Apply optimal device installation and AutoPlay settings"
          tags={['Recommended']}
          onClick={() => runAction('optimize', () => api.tweakStateSet({ device_optimized: true }), 'Device settings optimized')}
        />
        <ActionCard
          icon={<RotateCcw className="w-5 h-5" />}
          title="Reset Defaults"
          desc="Restore device settings to Windows defaults"
          variant="default"
          onClick={() => runAction('reset', () => api.tweakStateSet({ device_optimized: false }), 'Device defaults restored')}
        />
        <ActionCard
          icon={<Wrench className="w-5 h-5" />}
          title="Troubleshoot Hardware"
          desc="Run the hardware and devices troubleshooter"
          tags={['Diagnostic']}
          onClick={() => runAction('troubleshoot', () => api.tweakStateSet({ hardware_troubleshoot: true }), 'Hardware troubleshooter launched')}
        />
      </motion.div>

      <motion.div variants={item}>
        <Card>
          <h2 className="text-sm font-semibold text-text mb-4 flex items-center gap-2"><Play className="w-4 h-4 text-accent" /> AutoPlay Settings</h2>
          <div className="space-y-1 divide-y divide-border">
            <div className="flex items-center justify-between py-3 first:pt-0">
              <div>
                <p className="text-sm font-medium text-text">AutoPlay</p>
                <p className="text-xs text-text-tertiary">Automatically choose how to handle media and devices</p>
              </div>
              <button
                onClick={() => toggleSwitch('autoPlay', 'autoplay_enabled')}
                className={cn('relative w-10 h-5 rounded-full transition-colors duration-200', toggles.autoPlay ? 'bg-accent' : 'bg-surface-3')}
              >
                <motion.div animate={{ x: toggles.autoPlay ? 20 : 2 }} transition={{ type: 'spring', stiffness: 500, damping: 30 }} className="absolute top-0.5 w-4 h-4 rounded-full bg-white shadow" />
              </button>
            </div>
          </div>
        </Card>
      </motion.div>

      <motion.div variants={item}>
        <Card>
          <h2 className="text-sm font-semibold text-text mb-4 flex items-center gap-2"><Download className="w-4 h-4 text-accent" /> Device Installation</h2>
          <div className="space-y-1 divide-y divide-border">
            <div className="flex items-center justify-between py-3 first:pt-0">
              <div>
                <p className="text-sm font-medium text-text">Automatic Driver Download</p>
                <p className="text-xs text-text-tertiary">Allow Windows to download driver updates automatically</p>
              </div>
              <button
                onClick={() => toggleSwitch('autoDownloadDrivers', 'auto_download_drivers')}
                className={cn('relative w-10 h-5 rounded-full transition-colors duration-200', toggles.autoDownloadDrivers ? 'bg-accent' : 'bg-surface-3')}
              >
                <motion.div animate={{ x: toggles.autoDownloadDrivers ? 20 : 2 }} transition={{ type: 'spring', stiffness: 500, damping: 30 }} className="absolute top-0.5 w-4 h-4 rounded-full bg-white shadow" />
              </button>
            </div>

            <div className="py-3">
              <div className="flex items-center gap-3 p-3 rounded-xl bg-accent-dim/20 border border-accent/10">
                <Settings2 className="w-4 h-4 text-accent shrink-0" />
                <div>
                  <p className="text-xs font-medium text-text">Driver Installation Behavior</p>
                  <p className="text-xs text-text-secondary">Controls whether Windows Update downloads manufacturer-provided drivers and icons for devices.</p>
                </div>
              </div>
            </div>
          </div>
        </Card>
      </motion.div>

      <motion.div variants={item}>
        <Card>
          <h2 className="text-sm font-semibold text-text mb-4 flex items-center gap-2"><Usb className="w-4 h-4 text-accent" /> Removable Devices</h2>
          <div className="space-y-1 divide-y divide-border">
            <div className="flex items-center justify-between py-3 first:pt-0">
              <div>
                <p className="text-sm font-medium text-text">USB Drives Default Action</p>
                <p className="text-xs text-text-tertiary">Default action when inserting removable drives</p>
              </div>
              <select
                className="bg-surface-3 text-text text-xs rounded-lg px-2 py-1.5 border border-border outline-none"
                onChange={(e) => runAction('usb_action', () => api.tweakStateSet({ usb_default_action: true } as Record<string, boolean>), `USB action set to ${e.target.value}`)}
                defaultValue="prompt"
              >
                <option value="no_action">No action</option>
                <option value="prompt">Ask me</option>
                <option value="open">Open folder</option>
              </select>
            </div>

            <div className="flex items-center justify-between py-3">
              <div className="flex items-center gap-2">
                <Disc className="w-4 h-4 text-text-tertiary" />
                <div>
                  <p className="text-sm font-medium text-text">AutoPlay for Media</p>
                  <p className="text-xs text-text-tertiary">AutoPlay behavior for CDs, DVDs, and other media</p>
                </div>
              </div>
              <button
                onClick={() => toggleSwitch('autoPlayMedia', 'autoplay_media')}
                className={cn('relative w-10 h-5 rounded-full transition-colors duration-200', toggles.autoPlayMedia ? 'bg-accent' : 'bg-surface-3')}
              >
                <motion.div animate={{ x: toggles.autoPlayMedia ? 20 : 2 }} transition={{ type: 'spring', stiffness: 500, damping: 30 }} className="absolute top-0.5 w-4 h-4 rounded-full bg-white shadow" />
              </button>
            </div>
          </div>
        </Card>
      </motion.div>

      <motion.div variants={item}>
        <Card>
          <h2 className="text-sm font-semibold text-text mb-4 flex items-center gap-2"><Wrench className="w-4 h-4 text-accent" /> Tools</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <button
              onClick={() => runAction('devmgmt', () => api.tweakStateSet({ launch_device_manager: true }), 'Device Manager opened')}
              disabled={loadingAction === 'devmgmt'}
              className="flex items-center gap-3 p-3 rounded-xl bg-surface-2/60 hover:bg-surface-2 transition-colors text-left"
            >
              <div className="p-2 rounded-lg bg-accent-dim text-accent"><Settings2 className="w-4 h-4" /></div>
              <div>
                <p className="text-sm font-medium text-text">Device Manager</p>
                <p className="text-xs text-text-secondary">Quick launch Device Manager</p>
              </div>
            </button>
            <button
              onClick={() => runAction('troubleshoot', () => api.tweakStateSet({ hardware_troubleshoot: true }), 'Hardware troubleshooter launched')}
              disabled={loadingAction === 'troubleshoot'}
              className="flex items-center gap-3 p-3 rounded-xl bg-surface-2/60 hover:bg-surface-2 transition-colors text-left"
            >
              <div className="p-2 rounded-lg bg-yellow-dim text-yellow"><Wrench className="w-4 h-4" /></div>
              <div>
                <p className="text-sm font-medium text-text">Hardware Troubleshooter</p>
                <p className="text-xs text-text-secondary">Find and fix device issues</p>
              </div>
            </button>
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
