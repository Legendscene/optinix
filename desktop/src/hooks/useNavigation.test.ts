import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useNavigation } from './useNavigation'

describe('useNavigation', () => {
  beforeEach(() => {
    localStorage.clear()
    window.history.replaceState(null, '', window.location.pathname)
  })

  it('starts on home by default', () => {
    const { result } = renderHook(() => useNavigation())
    expect(result.current.route).toBe('home')
  })

  it('navigates to a valid destination', () => {
    const { result } = renderHook(() => useNavigation())
    act(() => result.current.navigate('performance'))
    expect(result.current.route).toBe('performance')
  })

  it('maps legacy zone ids to their successors', () => {
    const { result } = renderHook(() => useNavigation())
    /* Old shells stored these ids; the backend still emits `overview`. */
    act(() => result.current.navigate('overview'))
    expect(result.current.route).toBe('home')
    act(() => result.current.navigate('optimize'))
    expect(result.current.route).toBe('optimizer')
    act(() => result.current.navigate('system'))
    expect(result.current.route).toBe('optimizer')
  })

  it('keeps tool ids that share a name with an old zone id', () => {
    const { result } = renderHook(() => useNavigation())
    /* `cleanup` was a zone id and is still a tool id - it must open the tool. */
    act(() => result.current.navigate('cleanup'))
    expect(result.current.route).toBe('cleanup')
  })

  it('rejects unknown routes', () => {
    const { result } = renderHook(() => useNavigation())
    act(() => result.current.navigate('performance'))
    act(() => result.current.navigate('does-not-exist'))
    expect(result.current.route).toBe('performance')
  })

  it('restores a stored valid route on load', () => {
    localStorage.setItem('optinix-route', 'network')
    const { result } = renderHook(() => useNavigation())
    expect(result.current.route).toBe('network')
  })

  it('maps a stored legacy route on load', () => {
    localStorage.setItem('optinix-route', 'overview')
    const { result } = renderHook(() => useNavigation())
    expect(result.current.route).toBe('home')
  })
})
