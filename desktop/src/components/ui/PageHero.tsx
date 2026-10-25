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
 * one band — same lighting, same type scale, same stat plates — so moving
 * between pages reads as moving between rooms in one product rather than
 * between products.
 *
 * Visually the band is a lit stage: a cyan key light high right, a violet
 * counter-light low left, one soft shaft and a fine instrument baseline. All
 * of it leans with the pointer through two CSS variables (`--mx/--my` on the
 * section), written in one rAF per frame so a full-width sweep costs no React
 * renders; with reduced motion the handler returns early and the stage holds
 * still.
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
      {/* Stage: light only. Decoration, never interactive. */}
      <div aria-hidden className="pointer-events-none absolute inset-0 z-0 overflow-hidden rounded-[inherit]">
        <span className="hero-key" />
        <span className="hero-key hero-key-violet" />
        <span className="hero-shaft" />
        <span className="hero-baseline" />
        <span className="hero-grain absolute inset-0" />
      </div>

      <div className="hero-content relative z-10 grid gap-6 p-6 lg:p-7 lg:grid-cols-[minmax(0,1fr)_auto] items-start">
        <div className="min-w-0 space-y-4">
          {(eyebrow || badges) && (
            <div className="flex flex-wrap items-center gap-2.5">
              {eyebrow && (
                <span className="flex items-center gap-2">
                  <span className="h-1 w-4 rounded-full bg-accent" aria-hidden />
                  <span className="eyebrow text-accent-ink/85">{eyebrow}</span>
                </span>
              )}
              {badges}
            </div>
          )}

          <div className="flex items-start gap-3.5">
            {icon && (
              <span className="icon-chip text-accent-ink h-11 w-11 shrink-0">{icon}</span>
            )}
            <div className="min-w-0">
              <h1 className="grad-text text-[29px] font-bold leading-[1.12] tracking-[-0.032em]">
                {title}
              </h1>
              {subtitle && (
                <p className="page-subtitle mt-2 max-w-[64ch]">{subtitle}</p>
              )}
            </div>
          </div>

          {stats && stats.length > 0 && (
            <dl className="stat-grid grid grid-cols-2 gap-2.5 sm:grid-cols-4">
              {stats.map((s) => (
                <div key={s.label} className="stat-tile px-3 py-2.5">
                  <dt className="text-[9.5px] font-semibold uppercase tracking-[0.1em] text-text-tertiary">
                    {s.label}
                  </dt>
                  <dd className={cn('metric-value mt-1.5 text-[21px] leading-none', TONE[s.tone ?? 'default'])}>
                    {s.value}
                  </dd>
                  {s.hint && <p className="mt-1.5 text-[10.5px] text-text-tertiary">{s.hint}</p>}
                </div>
              ))}
            </dl>
          )}

          {children}
        </div>

        <div className="flex flex-col items-start gap-4 lg:items-end">
          {actions && (
            <div className="flex flex-wrap items-center gap-2">{actions}</div>
          )}
          {orb && (
            <div className="hero-ornament hidden lg:flex items-start justify-end pt-1">
              <Orb3D size={158} />
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
