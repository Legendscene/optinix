import { useCallback, useEffect, useState } from 'react'
import { TOOL_MAP, ZONES, LEGACY_ROUTES, type ZoneId } from '../nav'

const KEY = 'optinix-route'
const HOME = 'home'

const VALID = new Set<string>([HOME, ...ZONES.map((z) => z.id), ...Object.keys(TOOL_MAP)])

/** Resolve retired route ids (stored hashes, backend action targets). */
function resolve(next: string): string {
  return VALID.has(next) ? next : LEGACY_ROUTES[next] ?? next
}

/**
 * Route state with hash sync and browser back/forward support, so the palette
 * and the sidebar are both real navigation rather than local component state.
 */
export function useNavigation(initial = HOME) {
  const [route, setRoute] = useState<string>(() => {
    const fromHash = resolve(window.location.hash.replace(/^#\/?/, ''))
    if (VALID.has(fromHash)) return fromHash
    try {
      const saved = resolve(localStorage.getItem(KEY) ?? '')
      if (saved && VALID.has(saved)) return saved
    } catch {
      /* storage unavailable */
    }
    return initial
  })

  const navigate = useCallback((next: string) => {
    const target = resolve(next)
    if (!VALID.has(target)) return
    next = target
    setRoute(next)
    try {
      localStorage.setItem(KEY, next)
    } catch {
      /* storage unavailable */
    }
    const hash = `#/${next}`
    if (window.location.hash !== hash) {
      window.history.pushState({ route: next }, '', hash)
    }
  }, [])

  useEffect(() => {
    const onPop = () => {
      const fromHash = window.location.hash.replace(/^#\/?/, '')
      if (fromHash && VALID.has(fromHash)) setRoute(fromHash)
    }
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  const goHome = useCallback(() => navigate(HOME), [navigate])
  const goZone = useCallback(
    (zone: ZoneId) => navigate(zone),
    [navigate],
  )

  return { route, navigate, goHome, goZone }
}
