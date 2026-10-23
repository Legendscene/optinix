import { motion } from 'framer-motion'
import { cn } from '../../lib/utils'

interface ButtonProps {
  /* ReactNode, not string: several pages pass an icon or a conditional
     expression as the only child, which a string-only type rejects. */
  children?: React.ReactNode
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
  // Ink on the brand violet, not white: white only reaches 4.08:1 on
  // --color-accent while near-black clears 4.83:1. Danger is the opposite
  // case, so it keeps white text on a slightly deeper red (4.79:1).
  /* Gradient fill comes from the token ramp, not a per-button pair, so the
     accent presets and the light theme recolour it automatically. */
  primary: 'bg-accent bg-[image:var(--grad-control)] text-on-accent hover:bg-accent-hover shadow-e1 hover:brightness-110',
  secondary: 'bg-surface-2 text-text hover:bg-surface-3 border border-border',
  ghost: 'text-text-secondary hover:text-text hover:bg-surface-2',
  danger: 'bg-red text-white hover:bg-red/90',
  default: 'bg-accent bg-[image:var(--grad-control)] text-on-accent shadow-e1 hover:brightness-110',
}

const sizes = {
  sm: 'px-3 py-1.5 text-xs',
  md: 'px-4 py-2 text-sm',
  lg: 'px-6 py-3 text-base',
}

export function Button({ children, onClick, variant = 'secondary', size = 'sm', className, loading, disabled, icon, title }: ButtonProps) {
  return (
    <motion.button
      type="button"
      whileHover={disabled ? undefined : { scale: 1.02 }}
      whileTap={disabled ? undefined : { scale: 0.98 }}
      onClick={onClick}
      disabled={disabled || loading}
      title={title}
      className={cn(
        'inline-flex items-center gap-2 rounded-[var(--radius-control)] font-medium transition-colors duration-150',
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
