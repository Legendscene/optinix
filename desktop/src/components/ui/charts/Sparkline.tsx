import { useId, useMemo } from 'react'
import { area as d3Area, curveMonotoneX, line as d3Line } from 'd3-shape'
import { scaleLinear } from 'd3-scale'
import { useTweenValues } from './useTween'

interface SparklineProps {
  /** Most-recent-last sample series. Empty renders a flat placeholder. */
  values: number[]
  width?: number
  height?: number
  /** Defaults to the chart-1 token (follows the accent). */
  stroke?: string
  /** Fill the area under the line at low opacity. */
  area?: boolean
  /** Fixed y-domain; otherwise the domain is the data range with padding. */
  min?: number
  max?: number
  className?: string
  /** Accessible summary; omit only when a nearby label states the value. */
  ariaLabel?: string
}

/**
 * Small inline trend line. Pure SVG so it renders identically in the app,
 * in tests, and at any zoom - no chart library, no layout container.
 *
 * Every new sample morphs the curve (d3 `interpolateArray` + `curveMonotoneX`)
 * instead of redrawing a polyline, so a value landing reads as the line
 * settling rather than as a jump to a new picture.
 */
export function Sparkline({
  values,
  width = 96,
  height = 28,
  stroke = 'var(--chart-1)',
  area = true,
  min,
  max,
  className,
  ariaLabel,
}: SparklineProps) {
  const gradientId = useId().replace(/[^a-zA-Z0-9_-]/g, '')
  const shown = useTweenValues(values, 420)

  const path = useMemo(() => {
    if (shown.length < 2) return null
    const lo = min ?? Math.min(...shown)
    const hi = max ?? Math.max(...shown)
    /* A flat series has a zero-height domain; give d3 one unit to map. */
    const top = hi === lo ? lo + 1 : hi
    const pad = 2

    const x = scaleLinear().domain([0, shown.length - 1]).range([pad, width - pad])
    const y = scaleLinear().domain([lo, top]).range([height - pad, pad])

    const line = d3Line<number>()
      .x((_, i) => x(i))
      .y((v) => y(v))
      .curve(curveMonotoneX)

    const fill = d3Area<number>()
      .x((_, i) => x(i))
      .y0(height - 1)
      .y1((v) => y(v))
      .curve(curveMonotoneX)

    return { line: line(shown) ?? '', fill: fill(shown) ?? '' }
  }, [shown, width, height, min, max])

  if (!path) {
    return (
      <svg width={width} height={height} className={className} role="img" aria-label={ariaLabel ?? 'no samples yet'}>
        <line
          x1={2} y1={height / 2} x2={width - 2} y2={height / 2}
          stroke="var(--color-border-light)" strokeWidth={1} strokeDasharray="2 3"
        />
      </svg>
    )
  }

  return (
    <svg
      width={width} height={height} className={className}
      role="img" aria-label={ariaLabel ?? 'trend'}
      viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none"
    >
      {area && (
        <>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={stroke} stopOpacity="0.26" />
              <stop offset="100%" stopColor={stroke} stopOpacity="0" />
            </linearGradient>
          </defs>
          <path d={path.fill} fill={`url(#${gradientId})`} />
        </>
      )}
      <path
        d={path.line} fill="none" stroke={stroke} strokeWidth={1.5}
        strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke"
      />
    </svg>
  )
}
