import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import type { SystemInfo } from '../types'

/**
 * One shared system-info subscription for the whole app.
 *
 * Previously every page that wanted a number mounted its own `useSystemInfo`,
 * each with its own 5s interval. A handful of components mounted at once meant
 * duplicate requests, duplicate psutil work in the backend, and a re-render per
 * component per tick. This store polls once and hands the same snapshot down.
 */

const POLL_MS = 4000
const STALE_MS = 15000

type Listener = (info: SystemInfo) => void

let snapshot: SystemInfo | null = null
let timer: ReturnType<typeof setInterval> | undefined
let subscribers = 0
let lastError: string | null = null

const listeners = new Set<Listener>()

async function poll() {
  try {
    const d = await api.systemInfo()
    snapshot = d
    lastError = null
    listeners.forEach((fn) => fn(d))
  } catch (e) {
    lastError = (e as Error).message
  }
}

function start() {
  if (timer) return
  poll()
  timer = setInterval(() => {
    /* Do not burn cycles or battery while the window is in the background. */
    if (document.hidden) return
    poll()
  }, POLL_MS)
}

function stop() {
  if (timer) {
    clearInterval(timer)
    timer = undefined
  }
}

export interface SystemVitals {
  cpu?: number
  ram?: number
  disk?: number
  temp?: number | null
  gpu?: number | null
  stale: boolean
  error: string | null
  snapshot: SystemInfo | null
}

export function useSystemStore(): SystemVitals {
  const [info, setInfo] = useState<SystemInfo | null>(snapshot)
  const [error, setError] = useState<string | null>(lastError)
  const [stale, setStale] = useState(false)

  useEffect(() => {
    subscribers += 1
    start()

    /* Seed new subscribers from the cached snapshot instead of refetching. */
    if (snapshot) setInfo(snapshot)
    listeners.add(setInfo)

    const watch = setInterval(() => {
      const fresh = lastError == null && snapshot != null
      setStale(!fresh)
      if (lastError) setError(lastError)
    }, STALE_MS)

    return () => {
      listeners.delete(setInfo)
      subscribers -= 1
      clearInterval(watch)
      /* Only stop polling once nothing is listening. */
      if (subscribers === 0) stop()
    }
  }, [])

  if (!info) {
    return { stale, error, snapshot: null }
  }

  return {
    cpu: info.cpu?.percent,
    ram: info.memory?.percent,
    disk: Array.isArray(info.disk) ? info.disk[0]?.percent : undefined,
    temp: info.cpu?.temperature ?? info.gpu?.temperature ?? null,
    gpu: info.gpu?.usage ?? null,
    stale,
    error,
    snapshot: info,
  }
}

/** Non-reactive read for code that just needs the latest values. */
export function currentSystemInfo(): SystemInfo | null {
  return snapshot
}
