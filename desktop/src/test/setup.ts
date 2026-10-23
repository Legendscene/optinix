import '@testing-library/jest-dom/vitest'
import { afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'

afterEach(() => cleanup())

/* jsdom lacks matchMedia; the app queries it for reduced-motion. */
if (!window.matchMedia) {
  window.matchMedia = (query: string): MediaQueryList =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }) as MediaQueryList
}

/* ScrollIntoView used by the command palette list. */
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {}
}

/* jsdom has no canvas backend: asking for a WebGL context throws
   "Not implemented" noise through the virtual console on every probe.
   Answer null quietly instead — the hero treats null as "no WebGL" and
   renders its static fallback, which is the path these tests exercise. */
const origGetContext = HTMLCanvasElement.prototype.getContext
HTMLCanvasElement.prototype.getContext = function (
  this: HTMLCanvasElement,
  type: string,
  ...rest: unknown[]
) {
  if (type === 'webgl' || type === 'webgl2' || type === 'experimental-webgl') return null
  return origGetContext.call(this, type, ...(rest as []))
} as typeof HTMLCanvasElement.prototype.getContext
