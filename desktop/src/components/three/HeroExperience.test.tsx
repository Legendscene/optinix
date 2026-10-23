import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { HeroExperience } from './HeroExperience'

/**
 * jsdom never has WebGL (the setup stub answers null quietly), so these
 * tests pin the behaviour real machines get on locked-down or ancient
 * GPUs: a static emblem instead of a broken canvas.
 */
describe('HeroExperience', () => {
  it('renders the static emblem when WebGL is unavailable', () => {
    render(<HeroExperience className="w-[280px] h-[200px]" />)
    const fallback = screen.getByTestId('hero-fallback')
    expect(fallback).toBeInTheDocument()
    expect(fallback.dataset.reason).toBe('no-webgl')
  })

  it('keeps the container sizing the parent gave it', () => {
    const { container } = render(<HeroExperience className="w-[280px] h-[200px]" />)
    expect(container.firstElementChild).toHaveClass('w-[280px]', 'h-[200px]')
  })

  it('never throws even when the graphics stack is missing entirely', () => {
    /* The render itself is the assertion: an unguarded three.js import or
       an un-caught canvas failure would throw here and fail the test. */
    expect(() => render(<HeroExperience />)).not.toThrow()
  })
})
