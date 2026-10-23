import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  Clock, CheckCircle2, AlertTriangle, Power,
  RefreshCw, Save, Plus, Trash2, Play,
  History, ListOrdered, FileText,
} from 'lucide-react'
import { Card } from '../ui/Card'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { Skeleton } from '../ui/Skeleton'
import { PageHero } from '../ui/PageHero'
import { cn } from '../../lib/utils'
import { api } from '../../lib/api'

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.05 } } }
const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }

const PRESET_CONFIGS = [
  { id: 'daily', name: 'Daily Quick Clean', desc: 'Temp files, cache, logs daily', tasks: ['cleanup', 'cache'] },
  { id: 'weekly', name: 'Weekly Performance', desc: 'Deeper optimize weekly', tasks: ['cleanup', 'services', 'startup'] },
  { id: 'monthly', name: 'Monthly Full', desc: 'Full system optimization monthly', tasks: ['cleanup', 'services', 'startup', 'network', 'registry'] },
]

interface Task {
  id: string
  name: string
  action: string
  interval: string
  enabled: boolean
  last_run: string | null
  next_run: string | null
}

interface TaskHistory {
  timestamp: string
  status: string
  duration: string
}

interface PresetEntry {
  id: string
  name: string
  description: string
  tasks: string[]
}

export default function AutomationPage() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [presets, setPresets] = useState<PresetEntry[]>([])
  const [schedulerRunning, setSchedulerRunning] = useState(false)
  const [loading, setLoading] = useState(true)
  const [loadingAction, setLoadingAction] = useState<string | null>(null)
  const [result, setResult] = useState<{ key: string; message: string; success: boolean } | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [newName, setNewName] = useState('')
  const [newAction, setNewAction] = useState('cleanup')
  const [newInterval, setNewInterval] = useState('daily')
  const [taskHistory, setTaskHistory] = useState<TaskHistory[]>([])
  const [historyFor, setHistoryFor] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [tasksRes, presetsRes, schedRes] = await Promise.all([
        api.automationTasks(),
        api.automationPresets(),
        api.automationSchedulerStatus(),
      ])
      setTasks(tasksRes.tasks)
      setPresets(presetsRes.presets)
      setSchedulerRunning(schedRes.running)
    } catch {
      setTasks([])
      setPresets([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const runAction = async (key: string, fn: () => Promise<unknown>, successMsg: string) => {
    setLoadingAction(key)
    setResult(null)
    try {
      await fn()
      setResult({ key, message: successMsg, success: true })
      await load()
    } catch (e) {
      setResult({ key, message: e instanceof Error ? e.message : 'Operation failed', success: false })
    } finally {
      setLoadingAction(null)
    }
  }

  const toggleTask = (id: string, enabled: boolean) =>
    runAction(id, () => api.automationToggleTask(id, enabled), `Task ${enabled ? 'enabled' : 'disabled'}`)

  const runTask = (id: string) =>
    runAction(`run-${id}`, () => api.automationRunTask(id), 'Task started')

  const deleteTask = (id: string) =>
    runAction(`del-${id}`, () => api.automationDeleteTask(id), 'Task deleted')

  const createTask = async () => {
    if (!newName.trim()) return
    setLoadingAction('create')
    setResult(null)
    try {
      await api.automationCreateTask(newName.trim(), newAction, newInterval)
      setResult({ key: 'create', message: 'Task created', success: true })
      setShowForm(false)
      setNewName('')
      await load()
    } catch (e) {
      setResult({ key: 'create', message: e instanceof Error ? e.message : 'Failed to create task', success: false })
    } finally {
      setLoadingAction(null)
    }
  }

  const viewHistory = async (id: string) => {
    setHistoryFor(id)
    setLoadingAction(`history-${id}`)
    try {
      const res = await api.automationTaskHistory(id)
      setTaskHistory(res.history)
    } catch {
      setTaskHistory([])
    } finally {
      setLoadingAction(null)
    }
  }

  const toggleScheduler = () => {
    if (schedulerRunning) {
      runAction('sched-stop', () => api.automationSchedulerStop(), 'Scheduler stopped')
    } else {
      runAction('sched-start', () => api.automationSchedulerStart(), 'Scheduler started')
    }
  }

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="page space-y-6">
            <motion.div variants={item}>
        <PageHero
          title="Automation"
          subtitle="Schedule and manage automated optimization tasks"
          icon={<Clock size={19} />}
        />
      </motion.div>

      <motion.div variants={item} className="flex items-center justify-between">
        <div className="flex gap-2">
          <Button variant="primary" icon={<Plus className="w-4 h-4" />} onClick={() => setShowForm(!showForm)}>
            {showForm ? 'Cancel' : 'Add Task'}
          </Button>
          <Button variant="ghost" icon={<RefreshCw className="w-4 h-4" />} onClick={load}>Refresh</Button>
        </div>
        <Button
          variant={schedulerRunning ? 'danger' : 'primary'}
          icon={<Power className="w-4 h-4" />}
          onClick={toggleScheduler}
          loading={loadingAction === 'sched-start' || loadingAction === 'sched-stop'}
        >
          {schedulerRunning ? 'Stop Scheduler' : 'Start Scheduler'}
        </Button>
      </motion.div>

      {showForm && (
        <motion.div variants={item}>
          <Card padding="lg" className="border-accent/30">
            <h2 className="text-sm font-semibold text-text mb-4">New Scheduled Task</h2>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <p className="text-xs font-medium text-text-secondary mb-1">Task Name</p>
                <input type="text" value={newName} onChange={e => setNewName(e.target.value)}
                  placeholder="e.g. Weekly Cleanup"
                  className="w-full px-3 py-2 rounded-lg bg-surface-2 border border-border text-sm text-text placeholder:text-text-tertiary focus:outline-none focus:border-accent" />
              </div>
              <div>
                <p className="text-xs font-medium text-text-secondary mb-1">Action Type</p>
                <select value={newAction} onChange={e => setNewAction(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-surface-2 border border-border text-sm text-text focus:outline-none focus:border-accent">
                  <option value="cleanup">Cleanup</option>
                  <option value="optimize">Optimize</option>
                  <option value="debloat">Debloat</option>
                  <option value="registry">Registry Clean</option>
                  <option value="disk">Disk Cleanup</option>
                </select>
              </div>
              <div>
                <p className="text-xs font-medium text-text-secondary mb-1">Interval</p>
                <select value={newInterval} onChange={e => setNewInterval(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-surface-2 border border-border text-sm text-text focus:outline-none focus:border-accent">
                  <option value="hourly">Hourly</option>
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                </select>
              </div>
              <div className="flex items-end">
                <Button variant="primary" icon={<Save className="w-4 h-4" />} onClick={createTask} loading={loadingAction === 'create'}>Create</Button>
              </div>
            </div>
          </Card>
        </motion.div>
      )}

      <motion.div variants={item}>
        <Card padding="lg">
          <div className="flex items-center gap-2 mb-4">
            <ListOrdered className="w-5 h-5 text-accent" />
            <h2 className="text-sm font-semibold text-text">Scheduled Tasks</h2>
            <Badge>{tasks.length}</Badge>
          </div>
          {loading ? (
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-16 rounded-xl" />)}
            </div>
          ) : tasks.length === 0 ? (
            <p className="text-xs text-text-tertiary py-6 text-center">No tasks scheduled. Create one above.</p>
          ) : (
            <div className="space-y-2">
              {tasks.map(task => (
                <div key={task.id} className="flex items-center justify-between p-3 rounded-xl bg-surface-2/60 hover:bg-surface-2 transition-colors">
                  <div className="flex items-center gap-3 min-w-0 flex-1">
                    <div className={cn('p-2 rounded-lg', task.enabled ? 'bg-green-dim text-green' : 'bg-surface-3 text-text-tertiary')}>
                      <Clock className="w-4 h-4" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-text">{task.name}</p>
                      <div className="flex items-center gap-2 text-xs text-text-secondary">
                        <span>{task.action}</span>
                        <span>•</span>
                        <span>{task.interval}</span>
                        {task.last_run && <><span>•</span><span>Last: {task.last_run}</span></>}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <button onClick={() => toggleTask(task.id, !task.enabled)}
                      className={cn('relative w-9 h-5 rounded-full transition-colors', task.enabled ? 'bg-accent' : 'bg-surface-3')}
                    >
                      <div className={cn('absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform', task.enabled ? 'translate-x-[18px]' : 'translate-x-0.5')} />
                    </button>
                    <Button size="sm" variant="ghost" icon={<Play className="w-3 h-3" />} title="Run Now" onClick={() => runTask(task.id)} loading={loadingAction === `run-${task.id}`} />
                    <Button size="sm" variant="ghost" icon={<History className="w-3 h-3" />} title="History" onClick={() => viewHistory(task.id)} loading={loadingAction === `history-${task.id}`} />
                    <Button size="sm" variant="ghost" icon={<Trash2 className="w-3 h-3" />} title="Delete" onClick={() => deleteTask(task.id)} className="text-red hover:text-red/80" />
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </motion.div>

      {historyFor && taskHistory.length > 0 && (
        <motion.div variants={item}>
          <Card padding="lg">
            <div className="flex items-center gap-2 mb-3">
              <History className="w-5 h-5 text-accent" />
              <h2 className="text-sm font-semibold text-text">Task History</h2>
              <button onClick={() => { setHistoryFor(null); setTaskHistory([]) }} className="ml-auto text-xs text-text-secondary hover:text-text">Close</button>
            </div>
            <div className="space-y-1">
              {taskHistory.map((h, i) => (
                <div key={i} className="flex items-center justify-between p-2 rounded-lg bg-surface-2 text-xs">
                  <span className="text-text-secondary">{h.timestamp}</span>
                  <Badge variant={h.status === 'success' ? 'success' : h.status === 'failed' ? 'danger' : 'warning'}>{h.status}</Badge>
                  <span className="text-text-tertiary">{h.duration}</span>
                </div>
              ))}
            </div>
          </Card>
        </motion.div>
      )}

      <motion.div variants={item}>
        <Card padding="lg">
          <div className="flex items-center gap-2 mb-4">
            <FileText className="w-5 h-5 text-accent" />
            <h2 className="text-sm font-semibold text-text">Preset Configurations</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {(presets.length > 0 ? presets : PRESET_CONFIGS).map(p => (
              <div key={p.id} className="p-4 rounded-xl bg-surface-2/60 border border-border hover:border-accent/30 transition-colors">
                <p className="text-sm font-semibold text-text">{p.name}</p>
                <p className="text-xs text-text-secondary mt-1">{'description' in p ? (p as unknown as {description: string}).description : ''}</p>
                <div className="flex flex-wrap gap-1 mt-2">
                  {p.tasks.map(t => <Badge key={t} className="text-[10px]">{t}</Badge>)}
                </div>
                <Button size="sm" variant="ghost" icon={<Save className="w-3 h-3" />} className="mt-3"
                  onClick={() => runAction(`preset-${p.id}`, () => api.automationApplyPreset(p.id), `${p.name} applied`)}
                  loading={loadingAction === `preset-${p.id}`}>
                  Apply Preset
                </Button>
              </div>
            ))}
          </div>
        </Card>
      </motion.div>

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
