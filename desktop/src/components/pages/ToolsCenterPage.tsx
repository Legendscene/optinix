import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Briefcase, Settings2, Wifi, Globe, Terminal, FileCode, Activity, Cpu, HardDrive, Search, Play, X, Plus, Check, ToggleLeft, ToggleRight, Monitor, Shield } from 'lucide-react'
import { Card } from '../ui/Card'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { Skeleton } from '../ui/Skeleton'
import { PageHero } from '../ui/PageHero'
import { api } from '../../lib/api'
import type { SystemInfo } from '../../types'

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.04 } } }
const item = { hidden: { opacity: 0, y: 16 }, show: { opacity: 1, y: 0 } }

interface CategoryDef {
  id: string
  label: string
  icon: React.ReactNode
}

const CATEGORIES: CategoryDef[] = [
  { id: 'system', label: 'System Tools', icon: <Settings2 size={16} /> },
  { id: 'network', label: 'Network Tools', icon: <Wifi size={16} /> },
  { id: 'features', label: 'Windows Features', icon: <Globe size={16} /> },
  { id: 'env', label: 'Environment Variables', icon: <Terminal size={16} /> },
  { id: 'hosts', label: 'Hosts File', icon: <FileCode size={16} /> },
  { id: 'processes', label: 'Process Manager', icon: <Activity size={16} /> },
]

const SYSTEM_TOOLS = [
  { id: 'services.msc', name: 'Services Manager', icon: <Settings2 size={18} /> },
  { id: 'taskschd.msc', name: 'Task Scheduler', icon: <Activity size={18} /> },
  { id: 'eventvwr.msc', name: 'Event Viewer', icon: <Activity size={18} /> },
  { id: 'regedit', name: 'Registry Editor', icon: <FileCode size={18} /> },
  { id: 'devmgmt.msc', name: 'Device Manager', icon: <Monitor size={18} /> },
  { id: 'diskmgmt.msc', name: 'Disk Management', icon: <HardDrive size={18} /> },
  { id: 'compmgmt.msc', name: 'Computer Management', icon: <Briefcase size={18} /> },
  { id: 'perfmon.msc', name: 'Performance Monitor', icon: <Activity size={18} /> },
  { id: 'resmon', name: 'Resource Monitor', icon: <Cpu size={18} /> },
  { id: 'msconfig', name: 'System Configuration', icon: <Settings2 size={18} /> },
]

const NETWORK_TOOLS = [
  { id: 'flushdns', name: 'Flush DNS', icon: <Globe size={18} /> },
  { id: 'resetwinsock', name: 'Reset Winsock', icon: <Wifi size={18} /> },
  { id: 'ncpa.cpl', name: 'Network Connections', icon: <Wifi size={18} /> },
  { id: 'wf.msc', name: 'Firewall', icon: <Shield size={18} /> },
]

interface HostEntry {
  line: number
  ip: string
  hostnames: string[]
  enabled: boolean
  comment: string
}

interface ProcessEntry {
  pid: number
  name: string
  cpu_percent: number
  memory_mb: number
}

interface WinFeature {
  name: string
  enabled: boolean
  description?: string
}

export function ToolsCenterPage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const [activeCategory, setActiveCategory] = useState('system')
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState<string | null>(null)
  const [result, setResult] = useState<{ message: string; success: boolean } | null>(null)

  const [envVars, setEnvVars] = useState<{ name: string; value: string }[]>([])
  const [envLoading, setEnvLoading] = useState(false)
  const [envEdit, setEnvEdit] = useState<{ name: string; value: string; scope: string } | null>(null)

  const [hosts, setHosts] = useState<HostEntry[]>([])
  const [hostsLoading, setHostsLoading] = useState(false)
  const [hostForm, setHostForm] = useState({ ip: '', hostname: '', comment: '' })

  const [processes, setProcesses] = useState<ProcessEntry[]>([])
  const [processLoading, setProcessLoading] = useState(false)
  const [processSort, setProcessSort] = useState<'cpu' | 'memory'>('memory')
  const [killConfirm, setKillConfirm] = useState<number | null>(null)

  const [features, setFeatures] = useState<WinFeature[]>([])
  const [featuresLoading, setFeaturesLoading] = useState(false)

  useEffect(() => {
    if (activeCategory === 'env' && envVars.length === 0) fetchEnv()
    else if (activeCategory === 'hosts' && hosts.length === 0) fetchHosts()
    else if (activeCategory === 'processes' && processes.length === 0) fetchProcesses()
    else if (activeCategory === 'features' && features.length === 0) fetchFeatures()
  }, [activeCategory])

  const runTool = async (id: string) => {
    setLoading(id)
    setResult(null)
    try {
      await api.toolsLaunch(id)
      setResult({ message: `Launched ${id}`, success: true })
    } catch (e) {
      setResult({ message: e instanceof Error ? e.message : 'Failed to launch', success: false })
    } finally {
      setLoading(null)
    }
  }

  const runNetworkTool = async (id: string) => {
    setLoading(id)
    setResult(null)
    try {
      if (id === 'flushdns') await api.toolsFlushDns()
      else if (id === 'resetwinsock') await api.toolsResetWinsock()
      else await api.toolsLaunch(id)
      setResult({ message: `${id === 'flushdns' ? 'DNS' : id === 'resetwinsock' ? 'Winsock' : id} executed`, success: true })
    } catch (e) {
      setResult({ message: e instanceof Error ? e.message : 'Failed', success: false })
    } finally {
      setLoading(null)
    }
  }

  const fetchEnv = async () => {
    setEnvLoading(true)
    try {
      const d = await api.toolsEnvList() as { variables: { name: string; value: string }[] }
      setEnvVars(d.variables || [])
    } catch { setEnvVars([]) }
    setEnvLoading(false)
  }

  const addEnv = async () => {
    if (!envEdit) return
    setLoading('env')
    try {
      await api.toolsEnvSet(envEdit.name, envEdit.value, envEdit.scope)
      setEnvEdit(null)
      fetchEnv()
      setResult({ message: 'Environment variable saved', success: true })
    } catch (e) {
      setResult({ message: e instanceof Error ? e.message : 'Failed', success: false })
    }
    setLoading(null)
  }

  const deleteEnv = async (name: string, scope = 'user') => {
    setLoading('env-del')
    try {
      await api.toolsEnvDelete(name, scope)
      fetchEnv()
      setResult({ message: `Deleted ${name}`, success: true })
    } catch (e) {
      setResult({ message: e instanceof Error ? e.message : 'Failed', success: false })
    }
    setLoading(null)
  }

  const fetchHosts = async () => {
    setHostsLoading(true)
    try {
      const d = await api.toolsHostsGet() as { entries: HostEntry[] }
      const entries = (d.entries || []).map((e, i) => ({ ...e, line: e.line ?? i }))
      setHosts(entries)
    } catch { setHosts([]) }
    setHostsLoading(false)
  }

  const addHost = async () => {
    if (!hostForm.ip || !hostForm.hostname) return
    setLoading('host-add')
    try {
      await api.toolsHostsAdd(hostForm.ip, hostForm.hostname, hostForm.comment)
      setHostForm({ ip: '', hostname: '', comment: '' })
      fetchHosts()
      setResult({ message: 'Host entry added', success: true })
    } catch (e) {
      setResult({ message: e instanceof Error ? e.message : 'Failed', success: false })
    }
    setLoading(null)
  }

  const toggleHost = async (line: number) => {
    setLoading('host-toggle')
    try {
      await api.toolsHostsToggle(line)
      fetchHosts()
    } catch { /* ignore */ }
    setLoading(null)
  }

  const removeHost = async (line: number) => {
    setLoading('host-remove')
    try {
      await api.toolsHostsRemove(line)
      fetchHosts()
      setResult({ message: 'Host entry removed', success: true })
    } catch (e) {
      setResult({ message: e instanceof Error ? e.message : 'Failed', success: false })
    }
    setLoading(null)
  }

  const fetchProcesses = async () => {
    setProcessLoading(true)
    try {
      const d = await api.toolsProcesses(processSort) as { processes: ProcessEntry[] }
      setProcesses(d.processes || [])
    } catch { setProcesses([]) }
    setProcessLoading(false)
  }

  const sortProcesses = (sort: 'cpu' | 'memory') => {
    setProcessSort(sort)
    setProcessLoading(true)
    api.toolsProcesses(sort).then(d => {
      setProcesses((d as { processes: ProcessEntry[] }).processes || [])
    }).catch(() => {}).finally(() => setProcessLoading(false))
  }

  const killProcess = async (pid: number) => {
    setLoading(`kill-${pid}`)
    try {
      await api.toolsProcessKill(pid)
      setKillConfirm(null)
      fetchProcesses()
      setResult({ message: `Process ${pid} terminated`, success: true })
    } catch (e) {
      setResult({ message: e instanceof Error ? e.message : 'Failed', success: false })
    }
    setLoading(null)
  }

  const fetchFeatures = async () => {
    setFeaturesLoading(true)
    try {
      const d = await api.toolsWindowsFeatures() as { features: WinFeature[] }
      setFeatures(d.features || [])
    } catch { setFeatures([]) }
    setFeaturesLoading(false)
  }

  const toggleFeature = async (name: string, enable: boolean) => {
    setLoading(`feat-${name}`)
    try {
      if (enable) await api.toolsFeatureEnable(name)
      else await api.toolsFeatureDisable(name)
      setFeatures(prev => prev.map(f => f.name === name ? { ...f, enabled: enable } : f))
      setResult({ message: `${name} ${enable ? 'enabled' : 'disabled'}`, success: true })
    } catch (e) {
      setResult({ message: e instanceof Error ? e.message : 'Failed', success: false })
    }
    setLoading(null)
  }

  if (!systemInfo) {
    return (
      <div className="page space-y-6">
        <div><Skeleton className="h-8 w-48 mb-1" /><Skeleton className="h-4 w-64" /></div>
        <Skeleton className="h-10 rounded-xl" />
        <div className="grid grid-cols-3 gap-4">{Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-28 rounded-xl" />)}</div>
      </div>
    )
  }

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="page space-y-6">
      <motion.div variants={item}>
        <PageHero
          title="Tools Center"
          subtitle="Launch system tools, manage environment variables, hosts, processes, and Windows features"
          icon={<Briefcase size={19} />}
        />
      </motion.div>

      <motion.div variants={item} className="relative max-w-sm">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary" />
        <input
          type="text"
          placeholder="Search tools..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full pl-9 pr-3 py-2 rounded-lg bg-surface-2 border border-border text-text text-sm focus:outline-none focus:border-accent placeholder:text-text-tertiary"
        />
      </motion.div>

      <motion.div variants={item} className="flex flex-wrap gap-1.5">
        {CATEGORIES.map(cat => (
          <button
            key={cat.id}
            onClick={() => setActiveCategory(cat.id)}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeCategory === cat.id
                ? 'bg-accent text-surface-0 shadow-sm'
                : 'text-text-secondary hover:text-text bg-surface-2 hover:bg-surface-3 border border-border'
            }`}
          >
            {cat.icon}
            {cat.label}
          </button>
        ))}
      </motion.div>

      {activeCategory === 'system' && (
        <motion.div variants={item} className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          {SYSTEM_TOOLS.filter(t => !search || t.name.toLowerCase().includes(search.toLowerCase())).map(tool => (
            <Card key={tool.id} padding="md" hover className="flex flex-col items-center gap-2 text-center">
              <div className="p-3 rounded-xl bg-surface-2 text-accent">{tool.icon}</div>
              <span className="text-xs font-medium text-text">{tool.name}</span>
              <Button size="sm" variant="primary" icon={<Play size={12} />} onClick={() => runTool(tool.id)} loading={loading === tool.id}>
                Launch
              </Button>
            </Card>
          ))}
        </motion.div>
      )}

      {activeCategory === 'network' && (
        <motion.div variants={item} className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {NETWORK_TOOLS.filter(t => !search || t.name.toLowerCase().includes(search.toLowerCase())).map(tool => (
            <Card key={tool.id} padding="md" hover className="flex flex-col items-center gap-2 text-center">
              <div className="p-3 rounded-xl bg-surface-2 text-accent">{tool.icon}</div>
              <span className="text-xs font-medium text-text">{tool.name}</span>
              <Button size="sm" variant="primary" icon={<Play size={12} />} onClick={() => runNetworkTool(tool.id)} loading={loading === tool.id}>
                Run
              </Button>
            </Card>
          ))}
        </motion.div>
      )}

      {activeCategory === 'features' && (
        <motion.div variants={item}>
          <Card padding="lg">
            <div className="flex items-center gap-2 mb-4">
              <Globe size={16} className="text-accent" />
              <h2 className="text-sm font-semibold text-text">Windows Features</h2>
              <Button size="sm" variant="ghost" icon={<Settings2 size={12} />} onClick={fetchFeatures} loading={featuresLoading} className="ml-auto">
                Refresh
              </Button>
            </div>
            {featuresLoading ? (
              <div className="space-y-2">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-10 rounded-lg" />)}</div>
            ) : features.length > 0 ? (
              <div className="divide-y divide-border/50">
                {(search ? features.filter(f => f.name.toLowerCase().includes(search.toLowerCase())) : features).map(f => (
                  <div key={f.name} className="flex items-center justify-between py-2.5 px-2">
                    <div>
                      <span className="text-xs text-text font-medium">{f.name}</span>
                      {f.description && <p className="text-[10px] text-text-tertiary mt-0.5">{f.description}</p>}
                    </div>
                    <Button
                      size="sm"
                      variant={f.enabled ? 'danger' : 'primary'}
                      icon={f.enabled ? <ToggleRight size={14} /> : <ToggleLeft size={14} />}
                      onClick={() => toggleFeature(f.name, !f.enabled)}
                      loading={loading === `feat-${f.name}`}
                    >
                      {f.enabled ? 'Disable' : 'Enable'}
                    </Button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2 py-6">
                <Globe size={24} className="text-text-tertiary" />
                <p className="text-xs text-text-secondary">No Windows features data available.</p>
              </div>
            )}
          </Card>
        </motion.div>
      )}

      {activeCategory === 'env' && (
        <motion.div variants={item}>
          <Card padding="lg">
            <div className="flex items-center gap-2 mb-4">
              <Terminal size={16} className="text-accent" />
              <h2 className="text-sm font-semibold text-text">Environment Variables</h2>
              <div className="ml-auto flex items-center gap-2">
                <Button size="sm" variant="ghost" icon={<Settings2 size={12} />} onClick={fetchEnv} loading={envLoading}>Refresh</Button>
                <Button size="sm" variant="primary" icon={<Plus size={12} />} onClick={() => setEnvEdit({ name: '', value: '', scope: 'user' })}>
                  Add
                </Button>
              </div>
            </div>
            {envEdit && (
              <div className="flex items-center gap-2 p-3 mb-3 rounded-lg bg-surface-2 border border-border">
                <input
                  type="text" placeholder="Name"
                  value={envEdit.name}
                  onChange={e => setEnvEdit({ ...envEdit, name: e.target.value })}
                  className="flex-1 px-2 py-1.5 rounded bg-surface-3 border border-border text-text text-xs focus:outline-none focus:border-accent"
                />
                <input
                  type="text" placeholder="Value"
                  value={envEdit.value}
                  onChange={e => setEnvEdit({ ...envEdit, value: e.target.value })}
                  className="flex-[2] px-2 py-1.5 rounded bg-surface-3 border border-border text-text text-xs focus:outline-none focus:border-accent"
                />
                <select
                  value={envEdit.scope}
                  onChange={e => setEnvEdit({ ...envEdit, scope: e.target.value })}
                  className="px-2 py-1.5 rounded bg-surface-3 border border-border text-text text-xs focus:outline-none focus:border-accent"
                >
                  <option value="user">User</option>
                  <option value="system">System</option>
                </select>
                <Button size="sm" variant="primary" icon={<Check size={12} />} onClick={addEnv} loading={loading === 'env'}>Save</Button>
                <Button size="sm" variant="ghost" icon={<X size={12} />} onClick={() => setEnvEdit(null)}>Cancel</Button>
              </div>
            )}
            {envLoading ? (
              <div className="space-y-2">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-9 rounded-lg" />)}</div>
            ) : envVars.length > 0 ? (
              <div className="divide-y divide-border/50 max-h-[500px] overflow-y-auto">
                {(search ? envVars.filter(v => v.name.toLowerCase().includes(search.toLowerCase())) : envVars).map(env => (
                  <div key={env.name} className="flex items-center justify-between py-2 px-2">
                    <div className="flex-1 min-w-0">
                      <span className="text-xs text-text font-medium">{env.name}</span>
                      <p className="text-[10px] text-text-tertiary truncate" title={env.value}>{env.value}</p>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <Button size="sm" variant="ghost" icon={<Settings2 size={11} />} onClick={() => setEnvEdit({ name: env.name, value: env.value, scope: 'user' })} />
                      <Button size="sm" variant="ghost" icon={<X size={11} />} onClick={() => deleteEnv(env.name)} loading={loading === 'env-del'} />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2 py-6">
                <Terminal size={24} className="text-text-tertiary" />
                <p className="text-xs text-text-secondary">No environment variables loaded.</p>
              </div>
            )}
          </Card>
        </motion.div>
      )}

      {activeCategory === 'hosts' && (
        <motion.div variants={item}>
          <Card padding="lg">
            <div className="flex items-center gap-2 mb-4">
              <FileCode size={16} className="text-accent" />
              <h2 className="text-sm font-semibold text-text">Hosts File Editor</h2>
              <Button size="sm" variant="ghost" icon={<Settings2 size={12} />} onClick={fetchHosts} loading={hostsLoading} className="ml-auto">Refresh</Button>
            </div>
            <div className="flex items-center gap-2 p-3 mb-3 rounded-lg bg-surface-2 border border-border">
              <input
                type="text" placeholder="IP address"
                value={hostForm.ip}
                onChange={e => setHostForm({ ...hostForm, ip: e.target.value })}
                className="flex-1 px-2 py-1.5 rounded bg-surface-3 border border-border text-text text-xs focus:outline-none focus:border-accent"
              />
              <input
                type="text" placeholder="Hostname"
                value={hostForm.hostname}
                onChange={e => setHostForm({ ...hostForm, hostname: e.target.value })}
                className="flex-[2] px-2 py-1.5 rounded bg-surface-3 border border-border text-text text-xs focus:outline-none focus:border-accent"
              />
              <input
                type="text" placeholder="Comment (optional)"
                value={hostForm.comment}
                onChange={e => setHostForm({ ...hostForm, comment: e.target.value })}
                className="flex-1 px-2 py-1.5 rounded bg-surface-3 border border-border text-text text-xs focus:outline-none focus:border-accent"
              />
              <Button size="sm" variant="primary" icon={<Plus size={12} />} onClick={addHost} loading={loading === 'host-add'}>Add</Button>
            </div>
            {hostsLoading ? (
              <div className="space-y-2">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-9 rounded-lg" />)}</div>
            ) : hosts.length > 0 ? (
              <div className="divide-y divide-border/50">
                {(search ? hosts.filter(h => h.ip.includes(search) || h.hostnames.some(n => n.includes(search))) : hosts).map(h => (
                  <div key={h.line} className="flex items-center justify-between py-2 px-2">
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <Badge variant={h.enabled ? 'success' : 'default'} className="!text-[10px]">{h.enabled ? 'ON' : 'OFF'}</Badge>
                      <span className="text-xs text-text font-mono">{h.ip}</span>
                      <span className="text-xs text-text-secondary truncate">{h.hostnames.join(', ')}</span>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <Button size="sm" variant="ghost" icon={h.enabled ? <ToggleRight size={12} /> : <ToggleLeft size={12} />} onClick={() => toggleHost(h.line)} loading={loading === 'host-toggle'} title="Toggle" />
                      <Button size="sm" variant="ghost" icon={<X size={11} />} onClick={() => removeHost(h.line)} loading={loading === 'host-remove'} title="Remove" />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2 py-6">
                <FileCode size={24} className="text-text-tertiary" />
                <p className="text-xs text-text-secondary">No hosts entries loaded.</p>
              </div>
            )}
          </Card>
        </motion.div>
      )}

      {activeCategory === 'processes' && (
        <motion.div variants={item}>
          <Card padding="lg">
            <div className="flex items-center gap-2 mb-4">
              <Activity size={16} className="text-accent" />
              <h2 className="text-sm font-semibold text-text">Process Manager</h2>
              <Button size="sm" variant="ghost" icon={<Settings2 size={12} />} onClick={fetchProcesses} loading={processLoading} className="ml-auto">Refresh</Button>
            </div>
            {processLoading ? (
              <div className="space-y-2">{Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="h-9 rounded-lg" />)}</div>
            ) : processes.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-text-tertiary border-b border-border">
                      <th className="text-left py-2 px-2">PID</th>
                      <th className="text-left py-2 px-2">Name</th>
                      <th className="text-right py-2 px-2 cursor-pointer hover:text-text" onClick={() => sortProcesses('cpu')}>CPU% {processSort === 'cpu' && '↓'}</th>
                      <th className="text-right py-2 px-2 cursor-pointer hover:text-text" onClick={() => sortProcesses('memory')}>Memory MB {processSort === 'memory' && '↓'}</th>
                      <th className="text-center py-2 px-2">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(search ? processes.filter(p => p.name.toLowerCase().includes(search.toLowerCase())) : processes).slice(0, 50).map(p => (
                      <tr key={p.pid} className="border-b border-border/50 hover:bg-surface-2/50 transition-colors">
                        <td className="py-1.5 px-2 text-text-tertiary font-mono">{p.pid}</td>
                        <td className="py-1.5 px-2 text-text truncate max-w-[250px]">{p.name}</td>
                        <td className="py-1.5 px-2 text-right font-mono text-text-secondary">{p.cpu_percent?.toFixed(1)}</td>
                        <td className="py-1.5 px-2 text-right font-mono text-text-secondary">{p.memory_mb?.toFixed(0)}</td>
                        <td className="py-1.5 px-2 text-center">
                          {killConfirm === p.pid ? (
                            <div className="flex items-center justify-center gap-1">
                              <Button size="sm" variant="danger" onClick={() => killProcess(p.pid)} loading={loading === `kill-${p.pid}`}>Kill</Button>
                              <Button size="sm" variant="ghost" onClick={() => setKillConfirm(null)}>Cancel</Button>
                            </div>
                          ) : (
                            <Button size="sm" variant="ghost" icon={<X size={12} />} onClick={() => setKillConfirm(p.pid)}>
                              Kill
                            </Button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2 py-6">
                <Activity size={24} className="text-text-tertiary" />
                <p className="text-xs text-text-secondary">No process data available.</p>
              </div>
            )}
          </Card>
        </motion.div>
      )}

      {result && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
          className={`fixed bottom-4 right-4 p-3 rounded-xl border text-xs flex items-center gap-2 ${
            result.success ? 'bg-green-dim border-green/30 text-green' : 'bg-red-dim border-red/30 text-red'
          }`}>
          {result.success ? <Check size={14} /> : <X size={14} />}
          {result.message}
        </motion.div>
      )}
    </motion.div>
  )
}
