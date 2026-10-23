import { useCallback, useEffect, useRef, type PointerEvent, type ReactNode } from 'react'
import { cn } from '../../lib/utils'
import { prefersReducedMotion } from '../../hooks/useMotionPreference'
import { Orb3D } from './Orb3D'

export interface HeroStat {
  label: string
  value: string
  /** Optional second line, e.g. "of 16 GB" or "4 s interval". */
  hint?: string
  /** Tone for the value; defaults to ink. */
  tone?: 'default' | 'accent' | 'good' | 'warn' | 'bad'
}

interface PageHeroProps {
  title: string
  subtitle?: string
  /** Small uppercase line above the title. */
  eyebrow?: string
  /** Lucide icon shown in the gradient chip beside the title. */
  icon?: ReactNode
  /** Badges / status chips under the eyebrow. */
  badges?: ReactNode
  /** Four short readings under the title — the band's "instrument panel". */
  stats?: HeroStat[]
  /** Buttons or a control cluster on the right. */
  actions?: ReactNode
  /** Right-hand focal ornament. On by default; turn off on dense pages. */
  orb?: boolean
  /** Extra content inside the band, under the stats. */
  children?: ReactNode
  className?: string
}

const TONE: Record<NonNullable<HeroStat['tone']>, string> = {
  default: 'text-text',
  accent: 'text-accent',
  good: 'text-green',
  warn: 'text-yellow',
  bad: 'text-red',
}

/**
 * The page-opening band used by every tool page.
 *
 * Before this, each page invented its own header: some had a 2xl heading and a
 * paragraph, some had a 4xl hero, some had nothing but a card. They now share
 * one band — same gradient, same type scale, same stat grid — so moving between
 * pages reads as moving between rooms in one product rather than between
 * products.
 *
 * The band is a small 3D stage rather than a painted rectangle: a receding grid
 * floor, two light beacons, an orbiting hairline and a floating instrument
 * cluster, all tilted by the pointer through four CSS variables (`--mx/--my`
 * on the section). The parallax is written straight to the element's style in
 * one rAF per frame, so a full-width sweep costs no React renders; with
 * reduced motion the handler returns early and the layers stay still.
 *
 * Server/client data is passed in; the band itself is presentational.
 */
export function PageHero({
  title, subtitle, eyebrow, icon, badges, stats, actions, orb = true, children, className,
}: PageHeroProps) {
  const host = useRef<HTMLElement>(null)
  const frame = useRef(0)
  const aim = useRef({ x: 0.5, y: 0.5 })

  const flush = useCallback(() => {
    frame.current = 0
    const el = host.current
    if (!el) return
    el.style.setProperty('--mx', aim.current.x.toFixed(3))
    el.style.setProperty('--my', aim.current.y.toFixed(3))
  }, [])

  const onMove = (e: PointerEvent<HTMLElement>) => {
    const el = host.current
    if (!el || prefersReducedMotion()) return
    const rect = el.getBoundingClientRect()
    if (!rect.width || !rect.height) return
    aim.current = {
      x: Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width)),
      y: Math.min(1, Math.max(0, (e.clientY - rect.top) / rect.height)),
    }
    if (!frame.current) frame.current = requestAnimationFrame(flush)
  }

  const onLeave = () => {
    aim.current = { x: 0.5, y: 0.5 }
    if (!frame.current) frame.current = requestAnimationFrame(flush)
  }

  /* One pending frame at most, released on unmount. */
  useEffect(() => () => {
    if (frame.current) cancelAnimationFrame(frame.current)
  }, [])

  return (
    <section
      ref={host}
      className={cn('band-hero', className)}
      onPointerMove={onMove}
      onPointerLeave={onLeave}
    >
      {/* Stage: floor, light and orbit. Decoration only, never interactive. */}
      <div aria-hidden className="hero-stage">
        <span className="hero-beacon" />
        <span className="hero-beacon hero-beacon-violet" />
        <span className="hero-stage-floor" />
        <span className="hero-orbit" />
        <span className="hero-orbit hero-orbit-b" />
        <span className="hero-scanline" />
        <span className="hero-ticks" />
      </div>

      <div className="hero-content grid gap-6 p-6 lg:grid-cols-[minmax(0,1fr)_auto] items-start">
        <div className="min-w-0 space-y-4">
          {eyebrow && (
            <div className="flex flex-wrap items-center gap-2">
              <span className="eyebrow">{eyebrow}</span>
              {badges}
            </div>
          )}

          <div className="flex items-start gap-3">
            {icon && (
              <span className="icon-chip text-accent h-10 w-10 shrink-0">{icon}</span>
            )}
            <div className="min-w-0">
              <h1 className="grad-text text-[27px] font-semibold leading-tight tracking-[-0.025em]">
                {title}
              </h1>
              {subtitle && (
                <p className="page-subtitle mt-1.5 max-w-[62ch]">{subtitle}</p>
              )}
            </div>
          </div>

          {stats && stats.length > 0 && (
            <dl className="stat-grid grid grid-cols-2 gap-2.5 sm:grid-cols-4">
              {stats.map((s) => (
                <div key={s.label} className="stat-tile px-3 py-2.5">
                  <dt className="text-[10px] font-semibold uppercase tracking-[0.06em] text-text-tertiary">
                    {s.label}
                  </dt>
                  <dd className={cn('mt-1 text-[19px] font-semibold leading-none tnum', TONE[s.tone ?? 'default'])}>
                    {s.value}
                  </dd>
                  {s.hint && <p className="mt-1 text-[10.5px] text-text-tertiary">{s.hint}</p>}
                </div>
              ))}
            </dl>
          )}

          {children}

          {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
        </div>

        {orb && (
          <div className="hero-ornament hidden lg:flex items-start justify-end pr-2 pt-1">
            <Orb3D size={152} />
          </div>
        )}
      </div>
    </section>
  )
}
