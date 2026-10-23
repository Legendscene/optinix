import { useEffect, useId, useMemo, useRef, useState } from 'react'
import { area as d3Area, curveMonotoneX, line as d3Line } from 'd3-shape'
import { interpolateArray } from 'd3-interpolate'
import { scaleLinear } from 'd3-scale'
import { easeCubicOut } from 'd3-ease'
import { prefersReducedMotion } from '../../../hooks/useMotionPreference'
import { cn } from '../../../lib/utils'

export interface StreamSeries {
  key: string
  label: string
  /** Any CSS colour; the gradient fill and head dot derive from it. */
  color: string
  /** Most-recent-last samples. Non-finite entries are dropped defensively. */
  values: number[]
  /** Area fill under this series. Turn off for slow reference lines that
      would otherwise tint the whole plot (disk utilisation, for example). */
  fill?: boolean
}

interface StreamAreaProps {
  series: StreamSeries[]
  height?: number
  /** Fixed top of the y-domain; defaults to a padded data max. */
  yMax?: number
  yMin?: number
  /** Horizontal guide lines drawn behind the data. */
  guides?: number[]
  unit?: string
  ariaLabel?: string
  className?: string
  /** Pulse a dot on the newest sample. */
  showHead?: boolean
  /** One caption per sample, shown as the inspection header (e.g. a clock
      time). Falls back to "sample n/m" when omitted. */
  labels?: string[]
}

const PAD = { top: 10, right: 4, bottom: 4, left: 40 }

/** Replace non-finite samples with the row's previous real value. */
function sanitize(values: number[]): number[] {
  let last = 0
  return values.map((v) => {
    if (Number.isFinite(v)) { last = v; return v }
    return last
  })
}

/** Line up a previous frame with the new data so lengths always match. */
function matchShape(prev: number[][], target: number[][]): number[][] {
  return target.map((t, i) => {
    const p = prev[i]
    if (!p || p.length === 0) return t.map(() => t[0] ?? 0)
    if (p.length === t.length) return p
    if (p.length > t.length) return p.slice(p.length - t.length)
    return [...new Array(t.length - p.length).fill(p[0]), ...p]
  })
}

/**
 * Live multi-series area chart drawn with d3's shape generators.
 *
 * The animation is d3's own mechanism: on every data change the numeric
 * arrays are interpolated with `interpolateArray` over ~420ms and the path is
 * regenerated each frame, so a sample arriving produces a real morph instead
 * of a redrawn picture. Curves use `curveMonotoneX` (never overshoots a
 * measured value).
 *
 * Pointer inspection is included: hovering shows a vertical guide and the
 * exact readings at that sample, so the chart is also a reading tool.
 */
export function StreamArea({
  series, height = 132, yMax, yMin = 0, guides = [25, 50, 75], unit = '%', ariaLabel, className, showHead = true, labels,
}: StreamAreaProps) {
  const uid = useId().replace(/[^a-zA-Z0-9_-]/g, '')
  const hostRef = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(0)
  const [hover, setHover] = useState<number | null>(null)

  /* Width comes from layout, not a guess: d3 scales need real pixels. */
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

  const target = useMemo(() => series.map((s) => sanitize(s.values)), [series])
  const signature = useMemo(
    () => series.map((s) => `${s.key}:${s.values.length}:${s.values.join(',')}`).join('|'),
    [series],
  )

  const [displayed, setDisplayed] = useState<number[][]>(target)
  const displayedRef = useRef<number[][]>(target)
  const frame = useRef(0)

  useEffect(() => {
    const next = series.map((s) => sanitize(s.values))
    const from = matchShape(displayedRef.current, next)

    if (prefersReducedMotion()) {
      displayedRef.current = next
      setDisplayed(next)
      return
    }

    const interps = next.map((row, i) => interpolateArray(from[i] ?? row, row))
    const started = performance.now()
    const duration = 420

    const step = (now: number) => {
      const t = Math.min(1, (now - started) / duration)
      const eased = easeCubicOut(t)
      const out = interps.map((f) => {
        const row = f(eased) as (number | null)[]
        return row.map((v) => (typeof v === 'number' && Number.isFinite(v) ? v : 0))
      })
      displayedRef.current = out
      setDisplayed(out)
      if (t < 1) frame.current = requestAnimationFrame(step)
    }

    frame.current = requestAnimationFrame(step)
    return () => cancelAnimationFrame(frame.current)
    // The signature is the data identity; rebuilding per render would restart
    // the tween on every unrelated parent render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signature])

  useEffect(() => () => cancelAnimationFrame(frame.current), [])

  const points = displayed[0]?.length ?? 0
  const innerW = Math.max(0, width - PAD.left - PAD.right)
  const innerH = Math.max(0, height - PAD.top - PAD.bottom)

  const domainMax = useMemo(() => {
    if (yMax != null) return yMax
    const flat = displayed.flat()
    const m = flat.length ? Math.max(...flat) : 0
    return Math.max(yMin + 1, Math.ceil(m * 1.15))
  }, [displayed, yMax, yMin])

  const x = useMemo(
    () => scaleLinear().domain([0, Math.max(1, points - 1)]).range([0, innerW]),
    [points, innerW],
  )
  const y = useMemo(
    () => scaleLinear().domain([yMin, domainMax]).range([innerH, 0]).nice(),
    [yMin, domainMax, innerH],
  )

  /* Fixed viewport in CSS pixels: strokes and dots keep a constant weight
     instead of scaling with the box. */
  const svgW = width || 640

  const shapes = useMemo(() => {
    const areaGen = d3Area<number>()
      .x((_, i) => x(i))
      .y0(innerH)
      .y1((v) => y(v))
      .curve(curveMonotoneX)
      .defined((v) => Number.isFinite(v))
    const lineGen = d3Line<number>()
      .x((_, i) => x(i))
      .y((v) => y(v))
      .curve(curveMonotoneX)
      .defined((v) => Number.isFinite(v))

    return displayed.map((row) => ({
      area: areaGen(row) ?? '',
      line: lineGen(row) ?? '',
      head: row.length ? { x: x(row.length - 1), y: y(row[row.length - 1]) } : null,
    }))
  }, [displayed, x, y, innerH])

  const latest = series.map((s) => s.values[s.values.length - 1])
  const hoverRow = hover != null ? displayed.map((row) => row[hover]) : null

  return (
    /* `chart-stage` seats the plot on a lit plate: the area fill has a
       surface to glow against instead of floating on the card. */
    <div ref={hostRef} className={cn('chart-stage relative w-full', className)} style={{ height }}>
      <svg
        width={svgW}
        height={height}
        viewBox={`0 0 ${svgW} ${height}`}
        role="img"
        aria-label={ariaLabel ?? `Trend of ${series.map((s) => s.label).join(', ')}`}
        className="block overflow-visible"
        onPointerLeave={() => setHover(null)}
        onPointerMove={(e) => {
          if (points < 2) return
          const rect = e.currentTarget.getBoundingClientRect()
          const px = e.clientX - rect.left - PAD.left
          const i = Math.round((px / Math.max(1, innerW)) * (points - 1))
          setHover(Math.max(0, Math.min(points - 1, i)))
        }}
      >
        <defs>
          {series.map((s, i) => (
            <linearGradient key={s.key} id={`stream-${uid}-${i}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={s.color} stopOpacity={0.2} />
              <stop offset="62%" stopColor={s.color} stopOpacity={0.04} />
              <stop offset="100%" stopColor={s.color} stopOpacity={0} />
            </linearGradient>
          ))}
          <filter id={`head-glow-${uid}`} x="-200%" y="-200%" width="500%" height="500%">
            <feGaussianBlur stdDeviation="2.4" />
          </filter>
        </defs>

        <g transform={`translate(${PAD.left},${PAD.top})`}>
          {/* Guides + scale: a trend without a readable scale is decoration. */}
          {guides.map((g) => {
            const gy = y((g / 100) * domainMax)
            return (
              <g key={g}>
                <line
                  x1={0} x2={innerW} y1={gy} y2={gy}
                  stroke="var(--color-border)" strokeWidth={1} strokeDasharray="2 5"
                />
                <text
                  x={-9} y={gy}
                  textAnchor="end" dominantBaseline="middle"
                  fill="var(--color-text-tertiary)"
                  opacity={0.75}
                  style={{ fontSize: 9, fontVariantNumeric: 'tabular-nums' }}
                >
                  {Math.round((g / 100) * domainMax)}
                </text>
              </g>
            )
          })}

          {displayed.map((_, i) => (
            <g key={series[i]?.key ?? i}>
              {series[i]?.fill !== false && (
                <path d={shapes[i]?.area} fill={`url(#stream-${uid}-${i})`} />
              )}
              <path
                d={shapes[i]?.line}
                fill="none"
                stroke={series[i]?.color}
                strokeWidth={1.6}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </g>
          ))}

          {/* Newest-sample head: a soft glow plus a hard dot. */}
          {showHead && shapes.map((sh, i) => (
            sh.head && series[i] ? (
              <g key={`head-${series[i].key}`}>
                <circle cx={sh.head.x} cy={sh.head.y} r={4} fill={series[i].color} opacity={0.35} filter={`url(#head-glow-${uid})`} />
                <circle cx={sh.head.x} cy={sh.head.y} r={2.1} fill={series[i].color} />
              </g>
            ) : null
          ))}

          {/* Hover guide */}
          {hover != null && hoverRow && points > 1 && (
            <g pointerEvents="none">
              <line
                x1={x(hover)} x2={x(hover)} y1={0} y2={innerH}
                stroke="var(--color-border-light)" strokeWidth={1}
              />
              {hoverRow.map((v, i) => (
                series[i] ? (
                  <circle
                    key={`hv-${series[i].key}`}
                    cx={x(hover)} cy={y(v)} r={2.6}
                    fill="var(--color-surface-1)" stroke={series[i].color} strokeWidth={1.6}
                  />
                ) : null
              ))}
            </g>
          )}
        </g>
      </svg>

      {hover != null && hoverRow && (
        <div
          className="pointer-events-none absolute top-0 z-10 rounded-md border border-border bg-surface-1 px-2 py-1.5 shadow-e2"
          style={{
            left: Math.min(Math.max(0, PAD.left + x(hover) + 10), Math.max(0, svgW - 110)),
          }}
        >
          <div className="text-[10px] text-text-tertiary tnum mb-0.5">
            {labels?.[hover] ?? `sample ${hover + 1}/${points}`}
          </div>
          {hoverRow.map((v, i) => (
            series[i] ? (
              <div key={`tt-${series[i].key}`} className="flex items-center gap-1.5 text-[10.5px] leading-tight">
                <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: series[i].color }} />
                <span className="text-text-tertiary">{series[i].label}</span>
                <span className="text-text tnum ml-auto font-medium">{Math.round(v * 10) / 10}{unit}</span>
              </div>
            ) : null
          ))}
        </div>
      )}

      {!hover && latest.some((v) => Number.isFinite(v)) && (
        <div className="absolute top-0 right-0 flex items-center gap-2.5">
          {series.map((s) => (
            <span key={`lg-${s.key}`} className="flex items-center gap-1 text-[10px] text-text-tertiary">
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: s.color }} />
              {s.label}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
