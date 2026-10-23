interface GaugeProps {
  /** 0-100. Values outside are clamped. */
  value: number | null
  label: string
  /** Shown under the value when the sensor is missing. */
  unavailable?: string
  size?: number
  /** Semantic tone for the arc; defaults to value-derived thresholds. */
  tone?: 'auto' | 'accent' | 'good' | 'warn' | 'bad'
  /** Flip the auto thresholds: pass for utilization metrics where high
      is bad (CPU/RAM), leave off for scores where high is good. */
  invert?: boolean
  className?: string
}

const TONE_VAR: Record<'good' | 'warn' | 'bad' | 'accent', string> = {
  good: 'var(--color-green)',
  warn: 'var(--color-yellow)',
  bad: 'var(--color-red)',
  accent: 'var(--color-accent)',
}

function autoTone(value: number, invert: boolean): 'good' | 'warn' | 'bad' {
  const good = invert ? value <= 60 : value >= 85
  const bad = invert ? value >= 85 : value < 45
  if (bad) return 'bad'
  if (good) return 'good'
  return 'warn'
}

/**
 * Arc meter for a single percentage. Reads like an instrument: track,
 * value arc, big tabular number in the middle, no glow.
 */
export function Gauge({
  value, label, unavailable, size = 96, tone = 'auto', invert = false, className,
}: GaugeProps) {
  const clamped = value == null ? null : Math.max(0, Math.min(100, value))
  const stroke = 7
  const r = (size - stroke) / 2
  const cx = size / 2
  const cy = size / 2
  /* 240-degree sweep, open at the bottom. */
  const sweep = 240
  const start = -210
  const circumference = 2 * Math.PI * r
  const arcLen = (sweep / 360) * circumference
  const fillLen = clamped == null ? 0 : (clamped / 100) * arcLen
  const color = clamped == null
    ? 'var(--color-border-light)'
    : TONE_VAR[tone === 'auto' ? autoTone(clamped, invert) : tone]

  return (
    <div className={`flex flex-col items-center ${className ?? ''}`}>
      <svg width={size} height={size * 0.78} viewBox={`0 0 ${size} ${size * 0.78}`} role="img" aria-label={`${label}: ${clamped == null ? unavailable ?? 'unavailable' : `${Math.round(clamped)}%`}`}>
        <g transform={`rotate(${start} ${cx} ${cy})`}>
          <circle
            cx={cx} cy={cy} r={r} fill="none"
            stroke="var(--color-surface-4)" strokeWidth={stroke} strokeLinecap="round"
            strokeDasharray={`${arcLen} ${circumference}`}
          />
          {clamped != null && (
            <circle
              cx={cx} cy={cy} r={r} fill="none"
              stroke={color} strokeWidth={stroke} strokeLinecap="round"
              strokeDasharray={`${fillLen} ${circumference}`}
              style={{ transition: 'stroke-dasharray 400ms var(--ease-out-quart)' }}
            />
          )}
        </g>
        <text
          x={cx} y={cy - 2} textAnchor="middle"
          fill={clamped == null ? 'var(--color-text-tertiary)' : 'var(--color-text)'}
          style={{ font: `600 ${size * 0.26}px var(--font-mono)`, fontVariantNumeric: 'tabular-nums' }}
        >
          {clamped == null ? '—' : `${Math.round(clamped)}`}
        </text>
      </svg>
      <span className="text-[11px] font-medium text-text-secondary -mt-1">{label}</span>
      {clamped == null && unavailable && (
        <span className="text-[10px] text-text-tertiary text-center max-w-[120px]">{unavailable}</span>
      )}
    </div>
  )
}
