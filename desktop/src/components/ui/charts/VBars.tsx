import { useEffect, useMemo, useRef, useState } from 'react'
import { scaleBand, scaleLinear } from 'd3-scale'
import { cn } from '../../../lib/utils'
import { useTweenValues } from './useTween'

export interface VBarDatum {
  key: string
  label: string
  value: number
}

interface VBarsProps {
  data: VBarDatum[]
  height?: number
  /** Fixed top of the y-domain; otherwise a padded data max. */
  yMax?: number
  /** Any CSS colour; defaults to the accent token. */
  color?: string
  format?: (v: number) => string
  className?: string
  ariaLabel?: string
}

const PAD = { top: 8, right: 4, bottom: 18, left: 34 }

/**
 * Vertical bars for values that happened at discrete moments (one boot, one
 * scan, one run) rather than as a continuous stream — a line would imply
 * interpolation between two measurements that never existed.
 *
 * d3's band scale keeps the bars evenly spaced no matter how many arrive, and
 * the heights tween through the same `interpolateArray` pass as every other
 * chart, so a new event grows in instead of appearing.
 */
export function VBars({
  data, height = 220, yMax, color = 'var(--chart-1)', format = (v) => `${Math.round(v * 10) / 10}`, className, ariaLabel,
}: VBarsProps) {
  const hostRef = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(0)

  useEffect(() => {
    const el = hostRef.current
    if (!el) return
    const ro = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width ?? 0
      setWidth((prev) => (Math.abs(prev - w) > 0.5 ? w : prev))
    })
    ro.observe(el)
    setWidth(el.clientWidth)
    return () => ro.disconnect()
  }, [])

  const values = useMemo(() => data.map((d) => d.value), [data])
  const shown = useTweenValues(values, 460)

  const innerW = Math.max(0, width - PAD.left - PAD.right)
  const innerH = Math.max(0, height - PAD.top - PAD.bottom)
  const top = yMax ?? Math.max(1, Math.ceil(Math.max(...values, 0) * 1.15))

  const x = useMemo(
    () => scaleBand<number>().domain(data.map((_, i) => i)).range([0, innerW]).paddingInner(0.34).paddingOuter(0.12),
    [data, innerW],
  )
  const y = useMemo(() => scaleLinear().domain([0, top]).range([innerH, 0]), [top, innerH])

  /* Two gridlines are enough to read the scale without turning the plot into
     graph paper. */
  const grid = [0.5, 1].map((f) => ({ v: top * f, y: y(top * f) }))

  const svgW = width || 640
  const labelEvery = Math.max(1, Math.ceil(data.length / Math.max(2, Math.floor(innerW / 62))))

  if (!data.length) {
    return (
      <div className={cn('flex items-center justify-center text-[12px] text-text-tertiary', className)} style={{ height }}>
        No samples
      </div>
    )
  }

  return (
    <div ref={hostRef} className={cn('relative w-full', className)} style={{ height }}>
      <svg
        width={svgW}
        height={height}
        viewBox={`0 0 ${svgW} ${height}`}
        role="img"
        aria-label={ariaLabel ?? `${data.length} bars, latest ${format(values[values.length - 1] ?? 0)}`}
        className="block"
      >
        <g transform={`translate(${PAD.left},${PAD.top})`}>
          {grid.map((g) => (
            <g key={g.v}>
              <line x1={0} x2={innerW} y1={g.y} y2={g.y} stroke="var(--color-border)" strokeDasharray="2 5" />
              <text
                x={-8} y={g.y} textAnchor="end" dominantBaseline="middle"
                fill="var(--color-text-tertiary)" opacity={0.8}
                style={{ fontSize: 9, fontVariantNumeric: 'tabular-nums' }}
              >
                {Math.round(g.v)}
              </text>
            </g>
          ))}

          {data.map((d, i) => {
            const bx = x(i) ?? 0
            const bw = x.bandwidth()
            const h = Math.max(2, innerH - y(shown[i] ?? 0))
            return (
              <g key={d.key}>
                <rect
                  x={bx} y={innerH - h} width={bw} height={h}
                  rx={Math.min(4, bw / 3)}
                  fill={color} opacity={0.85}
                >
                  <title>{`${d.label}: ${format(d.value)}`}</title>
                </rect>
                {i % labelEvery === 0 && (
                  <text
                    x={bx + bw / 2} y={innerH + 12}
                    textAnchor="middle"
                    fill="var(--color-text-tertiary)"
                    style={{ fontSize: 9 }}
                  >
                    {d.label}
                  </text>
                )}
              </g>
            )
          })}
        </g>
      </svg>
    </div>
  )
}
