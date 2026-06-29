import { cn } from '../../lib/utils'

interface SkeletonProps {
  className?: string
  variant?: 'text' | 'circular' | 'rectangular'
  width?: string
  height?: string
}

export function Skeleton({ className, variant = 'text', width, height }: SkeletonProps) {
  return (
    <div
      className={cn(
        'animate-pulse-subtle bg-surface-3',
        variant === 'circular' ? 'rounded-full' : variant === 'text' ? 'rounded-md h-4' : 'rounded-xl',
        className
      )}
      style={{ width, height }}
    />
  )
}
