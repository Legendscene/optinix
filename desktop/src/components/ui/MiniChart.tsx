import { useId, useMemo } from 'react'
import { area as d3Area, curveMonotoneX, line as d3Line } from 'd3-shape'
import { scaleLinear } from 'd3-scale'
import { useTweenValues } from './charts/useTween'

interface MiniChartProps {
  data: number[]
  /** Any CSS colour; defaults to the accent token. */
  color?: string
  height?: number
  width?: number
}

/**
 * Inline trend line for a stat tile — d3 geometry, no chart library.
 *
 * Was a raw polyline with a hardcoded violet default. It now shares the
 * Sparkline's approach (monotone curve, gradient fill, tweened samples) so a
 * small trend and a large one are visually the same object.
 */
export function MiniChart({ data, color = 'var(--chart-1)', height = 32, width = 80 }: MiniChartProps) {
  const uid = useId().replace(/[^a-zA-Z0-9_-]/g, '')
  const shown = useTweenValues(data, 420)

  const path = useMemo(() => {
    if (shown.length < 2) return null
    const lo = Math.min(...shown)
    const hi = Math.max(...shown)
    const top = hi === lo ? lo + 1 : hi
    const x = scaleLinear().domain([0, shown.length - 1]).range([1, width - 1])
    const y = scaleLinear().domain([lo, top]).range([height - 2, 2])
    const line = d3Line<number>().x((_, i) => x(i)).y((v) => y(v)).curve(curveMonotoneX)
    const fill = d3Area<number>().x((_, i) => x(i)).y0(height).y1((v) => y(v)).curve(curveMonotoneX)
    return { line: line(shown) ?? '', fill: fill(shown) ?? '' }
  }, [shown, width, height])

  if (!path) return null

  return (
    <svg width={width} height={height} className="flex-shrink-0" aria-hidden focusable="false">
      <defs>
        <linearGradient id={`mini-${uid}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.3" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={path.fill} fill={`url(#mini-${uid})`} />
      <path
        d={path.line} fill="none" stroke={color} strokeWidth={1.6}
        strokeLinecap="round" strokeLinejoin="round"
      />
    </svg>
  )
}
