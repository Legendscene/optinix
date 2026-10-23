import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { Info, Cpu, Monitor, CircuitBoard, MemoryStick as MemoryIcon, HardDrive, Battery, Wifi, Cpu as BiosIcon, Shield, Truck, Copy, Check } from 'lucide-react'
import { Card } from '../ui/Card'
// import { Button } from '../ui/Button'
// import { Badge } from '../ui/Badge'
import { Skeleton } from '../ui/Skeleton'
import { PageHero } from '../ui/PageHero'
import { api } from '../../lib/api'
import { formatBytes } from '../../lib/utils'
import type { SystemInfo, DeviceInfo } from '../../types'

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.03 } } }
const item = { hidden: { opacity: 0, y: 16 }, show: { opacity: 1, y: 0 } }

interface TabDef {
  id: string
  label: string
  icon: React.ReactNode
}

const TABS: TabDef[] = [
  { id: 'cpu', label: 'CPU', icon: <Cpu size={16} /> },
  { id: 'gpu', label: 'GPU', icon: <Monitor size={16} /> },
  { id: 'motherboard', label: 'Motherboard', icon: <CircuitBoard size={16} /> },
  { id: 'ram', label: 'RAM', icon: <MemoryIcon size={16} /> },
  { id: 'storage', label: 'Storage', icon: <HardDrive size={16} /> },
  { id: 'battery', label: 'Battery', icon: <Battery size={16} /> },
  { id: 'network', label: 'Network', icon: <Wifi size={16} /> },
  { id: 'bios', label: 'BIOS/UEFI', icon: <BiosIcon size={16} /> },
  { id: 'tpm', label: 'TPM/SecureBoot', icon: <Shield size={16} /> },
  { id: 'drivers', label: 'Drivers', icon: <Truck size={16} /> },
]

function formatDeviceValue(key: string, val: unknown): string {
  if (val == null || val === '') return '—'
  if (typeof val === 'boolean') return val ? 'Yes' : 'No'
  if (typeof val === 'number') {
    const keyLower = key.toLowerCase()
    if (keyLower.includes('speed') || keyLower.includes('clock') || keyLower.includes('mhz')) {
      if (val >= 1000) return `${(val / 1000).toFixed(2)} GHz`
      return `${val} MHz`
    }
    if (keyLower.includes('temp')) return `${val}°C`
    if (keyLower.includes('percent') || keyLower.includes('usage') || keyLower.includes('load')) return `${val}%`
    if (keyLower.includes('size') || keyLower.includes('memory') || keyLower.includes('ram') || keyLower.includes('vram')) {
      return val >= 1024 ? formatBytes(val * 1024 * 1024) : `${val} GB`
    }
    if (keyLower.includes('cores')) return String(val)
    if (keyLower.includes('threads')) return String(val)
    return String(val)
  }
  return String(val)
}

function InfoRow({ label, value, onCopy }: { label: string; value: string; onCopy?: (v: string) => void }) {
  return (
    <div className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-surface-2/50 transition-colors group">
      <span className="text-xs text-text-tertiary capitalize">{label.replace(/_/g, ' ')}</span>
      <div className="flex items-center gap-2">
        <span className="text-xs text-text font-mono text-right max-w-[400px] truncate" title={value}>{value}</span>
        {onCopy && (
          <button
            onClick={() => onCopy(value)}
            className="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 rounded hover:bg-surface-3 text-text-tertiary hover:text-text"
            title="Copy"
          >
            <Copy size={12} />
          </button>
        )}
      </div>
    </div>
  )
}

export function DeviceInfoPage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const [activeTab, setActiveTab] = useState('cpu')
  const [allData, setAllData] = useState<DeviceInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [copiedKey, setCopiedKey] = useState<string | null>(null)

  const fetchAll = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.deviceInfo() as DeviceInfo
      setAllData(data)
    } catch {
      setError('Failed to load device information')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchAll() }, [fetchAll])

  const handleCopy = useCallback((val: string) => {
    navigator.clipboard.writeText(val)
    setCopiedKey(val)
    setTimeout(() => setCopiedKey(null), 1500)
  }, [])

  if (!systemInfo) {
    return (
      <div className="page space-y-6">
        <div><Skeleton className="h-8 w-48 mb-1" /><Skeleton className="h-4 w-64" /></div>
        <Skeleton className="h-10 rounded-xl" />
        <Skeleton className="h-96" />
      </div>
    )
  }

  const currentData = allData ? (allData as unknown as Record<string, Record<string, unknown>>)[activeTab] || {} : {}
  const entries = Object.entries(currentData)

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="page space-y-6">
      <motion.div variants={item}>
        <PageHero
          title="Device Information"
          subtitle="Detailed hardware and system information"
          icon={<Info size={19} />}
        />
      </motion.div>

      <motion.div variants={item} className="flex flex-wrap gap-1.5">
        {TABS.map(tab => {
          const isActive = activeTab === tab.id
          const hasData = allData && (allData as unknown as Record<string, unknown>)[tab.id] != null
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                isActive
                  ? 'bg-accent text-surface-0 shadow-sm'
                  : hasData
                    ? 'text-text-secondary hover:text-text bg-surface-2 hover:bg-surface-3 border border-border'
                    : 'text-text-tertiary bg-surface-1 border border-border/50 opacity-50 cursor-not-allowed'
              }`}
              disabled={!hasData}
            >
              {tab.icon}
              {tab.label}
            </button>
          )
        })}
      </motion.div>

      {loading && (
        <motion.div variants={item} className="space-y-2">
          {Array.from({ length: 10 }).map((_, i) => (
            <Skeleton key={i} className="h-9 rounded-lg" />
          ))}
        </motion.div>
      )}

      {error && (
        <motion.div variants={item} className="p-4 rounded-xl bg-red-dim border border-red/30 text-red text-sm">{error}</motion.div>
      )}

      {!loading && !error && allData && (
        <motion.div variants={item} key={activeTab}>
          <Card padding="lg">
            <div className="flex items-center gap-2 mb-4">
              {TABS.find(t => t.id === activeTab)?.icon}
              <h2 className="text-sm font-semibold text-text">{TABS.find(t => t.id === activeTab)?.label || activeTab}</h2>
              <span className="text-[10px] text-text-tertiary ml-auto">{entries.length} properties</span>
            </div>
            {entries.length > 0 ? (
              <div className="divide-y divide-border/50">
                {entries.map(([key, val]) => {
                  const formatted = formatDeviceValue(key, val)
                  return (
                    <InfoRow
                      key={key}
                      label={key}
                      value={formatted}
                      onCopy={handleCopy}
                    />
                  )
                })}
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2 py-6">
                <Info size={24} className="text-text-tertiary" />
                <p className="text-xs text-text-secondary">No data available for this category.</p>
              </div>
            )}
          </Card>
        </motion.div>
      )}

      {!loading && !error && !allData && (
        <motion.div variants={item}>
          <Card padding="lg">
            <div className="flex flex-col items-center gap-2 py-6">
              <Info size={24} className="text-text-tertiary" />
              <p className="text-xs text-text-secondary">Could not load device information. The system may not support this API.</p>
            </div>
          </Card>
        </motion.div>
      )}

      {copiedKey && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="fixed bottom-4 right-4 p-3 rounded-xl bg-green-dim border border-green/30 text-green text-xs flex items-center gap-2">
          <Check size={14} />
          Copied to clipboard
        </motion.div>
      )}
    </motion.div>
  )
}
