import { useState, useEffect, useCallback, useRef } from 'react'
import { api } from '../lib/api'
import type { SystemInfo, SmartDetect } from '../types'

export function useSystemInfo() {
  const [data, setData] = useState<SystemInfo | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const intervalRef = useRef<ReturnType<typeof setInterval>>(undefined)
  const wsRef = useRef<WebSocket | null>(null)
  const [wsConnected, setWsConnected] = useState(false)

  const fetch = useCallback(async () => {
    if (wsConnected) return
    try {
      const d = await api.systemInfo()
      setData(d)
      setError(null)
    } catch (e: unknown) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }, [wsConnected])

  useEffect(() => {
    fetch()
    intervalRef.current = setInterval(fetch, 5000)
    return () => clearInterval(intervalRef.current)
  }, [fetch])

  useEffect(() => {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${proto}//localhost:5000/ws/status`
    const ws = new WebSocket(url)
    wsRef.current = ws
    ws.onopen = () => setWsConnected(true)
    ws.onclose = () => setWsConnected(false)
    ws.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data)
        if (d.error) return
        setData((prev) => {
          if (!prev) return prev
          prev.cpu.percent = d.cpu
          prev.memory.percent = d.memory.percent
          prev.memory.available_gb = d.memory.available / 1073741824
          prev.memory.used_gb = d.memory.used / 1073741824
          prev.memory.total_gb = d.memory.total / 1073741824
          const sys = prev.disk.find(di => di.mountpoint === '/')
          if (sys) { sys.percent = d.disk.percent; sys.used = d.disk.used; sys.free = d.disk.free; sys.total = d.disk.total }
          return { ...prev }
        })
      } catch { /* ignore */ }
    }
    return () => ws.close()
  }, [])

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
