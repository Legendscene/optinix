import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'

export interface Preferences {
  theme: string
  background: string
  accent: string
  sidebarMode: string
  bgUrl: string
  bgOpacity: number
  blurIntensity: number
  glassEffect: boolean
}

const DEFAULTS: Preferences = {
  theme: 'dark',
  background: 'none',
  accent: '#7c3aed',
  sidebarMode: 'full',
  bgUrl: '',
  bgOpacity: 50,
  blurIntensity: 20,
  glassEffect: false,
}

function loadPrefs(): Preferences {
  try {
    const raw = localStorage.getItem('optinix-prefs')
    return raw ? { ...DEFAULTS, ...JSON.parse(raw) } : DEFAULTS
  } catch {
    return DEFAULTS
  }
}

function savePrefs(prefs: Preferences) {
  localStorage.setItem('optinix-prefs', JSON.stringify(prefs))
}

const themeBgMap: Record<string, string> = {
  dark: '#09090b',
  midnight: '#0a0a1a',
  purple: '#0f0a1a',
  ocean: '#0a121a',
  forest: '#0a120a',
  sunset: '#1a100a',
  glassy: 'rgba(9, 9, 11, 0.85)',
  neon: '#0a0a0a',
}

interface PreferencesContextValue {
  prefs: Preferences
  update: (key: keyof Preferences, value: string | number | boolean) => void
}

const PreferencesContext = createContext<PreferencesContextValue | null>(null)

export function PreferencesProvider({ children }: { children: ReactNode }) {
  const [prefs, setPrefs] = useState<Preferences>(DEFAULTS)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    setPrefs(loadPrefs())
    setReady(true)
  }, [])

  const update = useCallback((key: keyof Preferences, value: string | number | boolean) => {
    setPrefs(prev => {
      const next = { ...prev, [key]: value }
      savePrefs(next)
      return next
    })
  }, [])

  useEffect(() => {
    if (!ready) return
    const root = document.getElementById('app-root')
    if (!root) return

    root.style.setProperty('--accent-color', prefs.accent)
    root.style.setProperty('--accent-dim', `${prefs.accent}26`)
    root.style.setProperty('--accent-hover', prefs.accent)

    const bgColor = themeBgMap[prefs.theme] || '#09090b'
    root.style.setProperty('--bg-color', bgColor)
    root.style.backgroundColor = bgColor

    if (prefs.background === 'image' && prefs.bgUrl) {
      root.style.backgroundImage = `url(${prefs.bgUrl})`
      root.style.backgroundSize = 'cover'
      root.style.backgroundPosition = 'center'
      root.style.backgroundAttachment = 'fixed'
      root.style.backgroundBlendMode = 'overlay'
    } else if (prefs.background === 'video') {
      root.style.backgroundImage = 'none'
    } else if (prefs.background === 'gradient') {
      root.style.backgroundImage = `radial-gradient(ellipse at 50% 0%, ${prefs.accent}22 0%, transparent 70%)`
      root.style.backgroundSize = 'auto'
      root.style.backgroundAttachment = 'fixed'
    } else {
      root.style.backgroundImage = 'none'
      root.style.backgroundColor = bgColor
    }

    root.style.setProperty('--bg-opacity', String(prefs.bgOpacity / 100))
    root.style.setProperty('--blur-intensity', `${prefs.blurIntensity}px`)
  }, [prefs, ready])

  if (!ready) return null

  return (
    <PreferencesContext.Provider value={{ prefs, update }}>
      {prefs.background === 'video' && prefs.bgUrl && (
        <video
          autoPlay
          muted
          loop
          playsInline
          className="fixed inset-0 w-full h-full object-cover pointer-events-none"
          style={{ opacity: prefs.bgOpacity / 100, zIndex: 0 }}
        >
          <source src={prefs.bgUrl} type="video/mp4" />
        </video>
      )}
      <div
        id="app-root"
        className={`flex h-full w-full ${prefs.glassEffect ? 'backdrop-blur-xl' : ''}`}
        style={{
          backgroundColor: 'var(--bg-color, #09090b)',
          backgroundImage: 'var(--bg-image, none)',
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundAttachment: 'fixed',
        }}
      >
        {children}
      </div>
    </PreferencesContext.Provider>
  )
}

export function usePreferences() {
  const ctx = useContext(PreferencesContext)
  if (!ctx) throw new Error('usePreferences must be used within PreferencesProvider')
  return ctx
}
