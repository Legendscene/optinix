import { useState } from 'react'
import { motion } from 'framer-motion'
import { Terminal, GitBranch, Container, Code2, FolderOpen, Brush } from 'lucide-react'
import { Card } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { ActionCard } from '../ui/ActionCard'
import { Skeleton } from '../ui/Skeleton'
import { cn } from '../../lib/utils'
import { api } from '../../lib/api'
import type { SystemInfo } from '../../types'

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.06 } },
}

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
}

const TOOLS = [
  {
    key: 'npm',
    icon: <Terminal size={20} />,
    title: 'npm Cache Clean',
    desc: 'Clear npm cache to free disk space and resolve dependency issues',
    tags: ['Node.js', 'Cache'],
    action: () => post('/api/dev/npm-clean', {}),
    successMsg: 'npm cache cleaned',
  },
  {
    key: 'pip',
    icon: <Terminal size={20} />,
    title: 'pip Cache Clean',
    desc: 'Remove pip cache and stale wheel files from Python builds',
    tags: ['Python', 'Cache'],
    action: () => post('/api/dev/pip-clean', {}),
    successMsg: 'pip cache cleaned',
  },
  {
    key: 'git',
    icon: <GitBranch size={20} />,
    title: 'Git GC',
    desc: 'Run garbage collection to optimize repository storage',
    tags: ['Git', 'Optimization'],
    action: () => post('/api/dev/git-gc', {}),
    successMsg: 'Git garbage collection completed',
  },
  {
    key: 'docker',
    icon: <Container size={20} />,
    title: 'Docker Prune',
    desc: 'Remove unused containers, images, and volumes',
    tags: ['Docker', 'Cleanup'],
    action: () => post('/api/dev/docker-prune', {}),
    successMsg: 'Docker pruned',
  },
]

async function post(path: string, _body: unknown) {
  const r = await fetch(path, { method: 'POST', signal: AbortSignal.timeout(30000) })
  if (!r.ok) throw new Error(`${path}: ${r.status}`)
  return r.json()
}

export function DeveloperPage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const [, setLoadingAction] = useState<string | null>(null)
  const [result, setResult] = useState<{ key: string; message: string; success: boolean } | null>(null)

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

  if (!systemInfo) {
    return (
      <div className="space-y-6">
        <div><Skeleton className="h-8 w-48 mb-1" /><Skeleton className="h-4 w-64" /></div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-32 rounded-xl" />)}
        </div>
      </div>
    )
  }

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-6">
      <motion.div variants={item}>
        <div className="flex items-center gap-3 mb-1">
          <Code2 className="w-6 h-6 text-accent" />
          <h1 className="text-2xl font-bold tracking-tight text-text">Dev Tools</h1>
        </div>
        <p className="text-sm text-text-secondary ml-9">Clean build caches and dev artifacts</p>
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ActionCard
          icon={<Brush size={20} />}
          title="Full Dev Cleanup"
          desc="Comprehensive cleanup of all build caches, temp files, and dev artifacts"
          tags={['All-in-One']}
          onClick={() => runAction('full', () => api.optimize('developer'), 'Full dev cleanup completed')}
        />

        {TOOLS.map(tool => (
          <ActionCard
            key={tool.key}
            icon={tool.icon}
            title={tool.title}
            desc={tool.desc}
            tags={tool.tags}
            onClick={() => runAction(tool.key, tool.action, tool.successMsg)}
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
