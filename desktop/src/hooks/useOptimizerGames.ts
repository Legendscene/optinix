import { useCallback, useEffect, useState } from 'react'
import { api } from '../lib/api'
import type { GameProfileSummary, InstalledGamesSet } from '../types'

/** A profile card may carry the scan's appid for cover art. */
export type GameProfile = GameProfileSummary & { appid?: number }

/** Which game profile the user applied through this session. */
export interface ProfileFeed {
  id: string
  rows: { success: boolean; message: string }[]
}

interface GamesState {
  state: 'loading' | 'ready' | 'error'
  matched: InstalledGamesSet['matched']
  others: InstalledGamesSet['others']
}

/** One owner for everything the Games section needs: the installed-game scan,
    the profile list, and the apply/revert actions. The page renders what this
    returns; the hook owns how the data got there.
    Catches fire independently so a failed scan cannot matter to the profile
    list, and vice versa. */
export function useOptimizerGames() {
  const [profiles, setProfiles] = useState<GameProfileSummary[] | null>(null)
  const [games, setGames] = useState<GamesState>({
    state: 'loading', matched: [], others: [],
  })
  const [detected, setDetected] = useState<{ id?: string; name?: string; appid?: number } | null>(null)
  const [appliedId, setAppliedId] = useState<string | null>(null)
  const [applyFeed, setApplyFeed] = useState<ProfileFeed | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    /* Both sources must agree for the section to show games: a failed scan
       must not fall back to showing every profile — that would break the
       "only installed games" contract. */
    Promise.all([
      api.gameProfiles().catch(() => null),
      api.installedGames().catch(() => null),
    ]).then(([pr, inst]) => {
      if (!alive) return
      if (!pr || !inst) {
        setGames((g) => ({ ...g, state: 'error' }))
        return
      }
      setProfiles(pr.profiles)
      setGames((g) => ({
        ...g,
        state: 'ready',
        matched: inst.matched,
        others: inst.others,
      }))
    })
    api.detectGame().then((d) => {
      if (!alive) return
      /* Detection only ever adds the marker; it can never invent a game. */
      setDetected(d.detected ? { id: d.game_id, name: d.game_name, appid: d.appid } : null)
    }).catch(() => { /* the marker stays off; nothing is claimed */ })
    return () => { alive = false }
  }, [])

  /* Only games the scan found installed on this PC. The detected (running)
     game keeps its card even if the scan misses it — a game that is literally
     running now is stronger evidence than an absent registry entry. */
  const matchedProfiles: GameProfile[] = (profiles ?? []).flatMap((p) => {
    const m = games.matched.find((x) => x.profile_id === p.id)
    return m ? [{ ...p, appid: m.appid }] : []
  })
  const detectedFound =
    (profiles ?? []).find((p) => p.id === detected?.id)
    ?? (profiles ?? []).find((p) => !!detected?.name && p.name.toLowerCase() === detected.name.toLowerCase())
    ?? null
  /* The detection's appid rides along so the card gets cover art too. */
  const detectedProfile: GameProfile | null =
    detectedFound ? { ...detectedFound, appid: detected?.appid } : null
  /* The running game leads the list instead of waiting for a scroll. */
  const gameList = detectedProfile
    ? [detectedProfile, ...matchedProfiles.filter((p) => p.id !== detectedProfile.id)]
    : matchedProfiles

  const apply = useCallback(async (p: GameProfileSummary) => {
    if (busyId) return
    setBusyId(p.id)
    try {
      const res = await api.applyGameProfile(p.id)
      setApplyFeed({ id: p.id, rows: res.results })
      /* Partial successes keep Revert available; nothing is hidden. */
      setAppliedId(res.results.some((r) => r.success) ? p.id : null)
    } catch (e) {
      setApplyFeed({ id: p.id, rows: [{ success: false, message: e instanceof Error ? e.message : String(e) }] })
      setAppliedId(null)
    } finally {
      setBusyId(null)
    }
  }, [busyId])

  const revert = useCallback(async () => {
    if (!appliedId || busyId) return
    setBusyId(appliedId)
    try {
      const res = await api.revertGameProfile()
      setApplyFeed({ id: appliedId, rows: res.results })
      setAppliedId(null)
    } catch (e) {
      setApplyFeed({ id: appliedId, rows: [{ success: false, message: e instanceof Error ? e.message : String(e) }] })
    } finally {
      setBusyId(null)
    }
  }, [appliedId, busyId])

  return {
    /** 'loading' | 'ready' | 'error' for the whole section. */
    state: games.state,
    /** Card list, detected game first, null while loading/error. */
    profileList: games.state === 'ready' ? gameList : null,
    /** Installed games with no profile yet. */
    others: games.others,
    detectedId: detectedProfile?.id ?? null,
    appliedId,
    applyFeed,
    busyId,
    apply,
    revert,
  }
}
