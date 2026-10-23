import { useMemo } from 'react'
import { scaleLinear } from 'd3-scale'
import { cn } from '../../../lib/utils'
import { useTweenValues } from './useTween'

export interface HBarDatum {
  key: string
  label: string
  value: number
  /** Any CSS colour; defaults to the accent token. */
  color?: string
}

interface HBarsProps {
  data: HBarDatum[]
  /** Fixed maximum; otherwise the largest value sets the scale. */
  max?: number
  format?: (v: number) => string
  className?: string
  /** Accessible summary of every row. */
  ariaLabel?: string
}

const defaultFormat = (v: number) => `${Math.round(v * 10) / 10}`

/**
 * Horizontal bar rows drawn on a d3 linear scale.
 *
 * Horizontal because the labels are words ("Used", "Free", "VRAM") and a
 * rotated axis would make them unreadable; a single d3 scale keeps every row
 * comparable, which is the whole point of a bar chart. Widths tween through
 * `interpolateArray`, so a value change is a bar growing rather than a jump.
 */
export function HBars({ data, max, format = defaultFormat, className, ariaLabel }: HBarsProps) {
  const top = max ?? Math.max(1, ...data.map((d) => d.value))
  const values = useMemo(() => data.map((d) => d.value), [data])
  const shown = useTweenValues(values, 520)

  const scale = useMemo(() => scaleLinear().domain([0, top]).range([0, 100]).clamp(true), [top])

  return (
    <div className={cn('space-y-2.5', className)} role="img" aria-label={ariaLabel ?? 'bar chart'}>
      {data.map((d, i) => {
        const pct = scale(shown[i] ?? 0)
        const color = d.color ?? 'var(--chart-1)'
        return (
          <div key={d.key} className="flex items-center gap-3">
            <span className="w-[74px] shrink-0 truncate text-[11px] text-text-tertiary">{d.label}</span>
            <div className="relative h-2.5 flex-1 overflow-hidden rounded-full bg-surface-3">
              <div
                className="h-full rounded-full"
                style={{
                  width: `${pct}%`,
                  backgroundImage: `linear-gradient(90deg, color-mix(in srgb, ${color} 45%, transparent), ${color})`,
                }}
              />
            </div>
            <span className="w-16 shrink-0 text-right text-[11px] font-medium text-text-secondary tnum">
              {format(d.value)}
            </span>
          </div>
        )
      })}
    </div>
  )
}
