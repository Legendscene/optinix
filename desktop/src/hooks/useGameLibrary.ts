import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../lib/api'
import type {
  DiscoveredGame, EmulatorEntry, GameExeCandidate, GameLibrary,
  GameProfile, GameScanProgress, GameSessionData,
} from '../types'

/** Owns every piece of state the real game-library page needs: the cached
    scan result, live scan progress (polled), filters, and the per-game
    actions. The backend is the source of truth for statuses — the hook
    renders what the backend said, and never invents a game. */
export type LibraryState = 'loading' | 'ready' | 'error'

export function useGameLibrary() {
  const [state, setState] = useState<LibraryState>('loading')
  const [library, setLibrary] = useState<GameLibrary | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [progress, setProgress] = useState<GameScanProgress | null>(null)
  const [actionMsg, setActionMsg] = useState<string | null>(null)
  /** Per-game busy/action feedback: the id of the last acted-upon game. */
  const [busyGame, setBusyGame] = useState<string | null>(null)
  /** The backend-confirmed applied profile, when any (drives the Revert action). */
  const [appliedProfileId, setAppliedProfileId] = useState<string | null>(null)
  /** Backend-persisted favorite ids — the Gaming Center's pinned games. */
  const [favorites, setFavorites] = useState<Set<string>>(new Set())
  const pollRef = useRef<number | null>(null)

  /** One getter that refreshes the library and reconciles live state. */
  const refresh = useCallback(async () => {
    try {
      const lib = await api.gameLibrary()
      if (lib.needs_scan) {
        // Kick the first scan automatically only once; the UI shows the
        // honest "scan required" state otherwise.
        void api.gameLibraryScan().catch(() => { /* progress handles it */ })
      }
      setLibrary(lib)
      setState('ready')
      setError(null)
    } catch (e) {
      setState('error')
      setError(e instanceof Error ? e.message : String(e))
    }
  }, [])

  const tickProgress = useCallback(async () => {
    try {
      const p = await api.gameLibraryProgress()
      setProgress(p)
      if (!p.running) {
        if (pollRef.current) window.clearInterval(pollRef.current)
        pollRef.current = null
        // Scan finished (or was cancelled) — reload results.
        void refresh()
      }
    } catch {
      /* transient polls may fail while the service restarts; ignore */
    }
  }, [refresh])

  const startPolling = useCallback(() => {
    if (pollRef.current) return
    pollRef.current = window.setInterval(tickProgress, 500)
    void tickProgress()
  }, [tickProgress])

  useEffect(() => {
    void refresh()
    return () => { if (pollRef.current) window.clearInterval(pollRef.current) }
  }, [refresh])

  const scan = useCallback(async () => {
    setActionMsg(null)
    setProgress({ running: true, fraction: 0, games_found: 0, cancel_requested: false })
    startPolling()
    try {
      const r = await api.gameLibraryScan()
      if (!r.started) setActionMsg('Scan already running')
    } catch (e) {
      setProgress(null)
      setActionMsg(e instanceof Error ? e.message : String(e))
    }
  }, [startPolling])

  const cancelScan = useCallback(async () => {
    try { await api.gameLibraryCancel() } catch { /* the poll will settle */ }
  }, [])

  const openFolder = useCallback(async (g: DiscoveredGame) => {
    setBusyGame(g.id)
    setActionMsg(null)
    try {
      await api.gameLibraryOpen(g.id)
      setActionMsg(`Opened installation folder for ${g.name}`)
    } catch (e) {
      setActionMsg(e instanceof Error ? e.message : String(e))
    } finally {
      setBusyGame(null)
    }
  }, [])

  const launch = useCallback(async (g: DiscoveredGame) => {
    setBusyGame(g.id)
    setActionMsg(null)
    try {
      await api.gameLibraryLaunch(g.id)
      setActionMsg(`Launched ${g.name}`)
      void refresh()
    } catch (e) {
      setActionMsg(e instanceof Error ? e.message : String(e))
    } finally {
      setBusyGame(null)
    }
  }, [refresh])

  /** Fetch a profile for preview before applying — the preview shows what
      the backend would actually change, from the backend's own record. */
  const previewProfile = useCallback(async (profileId: string): Promise<GameProfile | null> => {
    try {
      const r = await api.gameProfile(profileId)
      return r.profile
    } catch {
      return null
    }
  }, [])

  /** Apply the game's compatible profile. The backend result decides the
      message: a failing step is reported, never papered over. */
  const applyProfile = useCallback(async (g: DiscoveredGame) => {
    if (!g.profile_id) return
    setBusyGame(g.id)
    setActionMsg(null)
    try {
      const r = await api.applyGameProfile(g.profile_id)
      const okCount = r.results.filter((x) => x.success).length
      const total = r.results.length
      if (okCount === total && total > 0) {
        setAppliedProfileId(g.profile_id)
        setActionMsg(`Applied "${g.profile_id}" profile — ${okCount}/${total} changes succeeded`)
      } else {
        const failures = r.results.filter((x) => !x.success).map((x) => x.message).join('; ')
        setActionMsg(`Profile partially applied (${okCount}/${total}): ${failures}`)
      }
    } catch (e) {
      setActionMsg(e instanceof Error ? e.message : String(e))
    } finally {
      setBusyGame(null)
    }
  }, [])

  /** Revert the last applied profile's reversible changes. */
  const revertProfile = useCallback(async () => {
    setActionMsg(null)
    try {
      const r = await api.revertGameProfile()
      const ok = r.results.every((x) => x.success)
      setAppliedProfileId(null)
      setActionMsg(ok ? 'Game optimizations reverted to defaults' : 'Revert finished with errors — see service log')
    } catch (e) {
      setActionMsg(e instanceof Error ? e.message : String(e))
    }
  }, [])

  /* ---- Favorites (backend-persisted user preference) ---- */

  useEffect(() => {
    api.gameLibraryFavorites()
      .then((r) => setFavorites(new Set(r.favorites)))
      .catch(() => { /* favorites are optional polish */ })
  }, [])

  const toggleFavorite = useCallback(async (g: DiscoveredGame) => {
    const isFav = favorites.has(g.id)
    // Optimistic flip; the backend response is authoritative afterwards.
    setFavorites((prev) => {
      const next = new Set(prev)
      if (isFav) next.delete(g.id)
      else next.add(g.id)
      return next
    })
    try {
      const r = isFav ? await api.gameLibraryFavoriteRemove(g.id) : await api.gameLibraryFavoriteAdd(g.id)
      setFavorites(new Set(r.favorites))
    } catch {
      setFavorites((prev) => {
        const next = new Set(prev)
        if (isFav) next.add(g.id)
        else next.delete(g.id)
        return next
      })
    }
  }, [favorites])

  /* ---- Session detail (one game, polled lightly) ---- */

  const fetchSession = useCallback(async (g: DiscoveredGame): Promise<GameSessionData | null> => {
    try {
      return await api.gameLibrarySession(g.id)
    } catch {
      return null
    }
  }, [])

  /* ---- Manual imports & emulators (Gaming Center V2) ----
     The backend store is the source of truth; the local list refreshes after
     the server confirms each write. */

  const [emulators, setEmulators] = useState<EmulatorEntry[]>([])

  const loadEmulators = useCallback(async () => {
    try {
      const r = await api.gameLibraryEmulators()
      setEmulators(r.emulators)
    } catch {
      /* emulators are additive; the library still renders without them */
    }
  }, [])

  useEffect(() => { void loadEmulators() }, [loadEmulators])

  const addEmulator = useCallback(async (name: string, exePath: string, args = '') => {
    const r = await api.gameLibraryAddEmulator({ name, exe_path: exePath, args })
    void loadEmulators()
    return r
  }, [loadEmulators])

  const removeEmulator = useCallback(async (id: string) => {
    await api.gameLibraryRemoveEmulator(id)
    void loadEmulators()
  }, [loadEmulators])

  const addManualExe = useCallback(async (exePath: string, name: string, emulatorId: string | null) => {
    const r = await api.gameLibraryAddExe({ exe_path: exePath, name, emulator_id: emulatorId })
    void refresh()
    return r
  }, [refresh])

  const addManualFolder = useCallback(async (folder: string, exePath: string, name: string) => {
    const r = await api.gameLibraryAddFolder({ folder, exe_path: exePath, name })
    void refresh()
    return r
  }, [refresh])

  const updateManual = useCallback(async (id: string, fields: { name?: string; args?: string; exe_path?: string; emulator_id?: string | null }) => {
    await api.gameLibraryUpdateManual(id, fields)
    void refresh()
  }, [refresh])

  const removeManual = useCallback(async (id: string) => {
    await api.gameLibraryRemoveManual(id)
    void refresh()
  }, [refresh])

  const scanFolder = useCallback(async (folder: string): Promise<GameExeCandidate[]> => {
    const r = await api.gameLibraryScanFolder(folder)
    return r.candidates
  }, [])

  const resolveShortcut = useCallback(async (lnk: string) => {
    return api.gameLibraryResolveShortcut(lnk)
  }, [])

  const launchManual = useCallback(async (g: DiscoveredGame) => {
    setBusyGame(g.id)
    setActionMsg(null)
    try {
      const r = await api.gameLibraryManualLaunch(g.id)
      if ((r as { created?: boolean }).created) {
        setActionMsg(`Launched ${g.name}`)
        void refresh()
      } else {
        setActionMsg((r as { error?: string }).error || 'Launch failed')
      }
    } catch (e) {
      setActionMsg(e instanceof Error ? e.message : String(e))
    } finally {
      setBusyGame(null)
    }
  }, [refresh])

  return {
    state, library, error,
    progress, actionMsg, busyGame,
    appliedProfileId, favorites, toggleFavorite,
    refresh, scan, cancelScan, openFolder, launch,
    previewProfile, applyProfile, revertProfile, fetchSession,
    /* V2 imports */
    emulators, addEmulator, removeEmulator,
    addManualExe, addManualFolder, updateManual, removeManual, launchManual,
    scanFolder, resolveShortcut,
  }
}
