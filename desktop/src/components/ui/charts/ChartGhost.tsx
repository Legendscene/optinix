import { cn } from '../../../lib/utils'

interface ChartGhostProps {
  height?: number
  /** Polls collected so far, shown so the wait is legible. */
  samples?: number
  /** Polls needed before the real plot is drawn. */
  target?: number
  title?: string
  hint?: string
  className?: string
}

/* A fixed, deliberately flat silhouette. It is scaffolding, not a trend: the
   bars never move and never carry a value, so nobody can read a measurement
   out of a panel that has none yet. */
const GHOST_BARS = [16, 21, 18, 26, 23, 30, 26, 34, 29, 38, 33, 42]

/**
 * The designed "no plot yet" state for a chart plate.
 *
 * Before this, a chart with two samples was a nearly empty rectangle and a
 * chart with none was a dashed box with a sentence — both read as unfinished
 * rather than as a measurement in progress. This draws the plate's structure
 * (guides, axis, column rhythm) as a ghost, keeps the poll count visible, and
 * says what is happening in plain words. Pure markup + one CSS pulse that the
 * global reduced-motion rules park, so it costs nothing.
 */
export function ChartGhost({
  height = 200,
  samples = 0,
  target = 6,
  title = 'Waiting for samples',
  hint,
  className,
}: ChartGhostProps) {
  return (
    <div
      className={cn('chart-stage chart-ghost relative w-full overflow-hidden', className)}
      style={{ height }}
      data-testid="chart-ghost"
    >
      <svg
        aria-hidden
        className="absolute inset-0 h-full w-full"
        viewBox="0 0 100 60"
        preserveAspectRatio="none"
      >
        {[15, 30, 45].map((y) => (
          <line
            key={y}
            x1="0"
            x2="100"
            y1={y}
            y2={y}
            vectorEffect="non-scaling-stroke"
            className="ghost-guide"
          />
        ))}
        <line
          x1="0"
          x2="100"
          y1="59"
          y2="59"
          vectorEffect="non-scaling-stroke"
          className="ghost-axis"
        />
        {GHOST_BARS.map((h, i) => (
          <rect
            key={i}
            x={4 + i * 8}
            y={60 - h}
            width="4"
            height={h}
            className="ghost-bar"
          />
        ))}
      </svg>

      <div className="absolute inset-0 flex flex-col items-center justify-center gap-1 px-6 text-center">
        <span
          aria-hidden
          className="animate-pulse-subtle mb-1 h-2 w-2 rounded-full bg-accent"
          style={{ boxShadow: '0 0 12px 2px var(--color-accent-dim)' }}
        />
        <p className="text-[12.5px] font-medium text-text-secondary">{title}</p>
        <p className="text-[11px] text-text-tertiary tnum">
          {samples} of {target} polls collected
        </p>
        {hint && (
          <p className="mt-1 max-w-[46ch] text-[11px] leading-relaxed text-text-tertiary">{hint}</p>
        )}
      </div>
    </div>
  )
}
