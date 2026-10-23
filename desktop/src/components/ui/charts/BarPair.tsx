interface BarPairProps {
  /** Label for the row, e.g. "RAM used". */
  label: string
  before: number
  after: number
  unit?: string
  /** Lower is better (time, bytes used) vs higher is better (score, fps). */
  lowerIsBetter?: boolean
  format?: (v: number) => string
  className?: string
}

function defaultFormat(v: number): string {
  return `${Math.round(v * 10) / 10}`
}

/**
 * Before/after comparison bars for optimization results. The delta chip
 * states direction explicitly (improved/regressed) rather than relying on
 * colour alone, and a zero delta reads "no change" instead of pretending.
 */
export function BarPair({
  label, before, after, unit = '', lowerIsBetter = true, format = defaultFormat, className,
}: BarPairProps) {
  const max = Math.max(before, after, 1)
  const delta = after - before
  const improved = delta === 0 ? null : lowerIsBetter ? delta < 0 : delta > 0
  const pct = before === 0 ? 0 : Math.round((delta / before) * 100)

  const tone =
    improved === null
      ? 'text-text-tertiary bg-surface-3'
      : improved
        ? 'text-green bg-green-dim'
        : 'text-red bg-red-dim'

 const deltaText =
    improved === null
      ? 'no change'
      : `${delta > 0 ? '+' : ''}${format(delta)}${unit} ${improved ? 'improvement' : 'regression'}`

  return (
    <div className={className}>
      <div className="flex items-baseline justify-between gap-3 mb-1.5">
        <span className="text-[12px] text-text-secondary">{label}</span>
        <span className={`text-[10.5px] font-semibold px-1.5 py-0.5 rounded ${tone}`}>
          {improved === null ? 'no change' : `${pct > 0 ? '+' : ''}${pct}%`}
        </span>
      </div>

      <div className="space-y-1">
        <Bar kind="Before" value={before} max={max} accent={false} display={`${format(before)}${unit}`} />
        <Bar kind="After" value={after} max={max} accent display={`${format(after)}${unit}`} />
      </div>

      <span className="sr-only">{deltaText}</span>
    </div>
  )
}

function Bar({ kind, value, max, accent, display }: {
  kind: string
  value: number
  max: number
  accent: boolean
  display: string
}) {
  const width = Math.max(2, (value / max) * 100)
  return (
    <div className="flex items-center gap-2" title={`${kind}: ${display}`}>
      <span className="w-10 shrink-0 text-[10px] text-text-tertiary uppercase tracking-[0.04em]">{kind}</span>
      <div className="flex-1 h-2 rounded-full bg-surface-3 overflow-hidden">
        <div
          className={`h-full rounded-full ${accent ? 'bg-accent' : 'bg-surface-4'}`}
          style={{ width: `${width}%`, transition: 'width 400ms var(--ease-out-quart)' }}
        />
      </div>
      <span className="w-16 shrink-0 text-right text-[11px] font-mono tnum text-text-secondary">{display}</span>
    </div>
  )
}
