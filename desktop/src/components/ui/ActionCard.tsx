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
  default: 'text-accent border-border hover:border-accent/50',
  danger: 'text-red border-red/30 hover:border-red/60',
  success: 'text-green border-green/30 hover:border-green/60',
}

/**
 * Runnable-optimization tile. The tone lives on the icon chip (via
 * currentColor), while the card surface stays neutral — a grid of ten of
 * these should not look like ten different alert levels.
 */
export function ActionCard({ icon, title, desc, onClick, variant = 'default', className, tags, loading, disabled }: ActionCardProps) {
  return (
    <motion.div
      whileHover={loading || disabled ? undefined : { y: -3 }}
      whileTap={loading || disabled ? undefined : { scale: 0.985 }}
      transition={{ type: 'spring', stiffness: 380, damping: 28 }}
      onClick={onClick}
      className={cn(
        'card-depth sheen relative rounded-[var(--radius-card)] border bg-surface-1 p-5 cursor-pointer group transition-colors',
        'shadow-e1 hover:shadow-e2',
        variants[variant],
        loading && 'opacity-60 cursor-not-allowed',
        disabled && 'opacity-40 cursor-not-allowed',
        className
      )}
    >
      <div className="flex items-start gap-3.5">
        <span className="icon-chip h-10 w-10 shrink-0">
          {loading ? <Loader2 className="w-[18px] h-[18px] animate-spin" /> : icon}
        </span>
        <div className="flex-1 min-w-0">
          <h3 className="text-[13.5px] font-semibold text-text group-hover:text-accent transition-colors">{title}</h3>
          <p className="text-[12px] text-text-secondary mt-1 leading-[1.5]">{desc}</p>
          {tags && (
            <div className="flex flex-wrap gap-1.5 mt-2.5">
              {tags.map(t => (
                <span key={t} className="px-2 py-0.5 rounded-md border border-border bg-surface-3/70 text-text-tertiary text-[10px] font-medium">
                  {t}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  )
}
