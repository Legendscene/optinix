import { useState, useEffect, useCallback, useRef } from 'react'
import { api } from '../lib/api'
import type { SystemInfo, SmartDetect } from '../types'

export function useSystemInfo() {
  const [data, setData] = useState<SystemInfo | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const intervalRef = useRef<ReturnType<typeof setInterval>>(undefined)

  const fetch = useCallback(async () => {
    try {
      const d = await api.systemInfo()
      setData(d)
      setError(null)
    } catch (e: unknown) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetch()
    intervalRef.current = setInterval(fetch, 3000)
    return () => clearInterval(intervalRef.current)
  }, [fetch])

  return { data, error, loading }
}

export function useSmartDetect() {
  const [data, setData] = useState<SmartDetect | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.smartDetect().then(setData).catch((e: unknown) => setError((e as Error).message))
  }, [])

  return { data, error }
}

export function useTweakState() {
  const [data, setData] = useState<Record<string, boolean>>({})
  useEffect(() => {
    api.tweakState().then(setData).catch(() => {})
  }, [])
  return data
}
