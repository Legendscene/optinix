import { useEffect, useRef } from 'react'

/**
 * A ref that is true while the component is mounted.
 *
 * The naive pattern — `useEffect(() => () => { ref.current = false }, [])` —
 * breaks under React StrictMode in dev: cleanup runs, the effect re-invokes,
 * and the ref stays false forever. Every async guard (`if (!mounted.current)
 * return`) then swallows its result and pages sit on their skeletons with the
 * data already loaded. Resetting in the effect body keeps guards valid across
 * the double-invoke. Shared so pages cannot reintroduce the naive version.
 */
export function useMountedRef() {
  const mounted = useRef(true)
  useEffect(() => {
    mounted.current = true
    return () => { mounted.current = false }
  }, [])
  return mounted
}
