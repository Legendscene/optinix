/**
 * Ambient depth layer behind every route.
 *
 * The shell used to be a flat surface: only Home and Live Monitor had any
 * sense of space, so every other page read as a spreadsheet on a dark
 * rectangle. This paints a small 3D room behind the content column — a grid
 * floor receding toward the horizon, two wireframe halls leaning in from
 * opposite corners, suspended specks and two slow light fields — present on
 * all 60+ routes, invisible where a card covers it, and gone entirely under
 * reduced motion (the CSS animations are parked by the global rules in
 * index.css).
 *
 * Purely decorative: no canvas, no WebGL context, and every moving part is a
 * transform or a background position on one element, so the layer costs the
 * compositor almost nothing and never blocks a click.
 */

/** Fixed field: same room on every route, no random layout between pages. */
const SPECKS = [
  { left: '18%', top: '22%', delay: '0s', duration: '16s' },
  { left: '30%', top: '58%', delay: '-4s', duration: '21s' },
  { left: '44%', top: '14%', delay: '-8s', duration: '19s' },
  { left: '57%', top: '44%', delay: '-2s', duration: '24s' },
  { left: '68%', top: '26%', delay: '-11s', duration: '17s' },
  { left: '79%', top: '62%', delay: '-6s', duration: '23s' },
  { left: '88%', top: '34%', delay: '-13s', duration: '20s' },
  { left: '24%', top: '80%', delay: '-9s', duration: '18s' },
  { left: '62%', top: '76%', delay: '-15s', duration: '26s' },
  { left: '93%', top: '72%', delay: '-5s', duration: '22s' },
]

export function PageAtmosphere() {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 z-0 overflow-hidden">
      {/* Static engineering grid, fading out toward the fold. */}
      <div className="grid-overlay absolute inset-x-0 top-0 h-[420px] opacity-70" />

      {/* Accent field, high right: the light source for the whole app. */}
      <div className="atmosphere-field atmosphere-field-a" />

      {/* Violet counter-light, low left, so the two never read as one blur. */}
      <div className="atmosphere-field atmosphere-field-b" />

      {/* Horizon glow directly under the header. */}
      <div className="absolute inset-x-0 top-0 h-56 opacity-70 atmosphere-horizon" />

      {/* The room: floor, halls, specks. */}
      <div className="scene-3d">
        <div className="scene-floor" />
        <span className="scene-hall scene-hall-a" />
        <span className="scene-hall scene-hall-b" />
        {SPECKS.map((s) => (
          <span
            key={`${s.left}-${s.top}`}
            className="scene-speck"
            style={{ left: s.left, top: s.top, animationDelay: s.delay, animationDuration: s.duration }}
          />
        ))}
      </div>
    </div>
  )
}
