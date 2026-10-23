import { useId, useMemo } from 'react'
import { line as d3Line, curveLinearClosed } from 'd3-shape'
import { cn } from '../../../lib/utils'
import { useTweenValues } from './useTween'

export interface RadarDatum {
  key: string
  label: string
  /** 0-100. */
  value: number
}

interface RadarScoresProps {
  scores: RadarDatum[]
  size?: number
  max?: number
  className?: string
  ariaLabel?: string
}

/**
 * Radar plot of the health dimensions, drawn with d3's closed-line generator.
 *
 * A radar is the right chart here because the question is shape ("where is
 * this machine lopsided?"), not ranking. Values tween with `interpolateArray`
 * so the polygon grows into a new shape after a re-score instead of swapping.
 */
export function RadarScores({ scores, size = 220, max = 100, className, ariaLabel }: RadarScoresProps) {
  const uid = useId().replace(/[^a-zA-Z0-9_-]/g, '')
  const values = useMemo(() => scores.map((s) => Math.max(0, Math.min(max, s.value))), [scores, max])
  /* Starts collapsed so the polygon opens outward on first paint. */
  const shown = useTweenValues(values, 720, { startAtZero: true })

  const n = scores.length
  const cx = size / 2
  const cy = size / 2
  /* Leave room for the labels around the plot. */
  const radius = size / 2 - Math.max(30, size * 0.17)

  const angle = (i: number) => -Math.PI / 2 + (i * 2 * Math.PI) / Math.max(1, n)
  const pointAt = (i: number, ratio: number): [number, number] => {
    const a = angle(i)
    return [cx + Math.cos(a) * radius * ratio, cy + Math.sin(a) * radius * ratio]
  }

  const closed = useMemo(() => d3Line<[number, number]>().x((p) => p[0]).y((p) => p[1]).curve(curveLinearClosed), [])

  const polygon = useMemo(
    () => closed(scores.map((_, i) => pointAt(i, (shown[i] ?? 0) / max))) ?? '',
    // pointAt is derived from stable inputs; recomputing on these is enough
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [closed, shown, max, scores, radius, cx, cy],
  )

  const rings = [0.25, 0.5, 0.75, 1]
  const weakest = scores.length
    ? scores.reduce((a, b) => (b.value < a.value ? b : a))
    : null

  if (!n) {
    return <div className={cn('text-[12px] text-text-tertiary', className)}>No scores yet.</div>
  }

  return (
    <div className={cn('inline-flex flex-col items-center', className)}>
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        role="img"
        aria-label={ariaLabel ?? `Health dimensions: ${scores.map((s) => `${s.label} ${Math.round(s.value)}`).join(', ')}`}
        className="overflow-visible"
      >
        <defs>
          <radialGradient id={`radar-fill-${uid}`} cx="50%" cy="50%" r="50%">
            <stop offset="30%" stopColor="var(--color-accent)" stopOpacity="0.32" />
            <stop offset="100%" stopColor="var(--color-accent)" stopOpacity="0.06" />
          </radialGradient>
        </defs>

        {/* Concentric grid rings. The outermost is solid and slightly
            brighter so the plot has a frame at a glance; the inner rings stay
            dashed and quiet so they read as scale, not as data. */}
        {rings.map((r, idx) => {
          const outer = idx === rings.length - 1
          return (
            <path
              key={r}
              d={closed(scores.map((_, i) => pointAt(i, r))) ?? ''}
              fill={outer ? 'var(--color-surface-1)' : 'none'}
              fillOpacity={outer ? 0.45 : undefined}
              stroke={outer ? 'var(--color-border-light)' : 'var(--color-border)'}
              strokeWidth={outer ? 1.25 : 1}
              strokeDasharray={outer ? undefined : '2 4'}
            />
          )
        })}

        {/* Spokes + labels */}
        {scores.map((s, i) => {
          const [ex, ey] = pointAt(i, 1)
          const [lx, ly] = pointAt(i, 1.2)
          const a = angle(i)
          const cos = Math.cos(a)
          return (
            <g key={s.key}>
              <line x1={cx} y1={cy} x2={ex} y2={ey} stroke="var(--color-border)" strokeWidth={1} />
              <text
                x={lx} y={ly}
                textAnchor={Math.abs(cos) < 0.25 ? 'middle' : cos > 0 ? 'start' : 'end'}
                dominantBaseline="middle"
                fill="var(--color-text-secondary)"
                style={{ fontSize: Math.max(9.5, size * 0.048), fontWeight: 500 }}
              >
                {s.label}
              </text>
            </g>
          )
        })}

        {/* Value polygon */}
        <path
          d={polygon}
          fill={`url(#radar-fill-${uid})`}
          stroke="var(--color-accent)"
          strokeWidth={2}
          strokeLinejoin="round"
          style={{ filter: 'drop-shadow(0 0 6px var(--color-accent-dim))' }}
        />

        {/* Vertices */}
        {scores.map((s, i) => {
          const [vx, vy] = pointAt(i, (shown[i] ?? 0) / max)
          return (
            <g key={`v-${s.key}`}>
              <circle cx={vx} cy={vy} r={3.4} fill="var(--color-surface-0)" stroke="var(--color-accent)" strokeWidth={1.6} />
            </g>
          )
        })}
      </svg>
      {weakest && (
        <p className="text-[10.5px] text-text-tertiary mt-1 text-center">
          Weakest: <span className="text-text-secondary">{weakest.label}</span> · {Math.round(weakest.value)}/100
        </p>
      )}
    </div>
  )
}
