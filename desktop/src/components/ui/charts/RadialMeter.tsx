import { useId, useMemo } from 'react'
import { arc as d3Arc, type DefaultArcObject } from 'd3-shape'
import { cn } from '../../../lib/utils'
import { useTween } from './useTween'

type Tone = 'auto' | 'accent' | 'good' | 'warn' | 'bad'

const TONE_VAR: Record<Exclude<Tone, 'auto'>, string> = {
  good: 'var(--color-green)',
  warn: 'var(--color-yellow)',
  bad: 'var(--color-red)',
  accent: 'var(--color-accent)',
}

function autoTone(value: number, invert: boolean): Exclude<Tone, 'auto'> {
  const good = invert ? value <= 60 : value >= 85
  const bad = invert ? value >= 85 : value < 45
  if (bad) return 'bad'
  if (good) return 'good'
  return 'warn'
}

const DEG = Math.PI / 180

/* The generators below configure every accessor, so the datum is unused.
   d3-shape still types the call as taking one; this is that placeholder. */
const NO_DATUM: DefaultArcObject = {
  innerRadius: 0, outerRadius: 0, startAngle: 0, endAngle: 0,
}
/** 260-degree sweep, open at the bottom: reads as an instrument dial. */
const START = -130 * DEG
const SWEEP = 260 * DEG
const TICKS = 40

interface RadialMeterProps {
  /** 0-100; null renders the unavailable state instead of a fake zero. */
  value: number | null
  label: string
  size?: number
  tone?: Tone
  /** High is bad (CPU/RAM utilisation) rather than high is good (score). */
  invert?: boolean
  unavailable?: string
  /** Optional caption under the label, e.g. the raw reading. */
  caption?: string
  className?: string
}

/**
 * Radial meter built from d3's arc generator.
 *
 * Three concentric readings: an outer tick ring (coarse, glanceable), the
 * value arc (precise, d3 corner-radius caps) and the numeric readout
 * (exact). Values tween with a d3 ease, so a poll landing 300ms later reads
 * as the needle moving rather than the number being replaced.
 */
export function RadialMeter({
  value, label, size = 120, tone = 'auto', invert = false, unavailable, caption, className,
}: RadialMeterProps) {
  const uid = useId().replace(/[^a-zA-Z0-9_-]/g, '')
  const clamped = value == null ? null : Math.max(0, Math.min(100, value))
  /* Sweeps up from zero on mount, then settles on each new reading. */
  const shown = useTween(clamped ?? 0, 760, 0)
  const fraction = clamped == null ? 0 : shown / 100

  const cx = size / 2
  const cy = size / 2
  const outer = size / 2 - 2
  const ringWidth = Math.max(4, size * 0.052)
  const arcRadius = outer - ringWidth * 1.9
  const tickInner = outer - 4
  const tickOuter = tickInner - Math.max(3, size * 0.026)

  const color = clamped == null
    ? 'var(--color-surface-4)'
    : TONE_VAR[tone === 'auto' ? autoTone(clamped, invert) : tone]

  const valueArc = useMemo(
    () => d3Arc()
      .innerRadius(arcRadius - ringWidth / 2)
      .outerRadius(arcRadius + ringWidth / 2)
      .startAngle(START)
      .endAngle(START + SWEEP * fraction)
      .cornerRadius(ringWidth / 2),
    [arcRadius, ringWidth, fraction],
  )

  const trackArc = useMemo(
    () => d3Arc()
      .innerRadius(arcRadius - ringWidth / 2)
      .outerRadius(arcRadius + ringWidth / 2)
      .startAngle(START)
      .endAngle(START + SWEEP)
      .cornerRadius(ringWidth / 2),
    [arcRadius, ringWidth],
  )

  const ticks = useMemo(() => {
    const out: { x1: number; y1: number; x2: number; y2: number; major: boolean; i: number }[] = []
    for (let i = 0; i < TICKS; i += 1) {
      const a = START + SWEEP * (i / (TICKS - 1))
      const major = i % 5 === 0
      const r2 = major ? tickOuter - 3 : tickOuter
      out.push({
        x1: cx + Math.sin(a) * tickInner,
        y1: cy - Math.cos(a) * tickInner,
        x2: cx + Math.sin(a) * r2,
        y2: cy - Math.cos(a) * r2,
        major,
        i,
      })
    }
    return out
  }, [cx, cy, tickInner, tickOuter])

  const inner = Math.round(size * 0.5)
  const readout = clamped == null ? '—' : Math.round(shown)

  return (
    <div className={cn('relative inline-flex items-center justify-center', className)} style={{ width: size, height: size }}>
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        role="img"
        aria-label={`${label}: ${clamped == null ? unavailable ?? 'unavailable' : `${Math.round(clamped)} percent`}`}
        className="block"
      >
        <defs>
          <radialGradient id={`halo-${uid}`} cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor={color} stopOpacity="0.16" />
            <stop offset="70%" stopColor={color} stopOpacity="0.04" />
            <stop offset="100%" stopColor={color} stopOpacity="0" />
          </radialGradient>
          <linearGradient id={`arc-${uid}`} x1="0" y1="1" x2="1" y2="0">
            <stop offset="0%" stopColor={color} stopOpacity="0.72" />
            <stop offset="100%" stopColor={color} stopOpacity="1" />
          </linearGradient>
        </defs>

        {/* Ambient wash behind the dial: gives the meter depth without a glow. */}
        <circle cx={cx} cy={cy} r={outer} fill={`url(#halo-${uid})`} />

        {/* Tick ring */}
        <g stroke={color === 'var(--color-surface-4)' ? 'var(--color-surface-4)' : color}>
          {ticks.map((t) => (
            <line
              key={t.i}
              x1={t.x1} y1={t.y1} x2={t.x2} y2={t.y2}
              strokeWidth={t.major ? 1.4 : 1}
              strokeLinecap="round"
              opacity={clamped == null ? 0.28 : t.i / (TICKS - 1) <= fraction ? (t.major ? 0.9 : 0.55) : 0.16}
            />
          ))}
        </g>

        {/* Track + value arc. d3.arc emits geometry centred on the origin, so
            these two need the translate the tick ring gets from its maths. */}
        <g transform={`translate(${cx},${cy})`}>
          <path d={trackArc(NO_DATUM) ?? undefined} fill="var(--color-surface-4)" opacity={0.9} />
          {clamped != null && fraction > 0.001 && (
            <path d={valueArc(NO_DATUM) ?? undefined} fill={`url(#arc-${uid})`} />
          )}
        </g>

        {/* Readout: value and unit in one text node so they share a baseline. */}
        <text
          x={cx} y={cy - inner * 0.12}
          textAnchor="middle" dominantBaseline="middle"
          className="tnum"
          fill={clamped == null ? 'var(--color-text-tertiary)' : 'var(--color-text)'}
        >
          <tspan style={{ fontSize: inner * 0.46, fontWeight: 600, letterSpacing: '-0.025em' }}>
            {readout}
          </tspan>
          {clamped != null && (
            <tspan
              dx={1}
              style={{ fontSize: Math.max(9, inner * 0.16), fontWeight: 500 }}
              fill="var(--color-text-tertiary)"
            >
              %
            </tspan>
          )}
        </text>

        {/* Label + caption sit in the dial's bottom gap. */}
        <text
          x={cx} y={cy + inner * 0.4}
          textAnchor="middle" dominantBaseline="middle"
          fill="var(--color-text-tertiary)"
          style={{ fontSize: Math.max(8.5, size * 0.078), fontWeight: 600, letterSpacing: '0.07em' }}
        >
          {label.toUpperCase()}
        </text>
        {caption && (
          <text
            x={cx} y={cy + inner * 0.62}
            textAnchor="middle" dominantBaseline="middle"
            fill="var(--color-text-tertiary)"
            opacity={0.75}
            style={{ fontSize: Math.max(8, size * 0.068) }}
          >
            {caption}
          </text>
        )}
      </svg>
    </div>
  )
}
