# AGENTS.md — AI handoff guide for Optinix (PC-Optimizer)

Read this first. The user's standing rule: **ko bhi naya AI is repo par kaam kare toh
use "kaha kya hai, kyu hai, kaise hai" turant pata chalna chahiye.** This file is
that map. `README.md` covers setup/run; this file covers *why things look the way
they do* and the rules you must not break.

---

## 1. What this project is

**Optinix** — a Windows PC optimizer desktop app:

- **Backend**: Python 3.9+ (Flask + Flask-SocketIO), loopback-only server on
  `127.0.0.1:5420`. It mutates real Windows settings (registry, services, power
  plans), so its security posture is strict.
- **Frontend**: `desktop/` — Vite 8 + React 19 + TypeScript + Tailwind v4
  (via `@tailwindcss/vite`). Built to `desktop/dist/`, which the backend serves.
- **Window modes**: `run.py` (server + browser) and `main.py` (pywebview window).
  `build.spec` packages it into a Windows exe via PyInstaller.
- `ui/` is a **fallback** dashboard used only when `desktop/dist` is missing
  (`core/config.py` decides). Don't "fix" the legacy dashboard — fix `desktop/`.

## 2. Where things are (kaha kya hai)

```
app.py                 Flask app, SocketIO, static/SPA serving, local-only guard
main.py / run.py       launchers; build.spec → Windows exe; installer.py
core/config.py         CONFIG dataclass: port, ui_dir, log/rollback dirs, poll intervals
core/no_console.py     installs child-process console hiding BEFORE any blueprint loads
core/api/*             ~46 Flask blueprints, registered by register_blueprints(core/api/__init__.py)
core/optimizers/*      each optimizer domain (cleanup, gaming, network, gpu, ...)
core/monitor/*         monitor engine + metrics store (history backend)
core/timeline/*        timeline event store; core/reports, core/intelligence, core/di ...
desktop/src/nav.ts     single source of truth for pages/routes (with nav.test.ts)
desktop/src/lib/api.ts typed API client — every backend call goes through this
desktop/src/components/pages/*   one file per page (~65 pages)
desktop/src/components/ui/*      shared primitives: Card, MetricCard, TiltCard, charts/...
desktop/src/index.css  design tokens (CSS vars) + theme system + reduced-motion rules
tests/                 backend pytest suite (pytest.ini: testpaths=tests)
screenshots/           playwright screenshot scripts + captures (see §6)
```

`docs/` currently does not exist; do not invent references to it.

## 3. How it runs (kaise chalta hai)

```bash
python run.py                    # dev: server + opens browser at 127.0.0.1:5420
python main.py                   # pywebview window instead of browser
cd desktop && npm run dev        # vite dev server on 5173 (backend must be running)
```

- SocketIO pushes a `system_status` block every ~3s (CPU/mem/disk/GPU), GPU
  values cached ~10s (`core/config.py` `ws_emit_seconds` / `ws_gpu_cache_seconds`).
- Deep links (`/cpu`) fall back to `index.html` in `app.py` — real files and
  `api/*` paths still 404 on purpose. Preserve this behavior when touching
  `statics()`; a broad index.html catch-all is a bug generator.

## 4. Checks you MUST keep green (baki sab chize thik)

CI = `.github/workflows/check.yml`. Run the same locally:

```bash
# Backend
python -m pytest -q

# Frontend (from desktop/)
npx tsc -p tsconfig.app.json --noEmit   # typecheck
npm run lint                            # oxlint
npm run test                            # vitest
npm run build                           # tsc -b && vite build
```

Status as of 2026-10-23: pytest ~163 passed, vitest 86 tests / 10 files passed,
tsc clean, build clean. **Bright line:** `oxlint` reports 0 errors and ~18
warnings. Do not add new warnings; the existing ones (react-hooks
exhaustive-deps on `mounted` refs, only-export-components in
PreferencesContext) are a known baseline — fix only if you touch that code.

Commit style: `feat: ...` / `fix: ...` / `chore: ...`, one topic per commit.

## 5. Architecture rules (kyu — the parts easy to break)

1. **Local-only API.** `app.py` blocks non-local Hosts and cross-origin
   mutating requests (DNS-rebinding/XSRF defense). Never loosen
   `LOCAL_ORIGINS`/`MUTATING`, never bind the server to `0.0.0.0`, and never
   add an endpoint without going through `register_blueprints`.
2. **PyInstaller reality.** In the frozen build there is no console and no
   eventlet/gevent: SocketIO uses `async_mode="threading"` for a reason, and
   `core/no_console.py` must stay installed before blueprints import. Any new
   dependency must be importable under `python -c "from app import app"`.
3. **One client layer.** Frontend never calls `fetch` directly for these APIs —
   add the typed method in `desktop/src/lib/api.ts` and use it. Backend returns
   JSON with `code` on error (see `core/errors.py` handler).
4. **Design language lives in primitives, not pages.** `Card` owns the pointer
   sheen; `MetricCard`/`TiltCard`/`PageHeader` own the tile vocabulary;
   `desktop/src/index.css` owns tokens (`--surface-*`, `--radius-*`, accent
   ramp), dark/light themes, and reduced-motion CSS. A new page should read
   like the others; copy the primitive, don't fork the styles. There must be
   **exactly one copy** of the pointer/tilt plumbing.
5. **Motion & a11y.** All decorative animation must be compositor-cheap
   (transform/opacity) and parked under reduced motion, both in CSS
   (index.css) and JS (`useMotionPreference` / `prefersReducedMotion` hook).
   Charts use d3 + rAF tween with a reduced-motion bypass.
6. **Data honesty.** Readings shown must come from the poller via the API.
   Mock data exists in a few legacy panels (e.g. `DiskPage` SMART) and should
   be labeled `mock` in code if you touch them. Never fake a metric to fill a
   card — render a collecting/empty state instead (`ChartGhost.tsx` pattern).
7. **Safety.** Many optimizers mutate the live system. Every mutating step
   must stay wired through the rollback engine (`core/rollback_engine.py`).
   Tests in `tests/test_security.py` guard the origin guard — extend, don't
   bypass.

## 6. Screenshots workflow

Visual verification is scriptable (playwright): scripts live in
`screenshots/*/_shoot.py`; captures land in `screenshots/<batch>/`. Viewport
for desktop shots: 1440 width, both dark and light themes. `logs/` and
`screenshots/` are dev artifacts — never commit binaries except when the task
asks for them.

## 7. Things to NOT touch

- `archive/` (frozen Electron prototype + debug artifacts), `ui/` legacy page
  logic, `../Android-Optimizer` (sibling project, outside this repo's CI).
- `data/` runtime files, `server_pid.txt`, `config/tweak_state.json` (user state).
- `.venv/`, `logs/`, `desktop/node_modules/`, `desktop/dist/` — all regenerated.

## 8. Known quirks (so you don't "fix" them wrong)

- `useSystemInfo.ts` hook was deleted; pages get system info from
  `systemStore`/`api.ts` now. Don't re-create it.
- `npx tsc` in the repo root isn't meaningful; always `-p tsconfig.app.json`
  from `desktop/`.
- Backends/tests are Windows-first: registry, powercfg, services. macOS/Linux
  paths exist but are best-effort in `core/optimizers/*`.
- npm build may warn about chunks >500 kB (three.js); acceptable, don't chase
  code-splitting unless asked.
