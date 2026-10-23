import { useCallback, useEffect, useState } from 'react'
import { TOOL_MAP } from '../nav'

const FAV_KEY = 'optinix-favorites'
const RECENT_KEY = 'optinix-recents'
const GAME_FAV_KEY = 'optinix-game-favorites'
const RECENT_LIMIT = 8

function readJSON<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key)
    if (!raw) return fallback
    const parsed = JSON.parse(raw)
    return parsed ?? fallback
  } catch {
    return fallback
  }
}

function writeJSON(key: string, value: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    /* storage disabled or full - preferences are not critical */
  }
}

export interface RecentEntry {
  id: string
  at: number
}

export interface Library {
  favorites: string[]
  recents: RecentEntry[]
  /** Game ids the user pinned to the home screen. */
  gameFavorites: string[]
  isFavorite: (id: string) => boolean
  toggleFavorite: (id: string) => void
  isGameFavorite: (id: string) => boolean
  toggleGameFavorite: (id: string) => void
  touch: (id: string) => void
  clearRecents: () => void
}

export function useLibrary(): Library {
  const [favorites, setFavorites] = useState<string[]>(() =>
    readJSON<string[]>(FAV_KEY, []).filter((id) => id in TOOL_MAP),
  )
  const [recents, setRecents] = useState<RecentEntry[]>(() =>
    readJSON<RecentEntry[]>(RECENT_KEY, []).filter((r) => r && r.id in TOOL_MAP),
  )
  const [gameFavorites, setGameFavorites] = useState<string[]>(() =>
    readJSON<string[]>(GAME_FAV_KEY, []),
  )

  useEffect(() => writeJSON(FAV_KEY, favorites), [favorites])
  useEffect(() => writeJSON(RECENT_KEY, recents), [recents])
  useEffect(() => writeJSON(GAME_FAV_KEY, gameFavorites), [gameFavorites])

  const isFavorite = useCallback((id: string) => favorites.includes(id), [favorites])

  const toggleFavorite = useCallback((id: string) => {
    setFavorites((prev) =>
      prev.includes(id) ? prev.filter((f) => f !== id) : [id, ...prev],
    )
  }, [])

  const isGameFavorite = useCallback(
    (id: string) => gameFavorites.includes(id),
    [gameFavorites],
  )

  const toggleGameFavorite = useCallback((id: string) => {
    setGameFavorites((prev) =>
      prev.includes(id) ? prev.filter((g) => g !== id) : [...prev, id],
    )
  }, [])

  const touch = useCallback((id: string) => {
    if (!(id in TOOL_MAP)) return
    setRecents((prev) =>
      [{ id, at: Date.now() }, ...prev.filter((r) => r.id !== id)].slice(0, RECENT_LIMIT),
    )
  }, [])

  const clearRecents = useCallback(() => setRecents([]), [])

  return {
    favorites, recents, gameFavorites,
    isFavorite, toggleFavorite,
    isGameFavorite, toggleGameFavorite,
    touch, clearRecents,
  }
}
