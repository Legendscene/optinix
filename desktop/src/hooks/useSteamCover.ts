import { useState } from 'react'

/** Steam's public CDN hosts cover art keyed by a game's real Steam appid.
    Not every app ships the tall portrait, so the chain falls back to the
    wide hero image (object-cover crops it) before giving up to the tile. */
const steamCovers = (appid: number) => [
  `https://cdn.cloudflare.steamstatic.com/steam/apps/${appid}/library_600x900.jpg`,
  `https://cdn.cloudflare.steamstatic.com/steam/apps/${appid}/library_hero.jpg`,
]

/** Walks Steam's cover-art chain; yields null (tile) when every step fails. */
export function useSteamCover(appid?: number) {
  const [step, setStep] = useState(0)
  if (!appid) return { url: null as string | null, fail: () => {} }
  const chain = steamCovers(appid)
  return {
    url: step < chain.length ? chain[step] : null,
    fail: () => setStep((s) => s + 1),
  }
}
