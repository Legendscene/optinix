import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  Trash2, AlertTriangle, CheckCircle2,
  Save,
} from 'lucide-react'
import { Card } from '../ui/Card'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { cn } from '../../lib/utils'
import type { SystemInfo } from '../../types'
import { api } from '../../lib/api'

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.03 } } }
const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }

const riskColor: Record<string, 'warning' | 'danger' | 'accent'> = { low: 'accent', medium: 'warning', high: 'danger' }

export function DebloatPage(_props: { systemInfo: SystemInfo | null }) {
  const [categories, setCategories] = useState<Record<string, { name: string; description: string; risk: string }>>({})
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)
  const [applying, setApplying] = useState(false)
  const [result, setResult] = useState<{ message: string; success: boolean } | null>(null)
  const [appResults, setAppResults] = useState<{ success: boolean; message: string }[]>([])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.debloatCategories()
      setCategories(data.categories)
    } catch {
      setCategories({})
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const toggle = (id: string) => {
    const next = new Set(selected)
    if (next.has(id)) next.delete(id); else next.add(id)
    setSelected(next)
  }

  const selectAll = () => setSelected(new Set(Object.keys(categories)))
  const deselectAll = () => setSelected(new Set())

  const applySelected = async () => {
    setApplying(true)
    setResult(null)
    setAppResults([])
    try {
      const r = await api.debloatApplyMultiple(Array.from(selected)) as { results?: { success: boolean; message: string }[]; success: boolean }
      setAppResults(r.results || [])
      const successCount = (r.results || []).filter(x => x.success).length
      setResult({ message: `Applied ${successCount}/${(r.results || []).length} operations`, success: r.success })
    } catch {
      setResult({ message: 'Debloat failed', success: false })
    } finally {
      setApplying(false)
    }
  }

  const createRestorePoint = async () => {
    setApplying(true)
    try {
      const r = await api.debloatRestorePoint() as { message?: string; success: boolean }
      setResult({ message: r.message || 'Restore point created', success: r.success })
    } catch {
      setResult({ message: 'Restore point failed', success: false })
    } finally {
      setApplying(false)
    }
  }

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="p-6 space-y-6">
      <motion.div variants={item} className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="p-2 rounded-xl bg-red-dim text-red"><Trash2 className="w-6 h-6" /></div>
            <h1 className="text-2xl font-bold text-text">Custom Debloater</h1>
          </div>
          <p className="text-sm text-text-secondary ml-11">Remove bloatware and disable telemetry</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" icon={<Save className="w-3 h-3" />} onClick={createRestorePoint} loading={applying}>Restore Point</Button>
          <Button variant="primary" icon={<Trash2 className="w-4 h-4" />} onClick={applySelected} disabled={selected.size === 0} loading={applying}>
            {`Debloat (${selected.size})`}
          </Button>
        </div>
      </motion.div>

      <motion.div variants={item} className="flex items-center gap-2">
        <Button variant="ghost" size="sm" onClick={selectAll}>Select All</Button>
        <Button variant="ghost" size="sm" onClick={deselectAll}>Deselect All</Button>
        <div className="flex-1" />
          <Badge variant="accent">{String(Object.keys(categories).length)} categories</Badge>
      </motion.div>

      {loading ? (
        <motion.div variants={item} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-28 rounded-xl bg-surface-2 animate-pulse" />)}
        </motion.div>
      ) : (
        <motion.div variants={item} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {Object.entries(categories).map(([id, cat]) => {
            const isSelected = selected.has(id)
            return (
              <button key={id} onClick={() => toggle(id)}
                className={cn('relative p-4 rounded-xl border text-left transition-all', isSelected ? 'border-red/40 bg-red-dim/10' : 'border-border bg-surface-1 hover:bg-surface-2')}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <p className="text-sm font-semibold text-text truncate">{cat.name}</p>
                    <Badge variant={riskColor[cat.risk] || 'accent'} className="shrink-0 text-[9px]">{cat.risk}</Badge>
                  </div>
                  <div className={cn('w-4 h-4 rounded border-2 shrink-0 ml-2', isSelected ? 'bg-red border-red' : 'border-text-tertiary')}>
                    {isSelected && <span className="flex items-center justify-center text-white text-[10px] font-bold">✓</span>}
                  </div>
                </div>
                <p className="text-xs text-text-secondary leading-relaxed line-clamp-2">{cat.description}</p>
              </button>
            )
          })}
        </motion.div>
      )}

      {appResults.length > 0 && (
        <motion.div variants={item}>
          <Card padding="lg">
            <h2 className="text-sm font-semibold text-text mb-3 flex items-center gap-2"><CheckCircle2 className="w-4 h-4 text-green" />Results</h2>
            <div className="space-y-1 max-h-60 overflow-y-auto">
              {appResults.map((r, i) => (
                <div key={i} className={cn('flex items-center gap-2 p-2 rounded-lg text-xs', r.success ? 'bg-green-dim/20 text-green' : 'bg-red-dim/20 text-red')}>
                  {r.success ? <CheckCircle2 className="w-3 h-3" /> : <AlertTriangle className="w-3 h-3" />}
                  {r.message}
                </div>
              ))}
            </div>
          </Card>
        </motion.div>
      )}

      {result && (
        <motion.div variants={item} className={cn('p-4 rounded-xl border', result.success ? 'bg-green-dim/10 border-green' : 'bg-red-dim/10 border-red')}>
          <div className="flex items-center gap-3">
            {result.success ? <CheckCircle2 className="w-5 h-5 text-green" /> : <AlertTriangle className="w-5 h-5 text-red" />}
            <span className="text-sm text-text">{result.message}</span>
          </div>
        </motion.div>
      )}
    </motion.div>
  )
}
