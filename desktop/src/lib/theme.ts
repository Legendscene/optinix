/**
 * Typed view over the shared preference store for the three design-system
 * switches: surface mode, accent preset, density. SettingsPage and the
 * Personalization page both read/write the same preferences, so a change
 * in either place is reflected everywhere immediately.
 */
import { usePreferences, ACCENT_PRESETS, type Preferences } from '../contexts/PreferencesContext'

export type ThemeMode = Preferences['mode']
export type AccentPreset = Preferences['accentPreset']
export type Density = Preferences['density']

export const ACCENT_OPTIONS: { id: AccentPreset; label: string; hex: string }[] = [
  { id: 'teal', label: 'Teal', hex: ACCENT_PRESETS.teal },
  { id: 'indigo', label: 'Indigo', hex: ACCENT_PRESETS.indigo },
  { id: 'amber', label: 'Amber', hex: ACCENT_PRESETS.amber },
  { id: 'rose', label: 'Rose', hex: ACCENT_PRESETS.rose },
]

export const MODE_OPTIONS: { id: ThemeMode; label: string }[] = [
  { id: 'dark', label: 'Dark' },
  { id: 'light', label: 'Light' },
]

export const DENSITY_OPTIONS: { id: Density; label: string }[] = [
  { id: 'comfortable', label: 'Comfortable' },
  { id: 'compact', label: 'Compact' },
]

export function useTheme() {
  const { prefs, update } = usePreferences()
  return {
    mode: prefs.mode,
    setMode: (m: ThemeMode) => update('mode', m),
    accent: prefs.accentPreset,
    setAccent: (a: AccentPreset) => update('accentPreset', a),
    density: prefs.density,
    setDensity: (d: Density) => update('density', d),
  }
}
