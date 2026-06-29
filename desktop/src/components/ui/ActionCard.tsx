import { type ReactNode } from 'react'
import { motion } from 'framer-motion'
import { cn } from '../../lib/utils'
import { Loader2 } from 'lucide-react'

interface ActionCardProps {
  icon: ReactNode
  title: string
  desc: string
  onClick?: () => void
  variant?: 'default' | 'danger' | 'success'
  className?: string
  tags?: string[]
  loading?: boolean
  disabled?: boolean
}

const variants = {
  default: 'border-border hover:border-accent/50',
  danger: 'border-red/30 hover:border-red/60',
  success: 'border-green/30 hover:border-green/60',
}

export function ActionCard({ icon, title, desc, onClick, variant = 'default', className, tags, loading, disabled }: ActionCardProps) {
  return (
    <motion.div
      whileHover={loading || disabled ? undefined : { y: -3, boxShadow: '0 12px 40px rgba(0,0,0,0.4)' }}
      whileTap={loading || disabled ? undefined : { scale: 0.98 }}
      onClick={onClick}
      className={cn(
        'relative rounded-2xl border bg-surface-1 p-5 cursor-pointer group transition-colors',
        variants[variant],
        loading && 'opacity-60 cursor-not-allowed',
        disabled && 'opacity-40 cursor-not-allowed',
        className
      )}
    >
      <div className="flex items-start gap-4">
        <div className={cn('p-3 rounded-xl bg-surface-2 shrink-0', variant === 'danger' ? 'text-red' : variant === 'success' ? 'text-green' : 'text-accent')}>
          {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : icon}
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-text group-hover:text-accent transition-colors">{title}</h3>
          <p className="text-xs text-text-secondary mt-1 leading-relaxed">{desc}</p>
          {tags && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {tags.map(t => <span key={t} className="px-2 py-0.5 rounded-md bg-surface-3 text-text-tertiary text-[10px] font-medium">{t}</span>)}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  )
}
