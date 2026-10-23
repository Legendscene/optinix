import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { PreferencesProvider } from '../../contexts/PreferencesContext'
import { PersonalizationPage } from './PersonalizationPage'

function renderPage() {
  return render(
    <PreferencesProvider>
      <PersonalizationPage />
    </PreferencesProvider>,
  )
}

describe('PersonalizationPage', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.removeAttribute('data-theme')
    document.documentElement.removeAttribute('data-accent')
    document.documentElement.removeAttribute('data-density')
  })

  it('renders theme, accent and density sections', () => {
    renderPage()
    expect(screen.getByText('Theme')).toBeInTheDocument()
    expect(screen.getByText('Accent color')).toBeInTheDocument()
    expect(screen.getByText('Density')).toBeInTheDocument()
  })

  it('switches to light mode and sets data-theme on the root', async () => {
    renderPage()
    const light = screen.getByRole('radio', { name: /Light/ })
    fireEvent.click(light)
    /* PreferencesProvider applies the attribute in an effect. */
    await Promise.resolve()
    expect(document.documentElement.dataset.theme).toBe('light')
    expect(screen.getByRole('radio', { name: /Light/ })).toHaveAttribute('aria-checked', 'true')
  })

  it('selecting an accent preset sets data-accent', async () => {
    renderPage()
    const indigo = screen.getByRole('radio', { name: /Indigo/ })
    fireEvent.click(indigo)
    await Promise.resolve()
    expect(document.documentElement.dataset.accent).toBe('indigo')
  })

  it('compact density sets data-density and persists', async () => {
    renderPage()
    const compact = screen.getByRole('radio', { name: /Compact/ })
    fireEvent.click(compact)
    await Promise.resolve()
    expect(document.documentElement.dataset.density).toBe('compact')

    const saved = JSON.parse(localStorage.getItem('optinix-prefs') ?? '{}')
    expect(saved.density).toBe('compact')
  })

  it('links through to the legacy backgrounds page', () => {
    const onNavigate = vi.fn()
    render(
      <PreferencesProvider>
        <PersonalizationPage onNavigate={onNavigate} />
      </PreferencesProvider>,
    )
    fireEvent.click(screen.getByText('Backgrounds & effects'))
    expect(onNavigate).toHaveBeenCalledWith('theme')
  })
})
