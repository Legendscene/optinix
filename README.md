# Optinix — PC Optimizer

Desktop application for system optimization. Supports Windows, macOS, and Linux.

Built with Python + pywebview for a native app feel. Packages to `.exe` via PyInstaller.

## Features

### 9 Optimization Modules

| Module | What it does |
|--------|-------------|
| **Cleanup** | Temp files, browser cache, crash dumps, thumbnails, logs, DNS, prefetch, Windows Update cache, recycle bin |
| **Network** | TCP/IP tuning, DNS (Cloudflare), Nagle disable, buffer bloat, MTU, fast open, BBR congestion, port range |
| **Performance** | Kill heavy processes, high performance power plan, virtual memory, CPU governor, kernel params |
| **Disk** | SSD TRIM, SMART health check, large file finder, disk space analysis |
| **Gaming** | Game mode, GPU priority, Game DVR off, fullscreen opt off, mouse accel off, shader cache, visual effects |
| **Services** | Disable telemetry, Cortana, Xbox, widgets, edge updates, scheduled tasks, startup apps |
| **Security** | Remove bloatware, disable telemetry tasks, firewall harden, advertising ID off, location tracking off |
| **Overclock** | CPU timing, memory management, GPU scheduling, power limits, timer resolution, core parking, prefetch |
| **Developer** | npm/pip cache, pycache, git gc, Docker prune, IDE cache, build artifacts |

### Cross-Platform

- **Windows**: Full registry, services, power plan, GPU, networking
- **macOS**: TCP tuning, cache cleanup, privacy, launch agents
- **Linux**: sysctl, systemd services, CPU governor, BBR, fstrim

## Installation

```bash
git clone https://github.com/Legendscene/optinix.git
cd optinix
pip install -r requirements.txt
python main.py
```

## Build .exe

```bash
pip install pyinstaller
pyinstaller build.spec
```

Output in `dist/PC Optimizer/`

## Tech Stack

- Python 3.9+
- Flask (backend API)
- pywebview (native window)
- psutil (system monitoring)
- PyInstaller (packaging)

## License

MIT
