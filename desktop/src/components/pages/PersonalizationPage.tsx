import { Sun, Moon, Palette as PaletteIcon, Rows3, Wand, Check } from 'lucide-react'
import { cn } from '../../lib/utils'
import { useTheme, ACCENT_OPTIONS, MODE_OPTIONS, DENSITY_OPTIONS } from '../../lib/theme'

interface PersonalizationPageProps {
  onNavigate?: (id: string) => void
}

/**
 * Personalization destination: the design-system switches (mode, accent,
 * density). Every control here is live — it writes the shared preference
 * store and the token overrides in index.css react immediately. Background
 * images, glass effects and the legacy accent picker live behind
 * "Backgrounds & effects" so this page stays about the core system.
 */
export function PersonalizationPage({ onNavigate }: PersonalizationPageProps) {
  const { mode, setMode, accent, setAccent, density, setDensity } = useTheme()

  return (
    <div className="max-w-[720px] space-y-4 animate-rise pb-4">
      <header>
        <h1 className="page-title">Personalization</h1>
        <p className="page-subtitle mt-1">
          How Optinix looks. Changes apply immediately and are remembered on this machine.
        </p>
      </header>

      {/* Mode */}
      <section className="surface-card p-4" aria-labelledby="mode-label">
        <div className="flex items-center gap-2 mb-3">
          {mode === 'light' ? <Sun size={15} className="text-accent-ink" /> : <Moon size={15} className="text-accent-ink" />}
          <h2 id="mode-label" className="text-[13px] font-semibold">Theme</h2>
        </div>
        <div className="grid grid-cols-2 gap-2.5" role="radiogroup" aria-labelledby="mode-label">
          {MODE_OPTIONS.map((m) => (
            <button
              key={m.id}
              role="radio"
              aria-checked={mode === m.id}
              onClick={() => setMode(m.id)}
              className={cn(
                'flex items-center gap-2.5 rounded-[10px] border px-3.5 py-3 text-left transition-colors duration-150',
                mode === m.id
                  ? 'border-accent-line bg-accent-dim'
                  : 'border-border bg-surface-2 hover:bg-surface-3 hover:border-border-light',
              )}
            >
              <span className={cn(
                'w-8 h-8 rounded-lg border flex items-center justify-center shrink-0',
                m.id === 'dark' ? 'bg-surface-0 border-border-light text-text-secondary'
                  : 'bg-white border-border text-[#171a20]',
              )}>
                {m.id === 'dark' ? <Moon size={14} /> : <Sun size={14} />}
              </span>
              <span className="min-w-0">
                <span className="block text-[13px] font-medium">{m.label}</span>
                <span className="block text-[11px] text-text-tertiary">
                  {m.id === 'dark' ? 'Graphite surfaces, teal accent' : 'Paper surfaces, dark accent'}
                </span>
              </span>
              {mode === m.id && <Check size={15} className="ml-auto text-accent-ink shrink-0" />}
            </button>
          ))}
        </div>
      </section>

      {/* Accent */}
      <section className="surface-card p-4" aria-labelledby="accent-label">
        <div className="flex items-center gap-2 mb-3">
          <PaletteIcon size={15} className="text-accent-ink" />
          <h2 id="accent-label" className="text-[13px] font-semibold">Accent color</h2>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5" role="radiogroup" aria-labelledby="accent-label">
          {ACCENT_OPTIONS.map((a) => (
            <button
              key={a.id}
              role="radio"
              aria-checked={accent === a.id}
              onClick={() => setAccent(a.id)}
              className={cn(
                'flex flex-col items-center gap-2 rounded-[10px] border px-3 py-3 transition-colors duration-150',
                accent === a.id
                  ? 'border-accent-line bg-accent-dim'
                  : 'border-border bg-surface-2 hover:bg-surface-3 hover:border-border-light',
              )}
            >
              <span
                className="w-7 h-7 rounded-full flex items-center justify-center"
                style={{ backgroundColor: a.hex }}
              >
                {accent === a.id && <Check size={14} className="text-white" strokeWidth={3} />}
              </span>
              <span className="text-[12px] font-medium">{a.label}</span>
            </button>
          ))}
        </div>
        <p className="text-[11.5px] text-text-tertiary mt-2.5">
          The accent drives buttons, active states, chart lines and focus rings.
          Both themes carry a tested contrast pair.
        </p>
      </section>

      {/* Density */}
      <section className="surface-card p-4" aria-labelledby="density-label">
        <div className="flex items-center gap-2 mb-3">
          <Rows3 size={15} className="text-accent-ink" />
          <h2 id="density-label" className="text-[13px] font-semibold">Density</h2>
        </div>
        <div className="grid grid-cols-2 gap-2.5" role="radiogroup" aria-labelledby="density-label">
          {DENSITY_OPTIONS.map((d) => (
            <button
              key={d.id}
              role="radio"
              aria-checked={density === d.id}
              onClick={() => setDensity(d.id)}
              className={cn(
                'flex items-center gap-2.5 rounded-[10px] border px-3.5 py-3 text-left transition-colors duration-150',
                density === d.id
                  ? 'border-accent-line bg-accent-dim'
                  : 'border-border bg-surface-2 hover:bg-surface-3 hover:border-border-light',
              )}
            >
              <span className="flex flex-col gap-1 shrink-0" aria-hidden>
                {[0, 1, 2].map((i) => (
                  <span
                    key={i}
                    className="block h-1.5 rounded-full bg-text-tertiary"
                    style={{ width: d.id === 'compact' ? 18 : 26 }}
                  />
                ))}
              </span>
              <span className="min-w-0">
                <span className="block text-[13px] font-medium">{d.label}</span>
                <span className="block text-[11px] text-text-tertiary">
                  {d.id === 'compact' ? 'More on screen, tighter gaps' : 'Default spacing'}
                </span>
              </span>
              {density === d.id && <Check size={15} className="ml-auto text-accent-ink shrink-0" />}
            </button>
          ))}
        </div>
      </section>

      {/* Link to legacy appearance controls */}
      <button
        onClick={() => onNavigate?.('theme')}
        className="surface-card surface-card-interactive w-full flex items-center gap-3 p-4 text-left"
      >
        <span className="w-8 h-8 rounded-lg bg-surface-3 border border-border
          flex items-center justify-center text-text-secondary shrink-0">
          <Wand size={15} />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-[13px] font-medium">Backgrounds &amp; effects</span>
          <span className="block text-[11.5px] text-text-tertiary">
            Wallpaper, gradient, glass effect and blur intensity
          </span>
        </span>
        <span className="text-text-tertiary text-[16px]" aria-hidden>›</span>
      </button>
    </div>
  )
}
