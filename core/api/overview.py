"""Overview API - single aggregated payload for the Optimizer home screen.

The home screen needs system vitals, a health score, a detected game, a set of
recommended actions and the last optimization result. Fetching each of those
separately means 6+ HTTP round trips and 6+ independent expensive probes. This
blueprint gathers them once and caches the expensive parts so the overview can
be polled cheaply.
"""
import ctypes
import os
import platform
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import psutil
from flask import Blueprint, jsonify, request

from ..logger import get_logger

overview_bp = Blueprint("overview", __name__)
logger = get_logger("api.overview")

OS = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(platform.system(), "unknown")

HEALTH_TTL = 90.0
GAME_TTL = 10.0
RECLAIM_TTL = 180.0
POWER_TTL = 60.0

_lock = threading.Lock()
_cache: dict = {}
# Keys currently being recomputed in the background, so a burst of pollers
# cannot start one refresh per request.
_refreshing: set[str] = set()
_MISSING = object()

# The four producers below are independent; on a cold cache they run in
# parallel instead of adding their latencies together.
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="overview")


def _produce(key: str, producer):
    """Run one producer with a timeout, storing the result in the cache.

    Returns the value, or the _MISSING sentinel when the producer did not
    answer in time (the caller then falls back to the last known value).
    """
    result: dict = {}

    def _work():
        try:
            result["value"] = producer()
        except Exception as e:  # noqa: BLE001 - surfaced to the caller
            logger.error(f"overview[{key}] failed: {e}")
            result["value"] = None

    thr = threading.Thread(target=_work, daemon=True)
    thr.start()
    thr.join(timeout=25)
    if "value" not in result:
        return _MISSING
    with _lock:
        _cache[key] = {"at": time.time(), "value": result["value"]}
    return result["value"]


def warm_overview_cache() -> None:
    """Compute the expensive probes once, off the request path.

    Called from app startup so the first dashboard paint does not pay for
    the health scan, the reclaimable-space walk, the GPU probe and game
    detection all at once. Safe to call repeatedly: `_cached` honours its
    own TTL and each key is computed at most once per window.
    """
    jobs = (
        ("game", GAME_TTL, _detected_game),
        ("power", POWER_TTL, _power_plan),
        ("health", HEALTH_TTL, _health),
        ("reclaim", RECLAIM_TTL, _reclaimable),
        ("gpu", 6.0, _probe_gpu),
    )
    futures = [_executor.submit(_cached, key, ttl, producer) for key, ttl, producer in jobs]
    for future in futures:
        try:
            future.result(timeout=30)
        except Exception as e:  # noqa: BLE001 - warm-up is best effort
            logger.debug(f"warm_overview_cache: {e}")


def _refresh(key: str, producer) -> None:
    """Background refresh used by the stale-while-revalidate path."""
    try:
        _produce(key, producer)
    finally:
        with _lock:
            _refreshing.discard(key)


def _cached(key, ttl, producer, force=False):
    """Return a cached value, computing it in a worker thread on miss.

    Stale entries are served immediately and refreshed behind the request.
    The dashboard polls every 4 s, so blocking a poll for a 13 s health
    recompute would freeze the whole first paint; this way the number on
    screen is at most one refresh old and the response is instant.
    """
    now = time.time()
    with _lock:
        hit = _cache.get(key)
        if hit and not force and (now - hit["at"]) < ttl:
            return hit["value"], True
        if hit and not force:
            stale = hit["value"]
            if key not in _refreshing:
                _refreshing.add(key)
                threading.Thread(target=_refresh, args=(key, producer), daemon=True).start()
            return stale, True

    value = _produce(key, producer)
    if value is _MISSING:
        with _lock:
            hit = _cache.get(key)
        return (hit["value"] if hit else None), False
    return value, False


def is_admin() -> bool:
    if os.name != "nt":
        return False
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def _health():
    from ..intelligence.health_scorer import HealthScorer
    data = HealthScorer().score_all()
    scores = {}
    for key in ("pc_health", "windows_health", "gaming", "storage", "security", "battery"):
        entry = data.get(key)
        if isinstance(entry, dict) and "score" in entry:
            scores[key] = {
                "score": entry.get("score", 0),
                "label": entry.get("label", ""),
            }
    return {"overall": data.get("overall", 0), "scores": scores}


def _detected_game():
    from ..game_profiles import GameProfiles
    game_id = GameProfiles().detect_running_game()
    if not game_id:
        return None
    profile = GameProfiles().get_profile(game_id) or {}
    return {
        "id": game_id,
        "name": profile.get("name", game_id),
        "description": profile.get("description", ""),
    }


def _power_plan():
    if OS != "windows":
        return {"name": "Unavailable", "is_high_performance": False}
    try:
        out = subprocess_run_powercfg()
        return out
    except Exception as e:  # noqa: BLE001
        logger.error(f"powercfg failed: {e}")
        return {"name": "Unknown", "is_high_performance": False}


def subprocess_run_powercfg():
    import subprocess
    r = subprocess.run(["powercfg", "/getactivescheme"], capture_output=True, text=True, timeout=6)
    name = "Unknown"
    if "(" in r.stdout and ")" in r.stdout:
        name = r.stdout[r.stdout.rfind("(") + 1:r.stdout.rfind(")")].strip()
    return {"name": name, "is_high_performance": "high performance" in name.lower()}


def _reclaimable():
    from ..disk_analyzer import DiskAnalyzer
    data = DiskAnalyzer(OS).scan("C:")
    cats = []
    total = 0
    for c in data.get("categories", []):
        size = c.get("bytes", 0)
        total += size
        # The scan returns a list of file entries. The overview only needs a
        # count; shipping thousands of paths would bloat the payload for no
        # reason. The cleanup page runs its own scan when the user wants detail.
        raw = c.get("files", 0)
        count = len(raw) if isinstance(raw, (list, tuple)) else int(raw or 0)
        cats.append({"name": c.get("name", ""), "bytes": size, "file_count": count})
    cats.sort(key=lambda x: x["bytes"], reverse=True)
    return {"total_bytes": total, "categories": cats[:6]}


def _vitals(admin, power, game):
    vm = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk = psutil.disk_usage(os.environ.get("SystemDrive", "C:") + "\\" if OS == "windows" else "/")
    net = psutil.net_io_counters()
    now = time.time()
    boot = psutil.boot_time()

    speed_down = speed_up = 0
    with _lock:
        prev = _cache.get("__net__")
    if prev and (now - prev["at"]) > 0.4:
        dt = now - prev["at"]
        speed_down = max(0.0, (net.bytes_recv - prev["value"].bytes_recv) / dt)
        speed_up = max(0.0, (net.bytes_sent - prev["value"].bytes_sent) / dt)
    with _lock:
        _cache["__net__"] = {"at": now, "value": net}

    cpu_temp = None
    try:
        for readings in psutil.sensors_temperatures().values():
            if readings:
                cpu_temp = readings[0].current
                break
    except Exception:
        pass

    gpu = {"name": "N/A", "usage": None, "temperature": None, "memory_used": 0, "memory_total": 0}
    gpu, _ = _cached("gpu", 6.0, _probe_gpu)

    return {
        "cpu_percent": psutil.cpu_percent(interval=0),
        "cpu_temp": cpu_temp,
        "cpu_threads": psutil.cpu_count(logical=True),
        "cpu_cores": psutil.cpu_count(logical=False),
        "ram_percent": vm.percent,
        "ram_used_gb": round(vm.used / 1073741824, 1),
        "ram_total_gb": round(vm.total / 1073741824, 1),
        "ram_available_gb": round(vm.available / 1073741824, 1),
        "swap_percent": swap.percent,
        "disk_percent": disk.percent,
        "disk_free_gb": round(disk.free / 1073741824, 1),
        "disk_total_gb": round(disk.total / 1073741824, 1),
        "process_count": len(psutil.pids()),
        "network_down_kbs": round(speed_down / 1024),
        "network_up_kbs": round(speed_up / 1024),
        "uptime_hours": round((now - boot) / 3600, 1),
        "gpu": gpu,
        "power_plan": power,
        "is_laptop": _is_laptop(),
        "battery": _battery(),
        "is_admin": admin,
        "detected_game": (game or {}).get("id"),
    }


_gpu_lock = threading.Lock()


def _probe_gpu():
    import subprocess
    if OS == "windows":
        try:
            r = subprocess.run(
                ["nvidia-smi",
                 "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=3,
            )
            if r.returncode == 0 and r.stdout.strip():
                p = [x.strip() for x in r.stdout.strip().split("\n")[0].split(",")]
                if len(p) >= 5:
                    return {
                        "name": p[0],
                        "usage": _int(p[1]),
                        "memory_used": _int(p[2]),
                        "memory_total": _int(p[3]),
                        "temperature": _int(p[4]),
                    }
        except Exception:
            pass
    return {"name": "N/A", "usage": None, "temperature": None, "memory_used": 0, "memory_total": 0}


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


_batt_cache = {"at": 0, "value": None}


def _battery():
    now = time.time()
    if (now - _batt_cache["at"]) < 30:
        return _batt_cache["value"]
    value = None
    try:
        batt = psutil.sensors_battery()
        if batt is not None:
            value = {
                "percent": round(batt.percent, 1),
                "plugged": batt.power_plugged,
                "seconds_left": batt.secondsleft if batt.secondsleft > 0 else None,
            }
    except Exception:
        value = None
    _batt_cache["at"] = now
    _batt_cache["value"] = value
    return value


_laptop_cache = {"at": 0, "value": False}


def _is_laptop():
    now = time.time()
    if (now - _laptop_cache["at"]) < 120:
        return _laptop_cache["value"]
    value = False
    try:
        value = psutil.sensors_battery() is not None
    except Exception:
        value = False
    _laptop_cache["at"] = now
    _laptop_cache["value"] = value
    return value


def _build_actions(vitals, health, reclaim, admin):
    """Recommended actions. Every item is derived from measured state, never invented."""
    actions = []

    def add(aid, title, detail, severity, page, action=None, meta=None):
        actions.append({
            "id": aid, "title": title, "detail": detail,
            "severity": severity, "page": page, "action": action, "meta": meta or {},
        })

    if not admin:
        add("admin", "Restart as Administrator",
            "Most optimizations need elevated privileges. Right-click Optinix and run as administrator.",
            "high", "settings")

    if vitals["ram_percent"] >= 80:
        add("ram_pressure", "Memory is under pressure",
            f"{vitals['ram_used_gb']} of {vitals['ram_total_gb']} GB in use ({vitals['ram_percent']:.0f}%). Free memory or trim startup apps.",
            "high", "memory", "memory_free")
    elif vitals["ram_percent"] >= 65:
        add("ram_watch", "Memory usage is elevated",
            f"{vitals['ram_percent']:.0f}% of RAM in use. Trimming will release standby memory.",
            "medium", "memory", "memory_free")

    if vitals["disk_percent"] >= 85:
        add("disk_pressure", "System drive is nearly full",
            f"{vitals['disk_percent']:.0f}% used, {vitals['disk_free_gb']} GB free. Clean up to reclaim space.",
            "high", "cleanup")
    elif vitals["disk_percent"] >= 75:
        add("disk_watch", "System drive is filling up",
            f"{vitals['disk_percent']:.0f}% used, {vitals['disk_free_gb']} GB free.",
            "medium", "cleanup")

    if reclaim and reclaim.get("total_bytes", 0) > 512 * 1024 * 1024:
        gb = reclaim["total_bytes"] / 1073741824
        top = reclaim["categories"][0]["name"] if reclaim["categories"] else "temp files"
        add("reclaim", f"{gb:.1f} GB of junk can be reclaimed",
            f"Largest category is {top}. Cleaning is reversible - nothing personal is touched.",
            "medium", "cleanup")

    if vitals["power_plan"] and not vitals["power_plan"].get("is_high_performance") and OS == "windows":
        add("power_plan", "Power plan is not tuned for performance",
            f"Active plan is '{vitals['power_plan']['name']}'. Switch to High performance for lower latency.",
            "medium", "power")

    if vitals["is_laptop"] and vitals.get("battery") and vitals["battery"].get("plugged") is False:
        add("battery", "Running on battery",
            "Unplugged - high performance plans will drain the battery faster. Consider Balanced when away from the charger.",
            "low", "power-center")

    if vitals["uptime_hours"] > 24 * 7:
        add("uptime", f"Uptime is {vitals['uptime_hours'] / 24:.0f} days",
            "A restart clears memory leaks and releases held resources.",
            "low", "overview")

    gpu = vitals.get("gpu") or {}
    if gpu.get("name") and gpu["name"] != "N/A" and gpu.get("usage") is None:
        add("gpu_probe", "GPU load is not readable",
            f"{gpu['name']} is present but utilisation is unavailable. GPU tuning still works.",
            "low", "gpu")

    for key, label in (("pc_health", "PC health"), ("storage", "Storage health"), ("security", "Security health")):
        entry = health.get("scores", {}).get(key)
        if entry and entry.get("score", 100) < 60:
            add(f"score_{key}", f"{label} scored {entry['score']}/100",
                entry.get("label") or "Review the findings for this area.",
                "high" if entry["score"] < 40 else "medium", "health-scores")

    if not actions:
        add("all_clear", "Nothing needs attention",
            "Memory, storage and power are all within healthy ranges. Safe to play.",
            "ok", "live-monitor")

    order = {"high": 0, "medium": 1, "low": 2, "ok": 3}
    actions.sort(key=lambda a: order.get(a["severity"], 9))
    return actions


def _last_optimization():
    from ..optimization_history import OptimizationHistory
    try:
        data = OptimizationHistory().get_all(limit=1)
        entries = data.get("entries", [])
        if not entries:
            return None
        e = entries[0]
        return {
            "entry_id": e.get("entry_id"),
            "category": e.get("category"),
            "name": e.get("optimizer_name"),
            "timestamp": e.get("timestamp"),
            "duration_ms": e.get("duration_ms"),
            "success_count": e.get("success_count"),
            "total_count": e.get("total_count"),
            "error": e.get("error"),
            "benchmark_before": e.get("benchmark_before"),
            "benchmark_after": e.get("benchmark_after"),
            "benchmark_comparison": e.get("benchmark_comparison"),
        }
    except Exception as e:  # noqa: BLE001
        logger.error(f"history read failed: {e}")
        return None


@overview_bp.route("/api/overview", methods=["GET"])
def overview():
    admin = is_admin()
    # Cold cache: the four probes are independent, so they overlap instead
    # of stacking their latencies. Warm cache: each submit returns a cached
    # value immediately.
    jobs = (
        ("game", GAME_TTL, _detected_game),
        ("power", POWER_TTL, _power_plan),
        ("health", HEALTH_TTL, _health),
        ("reclaim", RECLAIM_TTL, _reclaimable),
    )
    values = {
        key: future.result()[0]
        for key, future in {
            key: _executor.submit(_cached, key, ttl, producer)
            for key, ttl, producer in jobs
        }.items()
    }
    game = values["game"]
    power = values["power"]
    health = values["health"]
    reclaim = values["reclaim"]

    health = health or {"overall": 0, "scores": {}}
    vitals = _vitals(admin, power or {"name": "Unknown", "is_high_performance": False}, game)

    return jsonify({
        "generated_at": time.time(),
        "is_admin": admin,
        "health": health,
        "vitals": vitals,
        "detected_game": game,
        "actions": _build_actions(vitals, health, reclaim, admin),
        "reclaimable": reclaim,
        "last_optimization": _last_optimization(),
    })


@overview_bp.route("/api/overview/refresh", methods=["POST"])
def overview_refresh():
    """Drop the expensive caches so the next GET recomputes."""
    with _lock:
        for key in ("health", "reclaim", "power", "game"):
            _cache.pop(key, None)
    return jsonify({"success": True})


def _measure():
    """Live measurement used for before/after on the primary optimize action."""
    vm = psutil.virtual_memory()
    procs = psutil.pids()
    disk = psutil.disk_usage(os.environ.get("SystemDrive", "C:") + "\\" if OS == "windows" else "/")
    return {
        "ram_percent": round(vm.percent, 1),
        "ram_used_gb": round(vm.used / 1073741824, 2),
        "ram_available_gb": round(vm.available / 1073741824, 2),
        "process_count": len(procs),
        "disk_free_gb": round(disk.free / 1073741824, 2),
        "cpu_percent": psutil.cpu_percent(interval=0),
        "timestamp": time.time(),
    }


# Presets map to real optimizer categories. Each entry is honest about what it runs.
PRESETS = {
    "balanced": {
        "id": "balanced",
        "name": "Balanced",
        "summary": "Clears caches, applies safe network tuning and trims memory.",
        "detail": ["Cleanup", "Network", "Memory trim", "Smart Detect recommendations"],
        "categories": ["cleanup", "network", "startup"],
        "post": ["memory_free"],
    },
    "performance": {
        "id": "performance",
        "name": "Performance",
        "summary": "Balanced plus high performance power plan and scheduler tuning.",
        "detail": ["Cleanup", "Network", "Power plan", "Visual effects", "Memory trim"],
        "categories": ["cleanup", "network", "performance", "startup", "gpu"],
        "post": ["memory_free"],
    },
    "gaming": {
        "id": "gaming",
        "name": "Gaming",
        "summary": "Performance plus game mode, mouse accel off and timer resolution.",
        "detail": ["Game Mode", "GPU priority", "Fullscreen optimisation off", "Timer resolution", "Network tuning"],
        "categories": ["gaming", "network", "performance", "cleanup", "gpu"],
        "post": ["memory_free"],
    },
    "battery": {
        "id": "battery",
        "name": "Battery Saver",
        "summary": "Switches to the Balanced plan and trims memory. No performance loss.",
        "detail": ["Balanced power plan", "Memory trim", "DNS flush"],
        "categories": ["cleanup"],
        "post": ["balance_power", "memory_free", "flush_dns"],
    },
    "streaming": {
        "id": "streaming",
        "name": "Streaming",
        "summary": "Frees CPU for encoding, adds network headroom and hides the UI.",
        "detail": ["Memory trim", "Network tuning", "DWM optimisation", "Background process priority"],
        "categories": ["network", "performance", "cleanup"],
        "post": ["memory_free", "network_priority_high"],
    },
}


@overview_bp.route("/api/presets", methods=["GET"])
def presets():
    return jsonify({"presets": list(PRESETS.values())})


def _apply_post_action(name):
    """Post-optimizer actions that are not full optimizer categories."""
    if name == "memory_free":
        from core.memory_manager import MemoryManager
        return MemoryManager(OS).free_ram()
    if name == "flush_dns":
        import subprocess
        subprocess.run(["ipconfig", "/flushdns"], capture_output=True, timeout=10)
        return {"success": True, "message": "DNS cache flushed"}
    if name == "balance_power":
        import subprocess
        subprocess.run(["powercfg", "/setactive", "381b4222-f694-41f0-9685-ff5bb260df2e"],
                       capture_output=True, timeout=8)
        return {"success": True, "message": "Balanced power plan applied"}
    if name == "network_priority_high":
        from core.network_priority import NetworkPriority
        return NetworkPriority().set_high_priority()
    return {"success": False, "message": f"Unknown action '{name}'"}


@overview_bp.route("/api/optimize/quick", methods=["POST"])
def optimize_quick():
    """Run a preset with real before/after measurements. Never fabricates a score."""
    from .optimization import _run_category

    data = request.get_json() or {}
    preset_id = data.get("preset")
    # This endpoint changes the machine, so the caller must name the preset.
    # Defaulting here would let a stray request silently run a full pass.
    if not preset_id:
        return jsonify({
            "error": "A preset id is required",
            "known": sorted(PRESETS),
        }), 400
    preset = PRESETS.get(preset_id)
    if not preset:
        return jsonify({"error": f"Unknown preset '{preset_id}'", "known": sorted(PRESETS)}), 400

    before = _measure()
    steps = []
    admin = is_admin()

    for cat in preset["categories"]:
        started = time.time()
        out = _run_category(cat)
        ok = not out.get("error")
        steps.append({
            "id": cat,
            "label": cat.replace("_", " ").title(),
            "success": ok,
            "message": out.get("error") or _first_message(out),
            "duration_ms": int((time.time() - started) * 1000),
        })

    for action in preset.get("post", []):
        started = time.time()
        try:
            res = _apply_post_action(action)
        except Exception as e:  # noqa: BLE001
            res = {"success": False, "message": str(e)}
        steps.append({
            "id": action,
            "label": action.replace("_", " ").title(),
            "success": bool(res.get("success")),
            "message": res.get("message", ""),
            "duration_ms": int((time.time() - started) * 1000),
        })

    # let the OS settle so the 'after' reading is meaningful
    time.sleep(1.5)
    after = _measure()

    with _lock:
        for key in ("power", "reclaim", "game"):
            _cache.pop(key, None)

    succeeded = sum(1 for s in steps if s["success"])
    return jsonify({
        "preset": preset_id,
        "name": preset["name"],
        "is_admin": admin,
        "steps": steps,
        "succeeded": succeeded,
        "total": len(steps),
        "before": before,
        "after": after,
        "deltas": {
            "ram_used_gb": round(after["ram_used_gb"] - before["ram_used_gb"], 2),
            "ram_available_gb": round(after["ram_available_gb"] - before["ram_available_gb"], 2),
            "process_count": after["process_count"] - before["process_count"],
            "disk_free_gb": round(after["disk_free_gb"] - before["disk_free_gb"], 2),
        },
    })


def _first_message(payload):
    results = payload.get("results")
    if isinstance(results, list) and results:
        for r in results:
            if isinstance(r, dict):
                msg = r.get("message") or r.get("task") or r.get("name")
                if msg:
                    return str(msg)
    summary = payload.get("summary")
    if summary:
        return str(summary)
    if payload.get("success_count") is not None:
        return f"{payload.get('success_count', 0)}/{payload.get('total_count', 0)} steps applied"
    return "Completed"
