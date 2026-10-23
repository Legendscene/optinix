import { useEffect, useRef, useState } from 'react'
import { easeCubicOut } from 'd3-ease'
import { interpolateArray, interpolateNumber } from 'd3-interpolate'
import { prefersReducedMotion } from '../../../hooks/useMotionPreference'

/**
 * Animate a number toward `target` with a d3 easing curve.
 *
 * Every chart in the app uses this so a value change reads as one physical
 * motion instead of a jump. Interrupting is safe: a new target starts the
 * tween from wherever the current one had reached, so fast poll cycles never
 * snap backwards.
 *
 * Honours the app/OS reduced-motion setting: when motion is suppressed the
 * value is applied immediately (charts stay correct, they just don't animate).
 *
 * `mountFrom` gives an entrance: the meter starts there and sweeps to the
 * first real reading, which is how an instrument should power on.
 */
export function useTween(target: number, duration = 620, mountFrom?: number): number {
  const [value, setValue] = useState(() =>
    mountFrom != null && !prefersReducedMotion() ? mountFrom : target,
  )
  const current = useRef(mountFrom != null && !prefersReducedMotion() ? mountFrom : target)
  const frame = useRef(0)

  useEffect(() => {
    if (prefersReducedMotion() || duration <= 0 || !Number.isFinite(target)) {
      current.current = target
      setValue(target)
      return
    }

    const from = current.current
    if (Math.abs(from - target) < 0.001) {
      current.current = target
      setValue(target)
      return
    }

    const interp = interpolateNumber(from, target)
    const started = performance.now()

    const step = (now: number) => {
      const t = Math.min(1, (now - started) / duration)
      const next = interp(easeCubicOut(t))
      current.current = next
      setValue(next)
      if (t < 1) frame.current = requestAnimationFrame(step)
      else current.current = target
    }

    frame.current = requestAnimationFrame(step)
    return () => cancelAnimationFrame(frame.current)
  }, [target, duration])

  /* Unmount cleanup for the case where the effect resolves synchronously. */
  useEffect(() => () => cancelAnimationFrame(frame.current), [])

  return value
}

/**
 * Tween a whole series of samples, so a chart with new data morphs into its
 * new shape instead of redrawing.
 *
 * Growing series are left-padded with their own first value before tweening:
 * d3 pads with zero, which would draw a spike from the baseline every time
 * the window gains a sample.
 */
export function useTweenValues(
  target: number[],
  duration = 420,
  options: { startAtZero?: boolean } = {},
): number[] {
  const signature = target.join(',')
  const current = useRef<number[]>(
    options.startAtZero && !prefersReducedMotion() ? target.map(() => 0) : target,
  )
  const [value, setValue] = useState<number[]>(current.current)
  const frame = useRef(0)

  const targetRef = useRef(target)
  targetRef.current = target

  useEffect(() => {
    const next = targetRef.current
    if (prefersReducedMotion()) {
      current.current = next
      setValue(next)
      return
    }

    const prev = current.current
    /* Same length is required for a clean element-wise morph. */
    let from = prev
    if (prev.length !== next.length) {
      from = prev.length > next.length
        ? prev.slice(prev.length - next.length)
        : [...new Array(next.length - prev.length).fill(prev[0] ?? 0), ...prev]
    }
    if (!from.length) {
      current.current = next
      setValue(next)
      return
    }

    const interp = interpolateArray(from, next)
    const started = performance.now()

    const step = (now: number) => {
      const t = Math.min(1, (now - started) / duration)
      const row = (interp(easeCubicOut(t)) as (number | null)[])
        .map((v) => (typeof v === 'number' && Number.isFinite(v) ? v : 0))
      current.current = row
      setValue(row)
      if (t < 1) frame.current = requestAnimationFrame(step)
    }
    frame.current = requestAnimationFrame(step)
    return () => cancelAnimationFrame(frame.current)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signature, duration])

  useEffect(() => () => cancelAnimationFrame(frame.current), [])

  return value
}
