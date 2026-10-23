import { useSteamCover } from '../../hooks/useSteamCover'

/** Installed on this PC, but no optimization profile exists for it yet.
    Rendered like a real game card, not a cheap chip — it sits in the same grid. */
export function OtherGameCard({ game }: { game: { name: string; source: string; appid?: number } }) {
  const { url: cover, fail: coverFail } = useSteamCover(game.appid)
  return (
    <div className="surface-card overflow-hidden flex flex-col">
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
              {game.name.charAt(0)}
            </span>
          </div>
        )}
        <span
          title="Installed, but Optinix has no optimization profile for this game yet."
          className="absolute top-2 right-2 text-[10px] font-semibold uppercase tracking-[0.06em] text-yellow bg-black/65 px-1.5 py-0.5 rounded"
        >
          No profile yet
        </span>
      </div>
      <div className="p-3.5 flex flex-col flex-1">
        <h4 className="font-display uppercase text-[13px] font-semibold tracking-[0.02em] text-text truncate">{game.name}</h4>
        <p className="mt-0.5 text-[11px] leading-[1.4] text-text-tertiary flex-1">
          Installed on this computer — no optimization profile yet. Add one from the Games page.
        </p>
      </div>
    </div>
  )
}
