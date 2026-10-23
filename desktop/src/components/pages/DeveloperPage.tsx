import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  Terminal, GitBranch, Container, Code2, FolderOpen, Brush,
  Search, Download, Wrench, Package,
} from 'lucide-react'
import { Card } from '../ui/Card'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { ActionCard } from '../ui/ActionCard'
import { Skeleton } from '../ui/Skeleton'
import { MetricCard } from '../ui/MetricCard'
import { PageHero } from '../ui/PageHero'
import { cn } from '../../lib/utils'
import { api } from '../../lib/api'

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.06 } },
}

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
}

const QUICK_TOOLS = [
  { key: 'npm', icon: <Terminal size={20} />, title: 'npm Cache Clean', desc: 'Clear npm cache to free disk space and resolve dependency issues', tags: ['Node.js', 'Cache'] },
  { key: 'pip', icon: <Terminal size={20} />, title: 'pip Cache Clean', desc: 'Remove pip cache and stale wheel files from Python builds', tags: ['Python', 'Cache'] },
  { key: 'git', icon: <GitBranch size={20} />, title: 'Git GC', desc: 'Run garbage collection to optimize repository storage', tags: ['Git', 'Optimization'] },
  { key: 'docker', icon: <Container size={20} />, title: 'Docker Prune', desc: 'Remove unused containers, images, and volumes', tags: ['Docker', 'Cleanup'] },
]

interface DevTool {
  name: string
  version: string | null
  installed: boolean
  category: string
}

interface SearchResult {
  name: string
  version: string
  source: string
}

export function DeveloperPage() {
  const [tools, setTools] = useState<DevTool[]>([])
  const [loadingTools, setLoadingTools] = useState(true)
  const [loadingAction, setLoadingAction] = useState<string | null>(null)
  const [result, setResult] = useState<{ key: string; message: string; success: boolean } | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchSource, setSearchSource] = useState('winget')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [searching, setSearching] = useState(false)

  const loadTools = useCallback(async () => {
    setLoadingTools(true)
    try {
      const res = await api.devToolsList()
      setTools(res.tools)
    } catch {
      setTools([])
    } finally {
      setLoadingTools(false)
    }
  }, [])

  useEffect(() => { loadTools() }, [loadTools])

  const runAction = async (key: string, fn: () => Promise<unknown>, successMsg: string) => {
    setLoadingAction(key)
    setResult(null)
    try {
      await fn()
      setResult({ key, message: successMsg, success: true })
      if (key === 'cache-clean' || key === 'env-repair') await loadTools()
    } catch (e) {
      setResult({ key, message: e instanceof Error ? e.message : 'Operation failed', success: false })
    } finally {
      setLoadingAction(null)
    }
  }

  const doSearch = async () => {
    if (!searchQuery.trim()) return
    setSearching(true)
    try {
      const res = await api.devSearchPackages(searchQuery.trim(), searchSource)
      setSearchResults(res.packages)
    } catch {
      setSearchResults([])
    } finally {
      setSearching(false)
    }
  }

  const installPackage = async (name: string) => {
    runAction(`install-${name}`, () => api.devInstallPackage(name, searchSource), `${name} installation started`)
  }

  const installedCount = tools.filter(t => t.installed).length
  const hasOutdated = tools.some(t => t.installed && !t.version)

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="page space-y-6">
      <motion.div variants={item}>
        <PageHero
          title="Developer Center"
          subtitle="Environment tools, package managers, and dev cache management"
          icon={<Code2 size={19} />}
        />
      </motion.div>

      {!loadingTools && tools.length > 0 && (
        <motion.div variants={item} className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <MetricCard icon={<Code2 className="w-5 h-5" />} label="Dev Tools" value={String(tools.length)} sub={`${installedCount} installed`} />
          <MetricCard icon={<Package className="w-5 h-5" />} label="Package Sources" value="3" sub="winget, choco, npm" />
          <MetricCard icon={<Wrench className="w-5 h-5" />} label="Environment Health" value={hasOutdated ? 'Needs Repair' : 'Good'} trend={hasOutdated ? { value: hasOutdated ? 'Issues' : '', up: false } : undefined} />
        </motion.div>
      )}

      <motion.div variants={item} className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ActionCard
          icon={<Brush size={20} />}
          title="Full Dev Cache Clean"
          desc="Comprehensive cleanup of all build caches, temp files, and dev artifacts"
          tags={['All-in-One']}
          onClick={() => runAction('cache-clean', () => api.devCacheClean(), 'Dev cache cleaned')}
        />
        <ActionCard
          icon={<Wrench size={20} />}
          title="Environment Repair"
          desc="Repair broken PATH entries, re-register tools, fix common environment issues"
          tags={['Repair']}
          variant={hasOutdated ? 'danger' : 'default'}
          onClick={() => runAction('env-repair', () => api.devEnvRepair(), 'Environment repair completed')}
        />
      </motion.div>

      <motion.div variants={item}>
        <Card padding="lg">
          <h2 className="text-sm font-semibold text-text mb-4 flex items-center gap-2"><Search className="w-4 h-4 text-accent" />Package Manager</h2>
          <div className="flex gap-2 mb-4">
            <select value={searchSource} onChange={e => setSearchSource(e.target.value)}
              className="px-3 py-2 rounded-lg bg-surface-2 border border-border text-sm text-text focus:outline-none focus:border-accent">
              <option value="winget">winget</option>
              <option value="choco">Chocolatey</option>
              <option value="npm">npm</option>
            </select>
            <input type="text" value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search packages..."
              onKeyDown={e => e.key === 'Enter' && doSearch()}
              className="flex-1 px-3 py-2 rounded-lg bg-surface-2 border border-border text-sm text-text placeholder:text-text-tertiary focus:outline-none focus:border-accent" />
            <Button variant="primary" icon={<Search className="w-4 h-4" />} onClick={doSearch} loading={searching}>Search</Button>
          </div>
          {searchResults.length > 0 && (
            <div className="divide-y divide-border max-h-48 overflow-y-auto">
              {searchResults.map((pkg, i) => (
                <div key={i} className="flex items-center justify-between py-2 first:pt-0 last:pb-0">
                  <div>
                    <p className="text-sm font-medium text-text">{pkg.name}</p>
                    <p className="text-xs text-text-secondary">{pkg.version} from {pkg.source}</p>
                  </div>
                  <Button size="sm" variant="secondary" icon={<Download className="w-3 h-3" />}
                    loading={loadingAction === `install-${pkg.name}`}
                    onClick={() => installPackage(pkg.name)}>Install</Button>
                </div>
              ))}
            </div>
          )}
          {searching && <div className="py-4 text-center text-xs text-text-tertiary">Searching...</div>}
          {!searching && searchQuery && searchResults.length === 0 && (
            <div className="py-4 text-center text-xs text-text-tertiary">No packages found</div>
          )}
        </Card>
      </motion.div>

      <motion.div variants={item}>
        <Card padding="lg">
          <div className="flex items-center gap-2 mb-4">
            <Code2 className="w-5 h-5 text-accent" />
            <h2 className="text-sm font-semibold text-text">Dev Environment Tools</h2>
            <Badge>{tools.length}</Badge>
          </div>
          {loadingTools ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-16 rounded-xl" />)}
            </div>
          ) : tools.length === 0 ? (
            <p className="text-xs text-text-tertiary py-4 text-center">No dev tools detected. Run environment repair.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {tools.map((tool, i) => (
                <div key={i} className="flex items-center justify-between p-3 rounded-xl bg-surface-2/60">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className={cn('p-2 rounded-lg shrink-0', tool.installed ? 'bg-green-dim text-green' : 'bg-surface-3 text-text-tertiary')}>
                      <Terminal className="w-4 h-4" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-text truncate">{tool.name}</p>
                      <p className="text-xs text-text-secondary">{tool.category}{tool.version ? ` • v${tool.version}` : ''}</p>
                    </div>
                  </div>
                  <Badge variant={tool.installed ? 'success' : 'default'}>{tool.installed ? 'Installed' : 'Missing'}</Badge>
                </div>
              ))}
            </div>
          )}
        </Card>
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {QUICK_TOOLS.map(tool => (
          <ActionCard
            key={tool.key}
            icon={tool.icon}
            title={tool.title}
            desc={tool.desc}
            tags={tool.tags}
            onClick={() => {
              const path = tool.key === 'npm' ? '/api/dev/npm-clean' : tool.key === 'pip' ? '/api/dev/pip-clean' : tool.key === 'git' ? '/api/dev/git-gc' : '/api/dev/docker-prune'
              runAction(tool.key, () => fetch(path, { method: 'POST', signal: AbortSignal.timeout(30000) }), `${tool.title} completed`)
            }}
          />
        ))}
      </motion.div>

      <motion.div variants={item}>
        <Card padding="lg" className="border-dashed border-border">
          <div className="flex items-center gap-3">
            <FolderOpen className="w-5 h-5 text-text-tertiary" />
            <div>
              <h3 className="text-sm font-medium text-text-secondary">Dev Artifacts</h3>
              <p className="text-xs text-text-tertiary mt-0.5">
                Clean up node_modules, .next, dist, build, __pycache__, .cache directories across your workspace
              </p>
            </div>
            <Badge variant="warning">Caution</Badge>
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
    </motion.div>
  )
}
