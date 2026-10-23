import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App'
import { PreferencesProvider } from './contexts/PreferencesContext'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {/* SettingsPage reads usePreferences(), so the provider has to sit above
        the router rather than inside the settings route. */}
    <PreferencesProvider>
      <App />
    </PreferencesProvider>
  </StrictMode>,
)
