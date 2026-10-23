import { CheckCircle2, Loader2, XCircle } from 'lucide-react'
import { cn } from '../../lib/utils'
import { useSteamCover } from '../../hooks/useSteamCover'
import type { GameProfile, ProfileFeed } from '../../hooks/useOptimizerGames'

interface GameProfileCardProps {
  profile: GameProfile
  detected: boolean
  applied: boolean
  busy: boolean
  feed: ProfileFeed['rows'] | null
  onApply: () => void
  onRevert: () => void
}

/** Cover-art card for a game with an optimization profile. It renders what it
    is told; the data lives in useOptimizerGames. */
export function GameProfileCard({ profile, detected, applied, busy, feed, onApply, onRevert }: GameProfileCardProps) {
  const { url: cover, fail: coverFail } = useSteamCover(profile.appid)
  return (
    <div className={cn(
      'surface-card overflow-hidden flex flex-col',
      detected && 'border-eg-line',
    )}>
      <div className="relative shrink-0">
        {cover ? (
          <img
            src={cover}
            alt=""
            loading="lazy"
            onError={coverFail}
            className="w-full aspect-[3/4] object-cover bg-surface-3"
          />
        ) : (
          <div className="w-full aspect-[3/4] bg-surface-3 flex items-center justify-center">
            <span className="font-display text-[46px] font-bold text-eg-green/40 uppercase">
              {profile.name.charAt(0)}
            </span>
          </div>
        )}
        {detected && (
          <span
            title="Optinix detected this game as currently running."
            className="absolute top-2 left-2 text-[10px] font-semibold uppercase tracking-[0.06em] text-eg-green bg-black/65 px-1.5 py-0.5 rounded"
          >
            Running now
          </span>
        )}
      </div>
      <div className="p-3.5 flex flex-col flex-1">
        <h4 className="font-display uppercase text-[13px] font-semibold tracking-[0.02em] text-text">{profile.name}</h4>
        <p className="mt-0.5 text-[11px] leading-[1.4] text-text-tertiary flex-1">{profile.description}</p>

        {feed && feed.length > 0 && (
          <ul className="eg-feed mt-3 pl-3 space-y-1">
            {feed.map((r, i) => (
              <li key={i} className="eg-feed-row flex items-start gap-1.5 text-[11px]">
                {r.success ? <CheckCircle2 size={11} className="text-eg-green mt-0.5 shrink-0" /> : <XCircle size={11} className="text-red mt-0.5 shrink-0" />}
                <span className="text-text-secondary">{r.message}</span>
              </li>
            ))}
          </ul>
        )}

        <div className="mt-3 pt-0">
          {busy ? (
            <span className="inline-flex items-center gap-1.5 text-[11px] font-display uppercase tracking-[0.05em] text-text-secondary">
              <Loader2 size={13} className="animate-spin" /> Applying…
            </span>
          ) : applied ? (
            <button
              onClick={onRevert}
              className="font-display uppercase text-[11px] font-semibold tracking-[0.05em] px-3.5 py-2 rounded-lg bg-surface-2 border border-border text-text-secondary hover:text-text transition-colors duration-150"
            >
              Revert
            </button>
          ) : (
            <button
              onClick={onApply}
              className="font-display uppercase text-[11px] font-semibold tracking-[0.05em] px-3.5 py-2 rounded-lg bg-eg-green-dim text-eg-green border border-eg-line hover:bg-eg-green hover:text-eg-ink transition-colors duration-150"
            >
              Apply profile
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
