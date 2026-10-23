import { describe, it, expect } from 'vitest'
import { StrictMode, useEffect, useState } from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { useMountedRef } from './useMountedRef'

/* Mirrors the page pattern this hook exists for: an async load whose result
   is guarded by the mounted ref (HomePage/OverviewPage/GamesPage). */
function Probe() {
  const mounted = useMountedRef()
  const [label, setLabel] = useState('loading')
  useEffect(() => {
    Promise.resolve('loaded').then((v) => {
      if (mounted.current) setLabel(v)
    })
  }, [mounted])
  return <span>{label}</span>
}

describe('useMountedRef', () => {
  it('keeps async guards valid through StrictMode double-invoke', async () => {
    render(
      <StrictMode>
        <Probe />
      </StrictMode>,
    )
    /* Regression this guards: a ref cleared in effect cleanup but never
       reset stays false under StrictMode, so the guard swallows the result
       and the page sits on its skeleton forever. */
    await waitFor(() => expect(screen.getByText('loaded')).toBeInTheDocument())
  })

  it('is false after unmount so late async results are dropped', () => {
    let captured: ReturnType<typeof useMountedRef> | undefined
    function UnmountProbe() {
      captured = useMountedRef()
      return null
    }
    const { unmount } = render(<UnmountProbe />)
    expect(captured!.current).toBe(true)
    unmount()
    expect(captured!.current).toBe(false)
  })
})
