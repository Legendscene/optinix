import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  Undo2, History, Clock, CheckCircle2, AlertTriangle,
  Shield, RotateCcw, FileText,
} from 'lucide-react'
import { Card } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import { Skeleton } from '../ui/Skeleton'
import { cn } from '../../lib/utils'
import { api } from '../../lib/api'

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.05 } } }
const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }

interface Snapshot {
  file: string; created: string; os: string
}

export default function RollbackPage() {
  const [snapshots, setSnapshots] = useState<Snapshot[]>([])
  const [loading, setLoading] = useState(true)
  const [restoring, setRestoring] = useState<string | null>(null)
  const [result, setResult] = useState<{ success: boolean; message: string } | null>(null)
  const [creating, setCreating] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.rollbackSnapshots()
      setSnapshots(res.snapshots)
    } catch { setSnapshots([]) }
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  const createSnapshot = async () => {
    setCreating(true)
    try {
      await api.rollbackCreateSnapshot()
      setResult({ success: true, message: 'Snapshot created' })
      load()
    } catch (e) {
      setResult({ success: false, message: e instanceof Error ? e.message : 'Failed' })
    }
    setCreating(false)
  }

  const restore = async (file: string) => {
    setRestoring(file)
    setResult(null)
    try {
      const res = await api.rollbackRestore(file)
      setResult({ success: res.success, message: `Restored ${res.ok}/${res.total} settings` })
    } catch (e) {
      setResult({ success: false, message: e instanceof Error ? e.message : 'Restore failed' })
    }
    setRestoring(null)
  }

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-6">
      <motion.div variants={item}>
        <div className="flex items-center gap-3 mb-1">
          <Undo2 className="w-6 h-6 text-accent" />
          <h1 className="text-2xl font-bold text-text">Rollback & Restore</h1>
        </div>
        <p className="text-sm text-text-secondary ml-9">One-click restore Windows to previous state</p>
      </motion.div>

      <motion.div variants={item} className="flex items-center gap-3">
        <Button variant="primary" icon={<RotateCcw className="w-4 h-4" />} onClick={createSnapshot} loading={creating}>
          Create Snapshot
        </Button>
        <Button variant="ghost" icon={<History className="w-4 h-4" />} onClick={load} loading={loading}>
          Refresh
        </Button>
      </motion.div>

      {result && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
          className={cn('p-4 rounded-xl border', result.success ? 'bg-green-dim border-green/30' : 'bg-red-dim border-red/30')}>
          <div className="flex items-center gap-3">
            {result.success ? <CheckCircle2 className="w-5 h-5 text-green" /> : <AlertTriangle className="w-5 h-5 text-red" />}
            <p className={cn('text-sm font-medium', result.success ? 'text-green' : 'text-red')}>{result.message}</p>
          </div>
        </motion.div>
      )}

      <motion.div variants={item}>
        <Card padding="lg">
          <div className="flex items-center gap-2 mb-4">
            <Clock className="w-5 h-5 text-accent" />
            <h2 className="text-sm font-semibold text-text">Snapshots</h2>
            <Badge variant="accent">{snapshots.length}</Badge>
          </div>
          {loading ? (
            <div className="space-y-3">{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-16 rounded-xl" />)}</div>
          ) : snapshots.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-8 text-text-secondary">
              <Shield className="w-10 h-10 opacity-30" />
              <p className="text-sm">No snapshots found</p>
              <p className="text-xs">Run optimizations first, then restore here</p>
            </div>
          ) : (
            <div className="space-y-2">
              {snapshots.map(s => (
                <div key={s.file} className="flex items-center justify-between p-3 rounded-xl bg-surface-2 border border-border">
                  <div className="flex items-center gap-3 min-w-0">
                    <FileText className="w-4 h-4 text-text-secondary shrink-0" />
                    <div className="min-w-0">
                      <p className="text-sm text-text truncate">{s.file}</p>
                      <p className="text-xs text-text-tertiary">{s.created} &middot; {s.os}</p>
                    </div>
                  </div>
                  <Button variant="danger" size="sm" icon={<Undo2 className="w-3.5 h-3.5" />}
                    onClick={() => restore(s.file)} loading={restoring === s.file}>
                    Restore
                  </Button>
                </div>
              ))}
            </div>
          )}
        </Card>
      </motion.div>
    </motion.div>
  )
}
