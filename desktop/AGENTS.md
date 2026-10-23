# desktop/AGENTS.md — frontend-specific notes

Read the repo-root [AGENTS.md](../AGENTS.md) first; this file only adds
frontend detail.

- **Stack**: Vite 8 (rolldown) + React 19 + TypeScript ~6 + Tailwind v4 via
  `@tailwindcss/vite`. Tests: vitest + Testing Library (`src/test/setup.ts`).
  Lint: oxlint (config `.oxlintrc.json`), 0 errors is the bright line.
- **Typecheck**: `npx tsc -p tsconfig.app.json --noEmit` (run from this
  directory). `npm run build` = `tsc -b && vite build`.

## Map of src/

- `main.tsx` → `App.tsx`; routing is a state-driven page switch, page ids and
  nav groups come from `nav.ts` (tested by `nav.test.ts`).
- `lib/api.ts` — the single typed HTTP client. New endpoints get a method
  here; pages never fetch raw.
- `store/systemStore.ts` — shared system-info state; `hooks/useWebSocket.ts`
  feeds it from the backend's `system_status` socket stream.
- `components/pages/` — ~65 page files, one per `nav.ts` id.
- `components/ui/` — shared primitives: `Card` (panel + pointer sheen),
  `MetricCard`, `TiltCard`, `PageHeader`, `Button`, `ProgressBar`,
  `StatusPill`, `Skeleton`, `StatePanel`, `charts/` (d3-based
  StreamArea/Sparkline/RadialMeter/etc. with rAF tween + reduced-motion
  bypass), `ChartGhost` (designed empty/collecting state for chart panels).
- `components/three/` — the hero WebGL scene (@react-three/fiber) with a
  graceful fallback; kept compositor-cheap and disabled under reduced motion.
- `index.css` — all design tokens (CSS variables), dark/light theme system,
  accent presets, reduced-motion rules. No page should hardcode palette hex
  values; use the tokens.
- `contexts/PreferencesContext.tsx` — user preferences + theme/accent; the
  `data-motion` attribute on `<html>` is what the reduced-motion system reads.

## Conventions

- Cards/tiles must come from the `ui/` primitives so there is exactly one copy
  of the pointer/tilt/glow plumbing; do not fork styles per page.
- Long data flows: comments explain "why" (e.g. background-tab timer throttle
  workarounds in `LiveMonitorPage.tsx`). Keep that habit.
- Tests live next to the page (`XxxPage.test.tsx`); vitest run = `npm test`.
