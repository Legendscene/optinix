import { Component, lazy, Suspense, useEffect, useState, type ReactNode } from 'react'
import { FallbackEmblem } from './FallbackEmblem'
import { supportsWebGL } from './support'
import { useMotionPreference } from '../../hooks/useMotionPreference'

/**
 * Host for the 3D hero. Owns every failure path so the pages that use it
 * never have to think about graphics at all:
 *
 *  - no WebGL (tests, ancient GPUs, locked-down VDI)  -> static CSS emblem
 *  - three.js chunk still loading                     -> static CSS emblem
 *  - render error / context lost at runtime          -> static CSS emblem
 *  - reduced motion or hidden tab                    -> scene, not animated
 *    (the scene itself flips frameloop to "never", so zero GPU work)
 *
 * The dynamic import keeps three.js + fiber out of the main bundle;
 * HomePage stays a small first paint.
 */
const HeroScene = lazy(() => import('./HeroScene'))

class SceneBoundary extends Component<
  { children: ReactNode; fallback: ReactNode },
  { failed: boolean }
> {
  state = { failed: false }
  static getDerivedStateFromError() {
    return { failed: true }
  }
  render() {
    return this.state.failed ? this.props.fallback : this.props.children
  }
}

interface HeroExperienceProps {
  /** Canvas box size; parent controls layout. */
  className?: string
  /** Live load, 0..1; drives the emblem's glow and orbital speed. */
  level?: number
}

export function HeroExperience({ className, level = 0.45 }: HeroExperienceProps) {
  /* Probed once per mount: cheap, and the answer cannot change. */
  const [webgl] = useState(() => supportsWebGL())
  const [contextLost, setContextLost] = useState(false)
  const reduced = useMotionPreference()

  /* Safety net for the hidden case: if the scene's own visibilitychange
     listener never fires (e.g. the tab was already hidden at mount),
     the interval still parks the loop. */
  const [hidden, setHidden] = useState(() => document.hidden)
  useEffect(() => {
    const onVis = () => setHidden(document.hidden)
    document.addEventListener('visibilitychange', onVis)
    return () => document.removeEventListener('visibilitychange', onVis)
  }, [])

  if (!webgl || contextLost) {
    return (
      <div className={className}>
        <FallbackEmblem reason={contextLost ? 'context-lost' : 'no-webgl'} />
      </div>
    )
  }

  return (
    <div className={className}>
      <SceneBoundary fallback={<FallbackEmblem reason="context-lost" />}>
        <Suspense fallback={<FallbackEmblem reason="loading" />}>
          <HeroScene active={!reduced && !hidden} level={level} onContextLost={() => setContextLost(true)} />
        </Suspense>
      </SceneBoundary>
    </div>
  )
}
