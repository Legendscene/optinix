import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  Bell, AlertTriangle, AlertCircle, Info, CheckCheck, X, Eye, Clock,
} from 'lucide-react'
import { Card } from '../ui/Card'
import { PageHero } from '../ui/PageHero'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { Skeleton } from '../ui/Skeleton'
import { cn } from '../../lib/utils'
import { api } from '../../lib/api'
import type { SystemInfo, NotificationItem } from '../../types'

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.04 } } }
const item = { hidden: { opacity: 0, y: 16 }, show: { opacity: 1, y: 0 } }

const severityConfig: Record<string, { icon: React.ReactNode; border: string; bg: string; badge: 'danger' | 'warning' | 'info' }> = {
  critical: { icon: <AlertCircle className="w-5 h-5" />, border: 'border-l-red', bg: 'bg-red-dim/5', badge: 'danger' },
  warning: { icon: <AlertTriangle className="w-5 h-5" />, border: 'border-l-yellow', bg: 'bg-yellow-dim/5', badge: 'warning' },
  info: { icon: <Info className="w-5 h-5" />, border: 'border-l-cyan', bg: 'bg-cyan-dim/5', badge: 'info' },
}

const tabs = ['all', 'unread', 'critical', 'warning', 'info'] as const

function relativeTime(ts: number): string {
  const sec = Math.floor((Date.now() - ts) / 1000)
  if (sec < 60) return 'just now'
  const min = Math.floor(sec / 60)
  if (min < 60) return `${min}m ago`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr}h ago`
  const d = Math.floor(hr / 24)
  if (d < 30) return `${d}d ago`
  return new Date(ts).toLocaleDateString()
}

export function NotificationsPage({ systemInfo }: { systemInfo: SystemInfo | null }) {
  const [notifications, setNotifications] = useState<NotificationItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'all' | 'unread' | 'critical' | 'warning' | 'info'>('all')
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  const loadNotifications = useCallback(async () => {
    setError(null)
    try {
      const res = await api.notificationsList()
      setNotifications(res.notifications ?? [])
    } catch {
      setError('Failed to load notifications')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadNotifications()
    const interval = setInterval(loadNotifications, 30000)
    return () => clearInterval(interval)
  }, [loadNotifications])

  const unreadCount = notifications.filter(n => !n.read && !n.dismissed).length

  const filtered = notifications.filter(n => {
    if (activeTab === 'all') return !n.dismissed
    if (activeTab === 'unread') return !n.read && !n.dismissed
    return n.severity === activeTab && !n.dismissed
  })

  const handleMarkRead = async (id: string) => {
    setActionLoading(id)
    try {
      await api.notificationsMarkRead(id)
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n))
    } catch {
      setError('Failed to mark as read')
    } finally {
      setActionLoading(null)
    }
  }

  const handleDismiss = async (id: string) => {
    setActionLoading(id)
    try {
      await api.notificationsDismiss(id)
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, dismissed: true } : n))
    } catch {
      setError('Failed to dismiss notification')
    } finally {
      setActionLoading(null)
    }
  }

  const handleMarkAllRead = async () => {
    setActionLoading('all-read')
    try {
      await api.notificationsMarkAllRead()
      setNotifications(prev => prev.map(n => ({ ...n, read: true })))
    } catch {
      setError('Failed to mark all as read')
    } finally {
      setActionLoading(null)
    }
  }

  const handleDismissAll = async () => {
    setActionLoading('all-dismiss')
    try {
      await api.notificationsDismissAll()
      setNotifications(prev => prev.map(n => ({ ...n, dismissed: true })))
    } catch {
      setError('Failed to dismiss all')
    } finally {
      setActionLoading(null)
    }
  }

  if (!systemInfo) {
    return (
      <div className="page space-y-6">
        <div><Skeleton variant="text" width="200px" height="28px" /><Skeleton variant="text" width="300px" height="16px" className="mt-2" /></div>
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} variant="rectangular" height="72px" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="page space-y-6">
      <motion.div variants={item}>
        <PageHero
          eyebrow="History"
          title="Notification Center"
          subtitle="Alerts the app raised while it ran: what happened, and when. Nothing here is generated after the fact."
          icon={<Bell size={19} />}
          badges={unreadCount > 0 ? <Badge variant="danger">{unreadCount} unread</Badge> : undefined}
          stats={[
            { label: 'Unread', value: String(unreadCount), tone: unreadCount ? 'warn' : 'good' },
            { label: 'Open', value: String(notifications.filter(n => !n.dismissed).length) },
            { label: 'Critical', value: String(notifications.filter(n => n.severity === 'critical' && !n.dismissed).length), tone: 'bad' },
            { label: 'Total', value: String(notifications.length), hint: 'this session' },
          ]}
          actions={
            <>
              <Button
                variant="ghost"
                size="sm"
                icon={actionLoading === 'all-read' ? <Clock className="w-3.5 h-3.5 animate-spin" /> : <CheckCheck className="w-3.5 h-3.5" />}
                onClick={handleMarkAllRead}
                loading={actionLoading === 'all-read'}
                disabled={unreadCount === 0}
              >
                Mark all read
              </Button>
              <Button
                variant="ghost"
                size="sm"
                icon={actionLoading === 'all-dismiss' ? <Clock className="w-3.5 h-3.5 animate-spin" /> : <X className="w-3.5 h-3.5" />}
                onClick={handleDismissAll}
                loading={actionLoading === 'all-dismiss'}
                disabled={notifications.filter(n => !n.dismissed).length === 0}
              >
                Dismiss all
              </Button>
            </>
          }
        />
      </motion.div>

      <motion.div variants={item} className="flex gap-1 p-1 rounded-xl bg-surface-2 w-fit">
        {tabs.map(tab => {
          const count = tab === 'all'
            ? notifications.filter(n => !n.dismissed).length
            : tab === 'unread'
              ? unreadCount
              : notifications.filter(n => n.severity === tab && !n.dismissed).length
          return (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={cn(
                'px-4 py-2 rounded-lg text-sm font-medium transition-all capitalize',
                activeTab === tab
                  ? 'bg-surface-1 text-text shadow-sm'
                  : 'text-text-secondary hover:text-text'
              )}
            >
              {tab}
              {count > 0 && (
                <span className={cn(
                  'ml-2 px-1.5 py-0.5 rounded text-[10px] font-semibold',
                  tab === 'critical' ? 'bg-red-dim text-red' :
                  tab === 'warning' ? 'bg-yellow-dim text-yellow' :
                  tab === 'unread' ? 'bg-accent-dim text-accent' :
                  'bg-surface-3 text-text-secondary'
                )}>
                  {count}
                </span>
              )}
            </button>
          )
        })}
      </motion.div>

      {error && (
        <motion.div variants={item} className="p-4 rounded-xl border border-red/30 bg-red-dim/10">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red" />
            <span className="text-sm text-text">{error}</span>
            <button onClick={() => setError(null)} className="ml-auto p-1 rounded-md hover:bg-surface-2 text-text-secondary"><X className="w-4 h-4" /></button>
          </div>
        </motion.div>
      )}

      {loading ? (
        <motion.div variants={item} className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} variant="rectangular" height="72px" />
          ))}
        </motion.div>
      ) : filtered.length > 0 ? (
        <motion.div variants={item} className="space-y-2">
          {filtered.map((n, i) => {
            const sev = severityConfig[n.severity] ?? severityConfig.info
            const isExpanded = expandedId === n.id
            return (
              <motion.div
                key={n.id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.03 }}
              >
                <Card
                  padding="md"
                  className={cn(
                    'border-l-4 transition-all',
                    sev.border,
                    !n.read && sev.bg,
                    n.read && 'opacity-70'
                  )}
                  onClick={() => setExpandedId(isExpanded ? null : n.id)}
                  hover
                >
                  <div className="flex items-start gap-3">
                    <div className={cn(
                      'p-1.5 rounded-lg shrink-0 mt-0.5',
                      n.severity === 'critical' ? 'text-red bg-red-dim/20' :
                      n.severity === 'warning' ? 'text-yellow bg-yellow-dim/20' :
                      'text-cyan bg-cyan-dim/20'
                    )}>
                      {sev.icon}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className={cn(
                          'text-sm font-medium',
                          n.read ? 'text-text-secondary' : 'text-text'
                        )}>
                          {n.title}
                        </span>
                        {!n.read && <span className="w-2 h-2 rounded-full bg-accent shrink-0" />}
                        <Badge variant={sev.badge} className="ml-auto shrink-0">{n.severity}</Badge>
                      </div>
                      <p className={cn(
                        'text-xs leading-relaxed',
                        n.read ? 'text-text-tertiary' : 'text-text-secondary'
                      )}>
                        {n.message}
                      </p>
                      <div className="flex items-center gap-3 mt-1.5">
                        <div className="flex items-center gap-1 text-[10px] text-text-tertiary">
                          <Clock className="w-3 h-3" />
                          {relativeTime(n.timestamp)}
                        </div>
                      </div>
                      {isExpanded && n.action && (
                        <div className="mt-3 pt-3 border-t border-border">
                          <Button
                            variant="primary"
                            size="sm"
                            onClick={() => { if (n.action) window.open(n.action, '_blank') }}
                          >
                            View Details
                          </Button>
                        </div>
                      )}
                    </div>
                    <div className="flex items-center gap-1 shrink-0" onClick={e => e.stopPropagation()}>
                      {!n.read && (
                        <Button
                          variant="ghost"
                          size="sm"
                          icon={actionLoading === n.id ? <Clock className="w-3 h-3 animate-spin" /> : <Eye className="w-3.5 h-3.5" />}
                          onClick={() => handleMarkRead(n.id)}
                          loading={actionLoading === n.id}
                          title="Mark as read"
                        />
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        icon={<X className="w-3.5 h-3.5" />}
                        onClick={() => handleDismiss(n.id)}
                        loading={actionLoading === n.id}
                        title="Dismiss"
                      />
                    </div>
                  </div>
                </Card>
              </motion.div>
            )
          })}
        </motion.div>
      ) : (
        <motion.div variants={item}>
          <Card padding="lg">
            <div className="flex flex-col items-center gap-3 py-10">
              <div className="p-4 rounded-full bg-surface-3">
                <Bell className="w-10 h-10 text-text-tertiary" />
              </div>
              <p className="text-sm text-text-secondary font-medium">No notifications</p>
              <p className="text-xs text-text-tertiary">You're all caught up</p>
            </div>
          </Card>
        </motion.div>
      )}
    </motion.div>
  )
}
