import { motion } from 'framer-motion'
import { cn } from '../../lib/utils'

interface ButtonProps {
  children?: string
  onClick?: () => void
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'default'
  size?: 'sm' | 'md' | 'lg'
  className?: string
  loading?: boolean
  disabled?: boolean
  icon?: React.ReactNode
  title?: string
}

const variants = {
  primary: 'bg-accent text-white hover:bg-accent-hover',
  secondary: 'bg-surface-2 text-text hover:bg-surface-3 border border-border',
  ghost: 'text-text-secondary hover:text-text hover:bg-surface-2',
  danger: 'bg-red text-white hover:bg-red/90',
  default: 'bg-accent text-white hover:bg-accent-hover',
}

const sizes = {
  sm: 'px-3 py-1.5 text-xs',
  md: 'px-4 py-2 text-sm',
  lg: 'px-6 py-3 text-base',
}

export function Button({ children, onClick, variant = 'secondary', size = 'sm', className, loading, disabled, icon, title }: ButtonProps) {
  return (
    <motion.button
      whileHover={disabled ? undefined : { scale: 1.02 }}
      whileTap={disabled ? undefined : { scale: 0.98 }}
      onClick={onClick}
      disabled={disabled || loading}
      title={title}
      className={cn(
        'inline-flex items-center gap-2 rounded-lg font-medium transition-colors duration-150',
        'disabled:opacity-40 disabled:cursor-not-allowed',
        variants[variant],
        sizes[size],
        className
      )}
    >
      {loading ? (
        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
      ) : icon}
      {children}
    </motion.button>
  )
}
