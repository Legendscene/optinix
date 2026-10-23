/**
 * WebGL capability probe, deliberately free of any three.js import so the
 * check itself never costs a bundle byte. Result is cached: the answer
 * cannot change while the app is running.
 *
 * jsdom (tests) has no WebGL, so this returns false there and the hero
 * renders its static fallback — which is exactly the behaviour we want
 * to exercise in tests.
 */
let cached: boolean | null = null

export function supportsWebGL(): boolean {
  if (cached != null) return cached
  try {
    const canvas = document.createElement('canvas')
    const gl = (canvas.getContext('webgl2') ??
      canvas.getContext('webgl')) as WebGLRenderingContext | null
    cached = gl != null
    /* Free the tiny context we just created; the real one belongs to
       the canvas inside the hero scene. */
    gl?.getExtension('WEBGL_lose_context')?.loseContext()
  } catch {
    cached = false
  }
  return cached
}
