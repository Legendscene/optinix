import { useState, useCallback, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  Settings,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Save,
  FolderOpen,
  RotateCw,
} from 'lucide-react'
import { ActionCard } from '../ui/ActionCard'
import { Skeleton } from '../ui/Skeleton'
import { cn } from '../../lib/utils'
import { api } from '../../lib/api'
import type { SystemInfo } from '../../types'

export default function WindowsTweaksPage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const [tweaksData, setTweaksData] = useState<Record<string, { path: string; name: string; type: string; on: string; off: string }>>({})
  const [categoriesData, setCategoriesData] = useState<Record<string, string[]>>({})
  const [tweaks, setTweaks] = useState<Record<string, boolean>>({})
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [loadingAction, setLoadingAction] = useState<string | null>(null)
  const [result, setResult] = useState<{ key: string; message: string; success: boolean } | null>(null)
  const [activeCategory, setActiveCategory] = useState<string>('')

  useEffect(() => {
    setLoading(true)
    api.tweaksList()
      .then(data => {
        setTweaksData(data.tweaks)
        setCategoriesData(data.categories)
        const cats = Object.keys(data.categories)
        if (cats.length > 0) setActiveCategory(cats[0])
        setLoading(false)
      })
      .catch(err => {
        setLoadError(err.message)
        setLoading(false)
      })
  }, [])

  const toggleTweak = useCallback(async (id: string) => {
    const enable = !tweaks[id]
    setLoadingAction(id)
    setTweaks(prev => ({ ...prev, [id]: enable }))
    setResult(null)
    try {
      const res = await api.tweaksApply(id, enable) as { success?: boolean; message?: string }
      setResult({ key: id, message: res.message || `${tweaksData[id]?.name || id} ${enable ? 'enabled' : 'disabled'}`, success: res.success ?? true })
      if (res.success === false) {
        setTweaks(prev => ({ ...prev, [id]: !enable }))
      }
    } catch (e) {
      setTweaks(prev => ({ ...prev, [id]: !enable }))
      setResult({ key: id, message: e instanceof Error ? e.message : 'Failed', success: false })
    } finally {
      setLoadingAction(null)
    }
  }, [tweaks, tweaksData])

  const applyAll = useCallback(async () => {
    const enabled = Object.entries(tweaks).filter(([_, v]) => v).map(([k]) => k)
    const payload = Object.fromEntries(enabled.map(k => [k, true]))
    setLoadingAction('apply')
    setResult(null)
    try {
      const res = await api.tweaksApplyMultiple(payload) as { success?: boolean; results?: { success: boolean }[] }
      const successCount = res.results?.filter(r => r.success).length ?? 0
      const failCount = (res.results?.length ?? 0) - successCount
      setResult({ key: 'apply', message: res.success ? `Applied ${successCount} tweaks${failCount > 0 ? ` (${failCount} failed)` : ''}` : 'Failed to apply tweaks', success: res.success ?? false })
    } catch (e) {
      setResult({ key: 'apply', message: e instanceof Error ? e.message : 'Failed', success: false })
    } finally {
      setLoadingAction(null)
    }
  }, [tweaks])

  const createRestorePoint = useCallback(async () => {
    setLoadingAction('restore')
    setResult(null)
    try {
      const res = await api.debloatRestorePoint() as { success?: boolean; message?: string }
      setResult({ key: 'restore', message: res.message || 'System restore point created', success: res.success ?? true })
    } catch (e) {
      setResult({ key: 'restore', message: e instanceof Error ? e.message : 'Failed', success: false })
    } finally {
      setLoadingAction(null)
    }
  }, [])

  const exportSettings = useCallback(async () => {
    setLoadingAction('export')
    setResult(null)
    try {
      const activeTweaks = Object.fromEntries(Object.entries(tweaks).filter(([_, v]) => v))
      const data = await api.tweaksExport(activeTweaks)
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'optinix-tweaks.json'
      a.click()
      URL.revokeObjectURL(url)
      setResult({ key: 'export', message: 'Settings exported to optinix-tweaks.json', success: true })
    } catch (e) {
      setResult({ key: 'export', message: e instanceof Error ? e.message : 'Failed', success: false })
    } finally {
      setLoadingAction(null)
    }
  }, [tweaks])

  const importSettings = useCallback(async () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.json'
    input.onchange = async e => {
      const file = (e.target as HTMLInputElement).files?.[0]
      if (!file) return
      try {
        const text = await file.text()
        const imported = JSON.parse(text)
        setLoadingAction('import')
        setResult(null)
        const res = await api.tweaksImport(imported) as { success?: boolean }
        setResult({ key: 'import', message: res.success ? 'Settings imported successfully' : 'Import failed', success: res.success ?? false })
        if (res.success) {
          const fresh = await api.tweaksList()
          setTweaksData(fresh.tweaks)
          setCategoriesData(fresh.categories)
          const cats = Object.keys(fresh.categories)
          if (cats.length > 0 && !activeCategory) setActiveCategory(cats[0])
        }
      } catch (e) {
        setResult({ key: 'import', message: e instanceof Error ? e.message : 'Invalid settings file', success: false })
      } finally {
        setLoadingAction(null)
      }
    }
    input.click()
  }, [])

  if (!systemInfo) {
    return (
      <div className="p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <Skeleton variant="text" width="200px" height="28px" />
            <Skeleton variant="text" width="300px" height="16px" />
          </div>
          <Skeleton variant="circular" className="h-32 w-32" />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} variant="rectangular" height="100px" />)}
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="p-6 space-y-6">
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-accent" />
          <span className="ml-3 text-text-secondary">Loading tweaks...</span>
        </div>
      </div>
    )
  }

  if (loadError) {
    return (
      <div className="p-6 space-y-6">
        <div className="p-4 rounded-xl border border-red bg-red/10">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red" />
            <span className="text-sm text-text">{loadError}</span>
          </div>
        </div>
      </div>
    )
  }

  const categories = Object.keys(categoriesData)
  const enabledCount = Object.values(tweaks).filter(v => v).length

  return (
    <motion.div initial="hidden" animate="show" className="p-6 space-y-6">
      <motion.div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="p-2 rounded-xl bg-surface-2 text-accent"><Settings className="w-6 h-6" /></div>
            <h1 className="text-2xl font-bold text-text">Windows Tweaks</h1>
          </div>
          <p className="text-sm text-text-secondary ml-11">Advanced Windows configuration</p>
        </div>
        <motion.div className="flex items-center gap-2">
          <span className="px-3 py-1 rounded-full bg-blue-dim text-blue text-xs font-medium">{enabledCount} tweaks enabled</span>
          <span className="px-3 py-1 rounded-full bg-accent-dim text-accent text-xs font-medium">{categories.length} categories</span>
        </motion.div>
      </motion.div>

      <motion.div className="flex items-center gap-2 mb-4">
        {categories.map((cat) => (
          <button key={cat} onClick={() => setActiveCategory(cat)} className={cn('px-3 py-1.5 rounded-lg text-sm font-medium transition-colors', activeCategory === cat ? 'bg-accent text-white' : 'bg-surface-2 text-text-secondary hover:bg-surface-3 hover:text-text')}>
            {cat}
          </button>
        ))}
      </motion.div>

      <motion.div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {categoriesData[activeCategory]?.map((tweakId, i) => {
          const tweak = tweaksData[tweakId]
          if (!tweak) return null
          return (
            <motion.div key={tweakId} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.03 }} className="relative p-5 rounded-2xl bg-surface-1 border border-border hover:border-accent/50 transition-colors">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-surface-2 text-accent shrink-0"><Settings className="w-5 h-5" /></div>
                  <div>
                    <h3 className="text-sm font-semibold text-text">{tweak.name}</h3>
                    <p className="text-xs text-text-secondary">{tweak.path}</p>
                  </div>
                </div>
                <button onClick={() => toggleTweak(tweakId)} disabled={loadingAction === tweakId} className={cn('relative px-3 py-1.5 rounded-lg text-sm font-medium transition-colors', tweaks[tweakId] ? 'bg-accent text-white hover:bg-accent/90' : 'bg-surface-2 text-text-secondary hover:bg-surface-3 hover:text-text')}>
                  {loadingAction === tweakId ? <Loader2 className="w-4 h-4 animate-spin" /> : tweaks[tweakId] ? 'Enabled' : 'Disabled'}
                </button>
              </div>
            </motion.div>
          )
        })}
      </motion.div>

      <motion.div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <ActionCard icon={<CheckCircle2 className="w-5 h-5" />} title="Apply Selected Tweaks" desc={`Apply ${Object.values(tweaks).filter(v => v).length} enabled tweaks`} tags={['Apply']} variant="success" onClick={applyAll} loading={loadingAction === 'apply'} disabled={Object.values(tweaks).every(v => !v)} />
        <ActionCard icon={<RotateCw className="w-5 h-5" />} title="Create Restore Point" desc="Create system restore point before applying" tags={['Safety']} variant="default" onClick={createRestorePoint} loading={loadingAction === 'restore'} />
        <ActionCard icon={<Save className="w-5 h-5" />} title="Export Settings" desc="Save current tweak configuration to file" tags={['Export']} variant="default" onClick={exportSettings} loading={loadingAction === 'export'} disabled={!Object.values(tweaks).some(v => v)} />
        <ActionCard icon={<FolderOpen className="w-5 h-5" />} title="Import Settings" desc="Load tweak configuration from file" tags={['Import']} variant="default" onClick={importSettings} loading={loadingAction === 'import'} />
      </motion.div>

      <motion.div className="p-4 rounded-xl bg-surface-1 border border-border">
        <div className="flex items-center gap-2 mb-3">
          <AlertCircle className="w-4 h-4 text-yellow" />
          <span className="text-sm font-semibold text-text">System Stability Notice</span>
        </div>
        <p className="text-xs text-text-secondary">
          Some tweaks modify system behavior significantly. UAC disable, hibernation disable, and visual effects changes may affect system stability.
          Always create a restore point before applying multiple tweaks. Test each change individually if possible.
        </p>
      </motion.div>

      {result && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mt-4 p-4 rounded-xl border" style={{ borderColor: result.success ? '#22c55e' : '#ef4444', backgroundColor: result.success ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)' }}>
          <div className="flex items-center gap-3">
            <div className={cn('w-2 h-2 rounded-full', result.success ? 'bg-green' : 'bg-red')} />
            <span className="text-sm text-text">{result.message}</span>
          </div>
        </motion.div>
      )}
    </motion.div>
  )
}