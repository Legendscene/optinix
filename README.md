# Optinix — PC Optimizer

Desktop application for Windows system optimization: Python backend (Flask + pywebview), React/TypeScript frontend, and one Electron prototype kept in `archive/`.

## Directory map

```
PC-Optimizer/            ← repository root (this file's directory)
├── run.py               ← one-shot launcher: start server + open browser
├── main.py              ← pywebview desktop window entry point
├── app.py               ← Flask + SocketIO server (serves desktop/dist)
├── build.spec           ← PyInstaller spec (packages the desktop app)
├── installer.py         ← install helper
├── requirements.txt     ← Python dependencies
├── pytest.ini           ← backend test config
├── core/                ← Python backend: optimizers, API, monitoring, game library, AI
├── config/              ← tweak state and other config consumed at runtime
├── desktop/             ← React/TypeScript frontend (built to desktop/dist, served by app.py)
├── ui/                  ← legacy static dashboard, kept as fallback UI dir (see core/config.py)
├── tests/               ← backend pytest suite
├── scripts/             ← helper scripts (PowerShell network tool)
├── plugins/             ← plugin modules loaded at runtime
├── data/                ← runtime data (metrics, history, artwork cache, reports, timeline)
├── docs/                ← architecture notes and background docs
├── logs/                ← local log files (gitignored)
└── archive/             ← kept-but-not-active material (see below)
    ├── pc-optimizer-prototype/  ← earlier Electron+React "Command Center" prototype (mock data only)
    └── debug-artifacts/          ← one-off screenshots/playwright snapshots
```

## What each part does

- **Backend** — `app.py` boots Flask + SocketIO on `127.0.0.1:5420`, registers all API blueprints from `core/api*` modules, and serves the built frontend from `desktop/dist`. `run.py` wraps that in a browser-open loop and is the easiest way to launch the app for development.
- **Frontend** — `desktop/` is a Vite + React + TypeScript app. `npm run build` outputs to `desktop/dist/`, which `core/config.py` selects as `CONFIG.ui_dir` automatically. The `ui/` directory is only used if `desktop/dist` is missing, so the legacy dashboard still works without a frontend build.
- **Desktop packaging** — `main.py` opens the same server inside a pywebview window. `build.spec` packages that into a Windows `.exe` via PyInstaller (`pyinstaller build.spec`), bundling `desktop/dist` as the UI.

## Prerequisites

- **Python 3.9+** (3.14 is what's currently used locally)
- **Node.js 20+** (only needed to rebuild the frontend, `desktop/`)
- Per-OS notes: Windows gets full registry/services/power plan control; macOS and Linux use safer sysctl/systemd/launchd paths.

## Setup

```bash
# Backend
python -m venv .venv
.venv\Scripts\activate          # Windows  (source .venv/bin/activate elsewhere)
pip install -r requirements.txt

# Frontend (only needed if you change desktop/ source)
cd desktop
npm ci
npm run build                   # outputs to dist/, backend picks it up automatically
```

## Running

```bash
# Easiest: backend + browser frontend together
python run.py

# With the native pywebview window instead of a browser
python main.py
```

Frontend development loop (hot reload on port 5173):

```bash
cd desktop
npm run dev
```

## Tests & checks

```bash
# Backend
python -m pytest

# Frontend (from desktop/)
npx tsc -p tsconfig.app.json --noEmit   # typecheck
npm run lint
npm run test                             # vitest
npm run build
```

All four currently pass (see Verification section below).

## Runtime data & logs

- Metrics/history/reports/timeline live in `data/` (metrics ~9 MB currently). The artwork cache is `data/artwork_cache/` and is gitignored.
- Per-process logs go to `%TEMP%\optinix_logs` by default (`core/config.py`), with 30-day retention.
- Local dev logs and one-off debug snapshots from hacking sessions go into `logs/` and `archive/debug-artifacts/`, both gitignored.

## Building the desktop installer

```bash
pip install pyinstaller
pyinstaller build.spec
```

Output lands in `dist/PC Optimizer/` (contains `Optinix.exe` or similar). Electron NSIS installer from the archived prototype is **not** the current shipping artifact — that older Electron app is preserved in `archive/pc-optimizer-prototype/` for reference only.

## Verification (2026-10-20)

- Backend imports cleanly (`from app import app, socketio, PORT` → OK, port 5420).
- Backend tests: `python -m pytest -q` → 163 passed, exit 0.
- Frontend typecheck: `npx tsc -p tsconfig.app.json --noEmit` → exit 0.
- Frontend tests: `npm run test` in `desktop/` → 86 passed (10 files), exit 0.
- Frontend production build: `npm run build` → built in 610ms, exit 0.

## Archived material

- `archive/pc-optimizer-prototype/` — the earlier Electron + React + Vite "Command Center" prototype. It used its own mock data and was never integrated with the Python backend. Kept intact (including `node_modules`, `dist`, `release/Optinix-Setup-1.0.0.exe`) so nothing is lost; it is gitignored. Do not wire it up without rewriting its data layer.
- `archive/debug-artifacts/` — screenshots and Playwright snapshots captured during debugging sessions.

## Android-Optimizer

`../Android-Optimizer` is a separate sibling project and is not part of this repository's build or test pipeline. It is intentionally left untouched.

## License

MIT
