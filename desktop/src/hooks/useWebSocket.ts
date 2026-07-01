import { useEffect, useRef, useState, useCallback } from 'react'

interface SystemStatus {
  cpu: number
  memory: { total: number; available: number; used: number; percent: number }
  disk: { total: number; used: number; free: number; percent: number }
  gpu: { load: number; memory_used: number; memory_total: number; temperature: number } | null
  processes: number
  uptime: number
  timestamp: number
}

export function useWebSocket(onStatus?: (status: SystemStatus) => void) {
  const [connected, setConnected] = useState(false)
  const [status, setStatus] = useState<SystemStatus | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const cbRef = useRef(onStatus)
  cbRef.current = onStatus

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${proto}//localhost:5000/ws/status`
    const ws = new WebSocket(url)
    ws.onopen = () => setConnected(true)
    ws.onclose = () => setConnected(false)
    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data) as SystemStatus
        setStatus(data)
        cbRef.current?.(data)
      } catch { /* ignore */ }
    }
    ws.onerror = () => setConnected(false)
    wsRef.current = ws
  }, [])

  const disconnect = useCallback(() => {
    wsRef.current?.close()
    wsRef.current = null
    setConnected(false)
  }, [])

  useEffect(() => {
    return () => disconnect()
  }, [disconnect])

  return { connected, status, connect, disconnect }
}
