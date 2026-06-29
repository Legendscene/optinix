import { type ReactNode } from 'react'
import { motion } from 'framer-motion'
import { cn } from '../../lib/utils'

interface CardProps {
  children: ReactNode
  className?: string
  hover?: boolean
  glass?: boolean
  onClick?: () => void
  padding?: 'sm' | 'md' | 'lg'
}

const paddings = { sm: 'p-3', md: 'p-4', lg: 'p-6' }

export function Card({ children, className, hover, glass, onClick, padding = 'md' }: CardProps) {
  return (
    <motion.div
      whileHover={hover ? { y: -2, boxShadow: '0 8px 30px rgba(0,0,0,0.3)' } : undefined}
      transition={{ type: 'spring', stiffness: 300, damping: 20 }}
      onClick={onClick}
      className={cn(
        'rounded-xl border border-border bg-surface-1',
        paddings[padding],
        hover && 'cursor-pointer hover:border-border-light',
        glass && 'backdrop-blur-xl bg-surface-1/60',
        className
      )}
    >
      {children}
    </motion.div>
  )
}
