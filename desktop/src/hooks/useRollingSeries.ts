import { useRef, useState } from 'react'

/**
 * Rolling history built from readings the app has already polled.
 *
 * Pages that show a trend need more than one number. The shared system store
 * re-renders every page with a fresh snapshot every few seconds, so the honest
 * series is "the values we actually observed", not a random walk. This hook
 * appends the current reading each time `tick` changes (pass the snapshot
 * object itself) and keeps the last `length` samples.
 *
 * No fetching and no synthesis: if the value is missing the series simply does
 * not advance, which is why callers should render a "collecting" state while
 * `samples.length < 2` rather than a fabricated line.
 */
export function useRollingSeries(
  value: number | null | undefined,
  tick: unknown,
  length = 40,
): number[] {
  const [samples, setSamples] = useState<number[]>([])
  const lastTick = useRef<unknown>(tick)

  /* Adjustment during render (not an effect) so the first paint after a new
     snapshot already includes that reading — no one-frame lag. */
  if (tick !== lastTick.current) {
    lastTick.current = tick
    if (typeof value === 'number' && Number.isFinite(value)) {
      /* Every poll is appended, including a repeated reading. An idle core
         really does sit at 0% for minutes, and a flat line says that honestly;
         de-duplicating repeats would leave the chart empty on an idle machine. */
      const prev = samples
      const next = prev.length >= length ? prev.slice(prev.length - length + 1) : prev.slice()
      next.push(value)
      setSamples(next)
    }
  }

  return samples
}
