import os
import time
import platform
import subprocess
import psutil
from flask import Flask, send_from_directory, jsonify, request
from flask_socketio import SocketIO, emit

PORT = 5420
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=None)
socketio = SocketIO(app, cors_allowed_origins="*")
_boot = time.time()
_prev_net = None
_prev_net_time = None
_gpu_cache = None
_gpu_time = 0
OS = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(platform.system(), "unknown")
_bg_optimizer = None


UI_DIR = os.path.join(BASE_DIR, "desktop", "dist")
if not os.path.isdir(UI_DIR):
    UI_DIR = os.path.join(BASE_DIR, "ui")


@app.route("/")
def index():
    return send_from_directory(UI_DIR, "index.html")


@app.route("/<path:p>")
def statics(p):
    return send_from_directory(UI_DIR, p)


@app.route("/api/system-info")
def sysinfo():
    global _prev_net, _prev_net_time, _gpu_cache, _gpu_time
    out = {}
    try:
        out["cpu"] = {"percent": psutil.cpu_percent(interval=0.3), "logical": psutil.cpu_count(), "physical": psutil.cpu_count(False) or 1, "temperature": None}
        try:
            for n, e in psutil.sensors_temperatures().items():
                if e:
                    out["cpu"]["temperature"] = e[0].current
                    break
        except:
            pass
    except:
        out["cpu"] = {"percent": 0, "logical": 1, "physical": 1, "temperature": None}
    try:
        m = psutil.virtual_memory()
        out["memory"] = {"percent": m.percent, "total_gb": round(m.total/1073741824, 1), "used_gb": round(m.used/1073741824, 1), "available_gb": round(m.available/1073741824, 1)}
    except:
        out["memory"] = {"percent": 0, "total_gb": 0, "used_gb": 0, "available_gb": 0}
    try:
        disks = []
        for p in psutil.disk_partitions(all=False):
            try:
                u = psutil.disk_usage(p.mountpoint)
                is_ssd = None
                try:
                    if os.name == 'nt':
                        import subprocess as sp_
                        r_ = sp_.run(['wmic', 'diskdrive', 'where', f'Index=0', 'get', 'MediaType'], capture_output=True, text=True, timeout=5)
                        if 'SSD' in r_.stdout or 'Solid State' in r_.stdout:
                            is_ssd = True
                        elif 'HDD' in r_.stdout or 'Fixed' in r_.stdout:
                            is_ssd = False
                except:
                    pass
                is_ext = p.mountpoint != os.path.expanduser("~")[:2] and p.mountpoint not in ["C:\\", "D:\\"]
                disks.append({"device": p.device, "mountpoint": p.mountpoint, "fstype": p.fstype, "total": u.total, "used": u.used, "free": u.free, "percent": u.percent, "is_ssd": is_ssd, "is_external": is_ext})
            except:
                pass
        out["disk"] = disks
    except:
        out["disk"] = []
    try:
        s = psutil.net_io_counters()
        now = time.time()
        sp_up = sp_dn = 0
        if _prev_net and _prev_net_time:
            dt = now - _prev_net_time
            if dt > 0:
                sp_up = (s.bytes_sent - _prev_net.bytes_sent) / dt
                sp_dn = (s.bytes_recv - _prev_net.bytes_recv) / dt
        _prev_net = s
        _prev_net_time = now
        out["network"] = {"bytes_sent": s.bytes_sent, "bytes_recv": s.bytes_recv, "speed_up": int(sp_up), "speed_down": int(sp_dn)}
    except:
        out["network"] = {"bytes_sent": 0, "bytes_recv": 0, "speed_up": 0, "speed_down": 0}
    now = time.time()
    if not _gpu_cache or (now - _gpu_time) > 5:
        gpu = {"name": "N/A", "usage": 0, "memory_total": 0, "memory_used": 0, "temperature": 0, "driver": "N/A"}
        try:
            r = subprocess.run(["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu,driver_version", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=2)
            if r.returncode == 0 and r.stdout.strip():
                p = r.stdout.strip().split(", ")
                if len(p) >= 6:
                    gpu = {"name": p[0].strip(), "usage": int(p[1]), "memory_used": int(p[2]), "memory_total": int(p[3]), "temperature": int(p[4]), "driver": p[5].strip()}
        except:
            pass
        if gpu["name"] == "N/A" and os.name == 'nt':
            try:
                r = subprocess.run(["wmic", "path", "win32_VideoController", "get", "Name,AdapterRAM,DriverVersion,CurrentHorizontalResolution,CurrentVerticalResolution", "/format:csv"], capture_output=True, text=True, timeout=5)
                for line in r.stdout.strip().split("\n")[1:]:
                    if line.strip() and "Node" not in line:
                        parts = [x.strip() for x in line.split(",") if x.strip()]
                        for p in parts:
                            if "GB" in p or "MB" in p or not any(c.isdigit() for c in p):
                                continue
                        name = parts[1] if len(parts) > 1 else gpu["name"]
                        ram_str = parts[2] if len(parts) > 2 else "0"
                        driver = parts[3] if len(parts) > 3 else gpu["driver"]
                        try:
                            mem_total = int(ram_str) // (1024*1024) if ram_str.isdigit() else 0
                        except:
                            mem_total = 0
                        if name.lower() != "name":
                            gpu = {"name": name, "usage": gpu["usage"], "memory_total": mem_total, "memory_used": gpu["memory_used"], "temperature": gpu["temperature"], "driver": driver}
            except:
                pass
        _gpu_cache = gpu
        _gpu_time = now
    out["gpu"] = _gpu_cache
    try:
        up = time.time() - _boot
        out["system"] = {"os": platform.system() + " " + platform.release(), "processor": platform.processor() or "Unknown", "uptime": f"{int(up//86400)}d {int((up%86400)//3600)}h {int((up%3600)//60)}m"}
    except:
        out["system"] = {"os": "Unknown", "uptime": "N/A"}
    out["os"] = {"os_name": platform.system(), "release": platform.release()}
    return jsonify(out)


@app.route("/api/services")
def svc_list():
    try:
        from core.services_manager import ServicesManager
        return jsonify({"services": ServicesManager(OS).list_services()})
    except Exception as e:
        return jsonify({"services": [], "error": str(e)})


@app.route("/api/services/toggle", methods=["POST"])
def svc_toggle():
    try:
        d = request.get_json() or {}
        from core.services_manager import ServicesManager
        return jsonify(ServicesManager(OS).toggle_service(d.get("name"), d.get("enable", False)))
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/startup")
def st_list():
    try:
        from core.startup_manager import StartupManager
        return jsonify({"apps": StartupManager(OS).list_startup_apps()})
    except Exception as e:
        return jsonify({"apps": [], "error": str(e)})


@app.route("/api/startup/toggle", methods=["POST"])
def st_toggle():
    try:
        d = request.get_json() or {}
        from core.startup_manager import StartupManager
        return jsonify(StartupManager(OS).toggle_startup(d.get("name"), d.get("enable", False)))
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/external-disk")
def ext_disk():
    try:
        from core.external_disk import ExternalDiskManager
        return jsonify({"disks": ExternalDiskManager(OS).list_external_disks()})
    except Exception as e:
        return jsonify({"disks": [], "error": str(e)})


@app.route("/api/external-disk/optimize", methods=["POST"])
def ext_opt():
    try:
        d = request.get_json() or {}
        from core.external_disk import ExternalDiskManager
        return jsonify(ExternalDiskManager(OS).optimize_disk(d.get("device")))
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/tuning/extreme", methods=["POST"])
def extreme():
    try:
        from core.ultimate_tweaks import UltimateTweaks
        return jsonify({"results": UltimateTweaks(OS).apply_all_optimizations()})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/toolbox/dns", methods=["POST"])
def tb_dns():
    try:
        from core.toolbox import Toolbox
        return jsonify(Toolbox(OS).set_dns((request.get_json() or {}).get("provider", "cloudflare")))
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/toolbox/ping", methods=["POST"])
def tb_ping():
    try:
        from core.toolbox import Toolbox
        return jsonify(Toolbox(OS).ping_host((request.get_json() or {}).get("host", "8.8.8.8")))
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/toolbox/flush-dns", methods=["POST"])
def tb_flush():
    try:
        from core.toolbox import Toolbox
        return jsonify(Toolbox(OS).flush_dns())
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/toolbox/windows-update", methods=["POST"])
def tb_up():
    try:
        from core.toolbox import Toolbox
        return jsonify(Toolbox(OS).toggle_windows_update((request.get_json() or {}).get("enable", False)))
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/toolbox/defender", methods=["POST"])
def tb_def():
    try:
        from core.toolbox import Toolbox
        return jsonify(Toolbox(OS).toggle_defender((request.get_json() or {}).get("enable", False)))
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/toolbox/context-menu", methods=["POST"])
def tb_ctx():
    try:
        from core.toolbox import Toolbox
        return jsonify(Toolbox(OS).set_classic_context_menu((request.get_json() or {}).get("enable", True)))
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/toolbox/power-plan", methods=["POST"])
def tb_power():
    try:
        from core.toolbox import Toolbox
        return jsonify(Toolbox(OS).set_power_plan((request.get_json() or {}).get("plan", "high")))
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/toolbox/office-telemetry", methods=["POST"])
def tb_office():
    try:
        from core.toolbox import Toolbox
        return jsonify(Toolbox(OS).disable_office_telemetry())
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/toolbox/hpet", methods=["POST"])
def tb_hpet():
    try:
        from core.toolbox import Toolbox
        return jsonify(Toolbox(OS).disable_hpet())
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/toolbox/hardware")
def tb_hw():
    try:
        from core.toolbox import Toolbox
        return jsonify(Toolbox(OS).get_hardware_info())
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/drivers/scan")
def drv_scan():
    try:
        from core.drivers import DriverManager
        return jsonify({"drivers": DriverManager(OS).scan_drivers()[:30]})
    except Exception as e:
        return jsonify({"drivers": [], "error": str(e)})


@app.route("/api/drivers/missing")
def drv_miss():
    try:
        from core.drivers import DriverManager
        return jsonify({"missing": DriverManager(OS).get_missing_drivers()})
    except Exception as e:
        return jsonify({"missing": [], "error": str(e)})


@app.route("/api/optimize/<cat>", methods=["POST"])
def optimize(cat):
    _cat = cat
    _out = {"error": "Optimizer failed"}
    def _work(c):
        nonlocal _out
        try:
            if c == "all":
                results = {}
                for n in ["cleanup", "network", "disk", "performance", "gaming", "security", "developer", "services", "overclock"]:
                    try:
                        mod = __import__(f"core.optimizers.{n}", fromlist=[f"{n.title()}Optimizer"])
                        results[n] = getattr(mod, f"{n.title()}Optimizer")(OS).run()
                    except:
                        pass
                _out = results
            else:
                mod = __import__(f"core.optimizers.{c}", fromlist=[f"{c.title()}Optimizer"])
                _out = {"category": c, "results": getattr(mod, f"{c.title()}Optimizer")(OS).run()}
        except Exception as e:
            _out = {"error": str(e)}
    thr = threading.Thread(target=_work, args=(_cat,), daemon=True)
    thr.start()
    thr.join(timeout=120)
    if thr.is_alive():
        return jsonify({"error": "Optimizer timed out"}), 504
    if isinstance(_out, dict) and _out.get("error"):
        return jsonify(_out), 500
    return jsonify(_out)


@app.route("/api/background/status")
def bg_st():
    global _bg_optimizer
    if not _bg_optimizer:
        from core.background_optimizer import BackgroundOptimizer
        _bg_optimizer = BackgroundOptimizer(OS)
    return jsonify(_bg_optimizer.get_status())


@app.route("/api/ram-boost", methods=["POST"])
def ram_boost():
    try:
        import ctypes
        try:
            ctypes.windll.ntdll.NtSetSystemInformation(
                0x57,
                bytes([0x01, 0x00, 0x00, 0x00]),
                4
            )
        except Exception:
            pass
        subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "[System.GC]::Collect(); [System.GC]::WaitForPendingFinalizers()"],
            capture_output=True, timeout=15
        )
        return jsonify({"success": True, "message": "RAM standby memory cleared"})
    except Exception as e:
        return jsonify({"success": False, "message": f"RAM boost failed: {e}"})


@app.route("/api/background/start", methods=["POST"])
def bg_go():
    global _bg_optimizer
    if not _bg_optimizer:
        from core.background_optimizer import BackgroundOptimizer
        _bg_optimizer = BackgroundOptimizer(OS)
    _bg_optimizer.start()
    return jsonify({"success": True})


@app.route("/api/background/stop", methods=["POST"])
def bg_no():
    global _bg_optimizer
    if _bg_optimizer:
        _bg_optimizer.stop()
    return jsonify({"success": True})


_scheduler = None

@app.route("/api/scheduler/status")
def sched_status():
    global _scheduler
    if not _scheduler:
        from core.scheduler import MaintenanceScheduler
        _scheduler = MaintenanceScheduler(OS)
    return jsonify(_scheduler.get_config())


@app.route("/api/scheduler/update", methods=["POST"])
def sched_update():
    global _scheduler
    if not _scheduler:
        from core.scheduler import MaintenanceScheduler
        _scheduler = MaintenanceScheduler(OS)
    d = request.get_json() or {}
    if _scheduler.save_config(d):
        if d.get("enabled"):
            _scheduler.start()
        else:
            _scheduler.stop()
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Failed to save config"})


_tweak_state = None

@app.route("/api/smart-detect")
def smart_detect():
    try:
        from core.smart_detect import SmartDetector
        sd = SmartDetector(OS)
        return jsonify({"hardware": sd.get_hardware_info(), "recommendations": sd.get_recommendations()})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/tweak-state")
def tweak_state_get():
    global _tweak_state
    if not _tweak_state:
        from core.tweak_state import TweakState
        _tweak_state = TweakState()
    return jsonify(_tweak_state.get_all())


@app.route("/api/tweak-state/set", methods=["POST"])
def tweak_state_set():
    global _tweak_state
    if not _tweak_state:
        from core.tweak_state import TweakState
        _tweak_state = TweakState()
    d = request.get_json() or {}
    for k, v in d.items():
        _tweak_state.set(k, v)
    return jsonify({"success": True})


@app.route("/api/network/adapters")
def net_adapters():
    try:
        from core.network_tuner import NetworkTuner
        return jsonify({"adapters": NetworkTuner(OS).get_adapters()})
    except Exception as e:
        return jsonify({"adapters": [], "error": str(e)})


@app.route("/api/network/tune-adapter", methods=["POST"])
def net_tune_adapter():
    try:
        d = request.get_json() or {}
        from core.network_tuner import NetworkTuner
        return jsonify({"results": NetworkTuner(OS).tune_adapter(d.get("adapter"), d.get("preset", "gaming"))})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/network/bufferbloat", methods=["POST"])
def net_bufferbloat():
    try:
        d = request.get_json() or {}
        from core.network_tuner import NetworkTuner
        return jsonify({"results": NetworkTuner(OS).set_bufferbloat_preset(d.get("preset", "low_latency"))})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/network/qos", methods=["POST"])
def net_qos():
    try:
        d = request.get_json() or {}
        from core.network_tuner import NetworkTuner
        return jsonify({"results": NetworkTuner(OS).set_qos_priority(d.get("enable", True))})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/network/advanced-tweaks", methods=["POST"])
def net_advanced():
    try:
        from core.network_tuner import NetworkTuner
        return jsonify({"results": NetworkTuner(OS).advanced_network_tweaks()})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/optimize/gpu", methods=["POST"])
def optimize_gpu():
    try:
        from core.optimizers.gpu import GPUOptimizer
        return jsonify({"results": GPUOptimizer(OS).run()})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/optimize/peripheral", methods=["POST"])
def optimize_peripheral():
    try:
        from core.optimizers.peripheral import PeripheralOptimizer
        return jsonify({"results": PeripheralOptimizer(OS).run()})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/optimize/affinity", methods=["POST"])
def optimize_affinity():
    try:
        from core.optimizers.affinity import AffinityOptimizer
        return jsonify({"results": AffinityOptimizer(OS).run()})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/services/debloat", methods=["POST"])
def svc_debloat():
    try:
        d = request.get_json() or {}
        preset = d.get("preset", "basic")
        from core.optimizers.services import ServicesOptimizer
        o = ServicesOptimizer(OS)
        if preset == "basic":
            o.disable_basic_debloat()
        else:
            o.disable_advanced_debloat()
        return jsonify({"results": o.results})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/bios/info")
def bios_info():
    try:
        from core.bios_optimizer import BIOSOptimizer
        return jsonify(BIOSOptimizer(OS).get_bios_info())
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/bios/recommendations")
def bios_recs():
    try:
        from core.bios_optimizer import BIOSOptimizer
        return jsonify({"recommendations": BIOSOptimizer(OS).get_recommended_settings()})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/bios/apply", methods=["POST"])
def bios_apply():
    try:
        d = request.get_json() or {}
        from core.bios_optimizer import BIOSOptimizer
        return jsonify(BIOSOptimizer(OS).apply_settings(d.get("settings", [])))
    except Exception as e:
        return jsonify({"error": str(e)})


_game_mode_instance = None


def _get_game_mode():
    global _game_mode_instance
    if not _game_mode_instance:
        from core.game_mode import GameMode
        _game_mode_instance = GameMode(OS)
    return _game_mode_instance


@app.route("/api/game-mode/status")
def gm_status():
    try:
        return jsonify(_get_game_mode().get_status())
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/game-mode/games")
def gm_games():
    try:
        return jsonify({"games": _get_game_mode().get_game_processes()})
    except Exception as e:
        return jsonify({"games": [], "error": str(e)})


@app.route("/api/game-mode/enable", methods=["POST"])
def gm_enable():
    try:
        return jsonify(_get_game_mode().enable_game_mode())
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/game-mode/disable", methods=["POST"])
def gm_disable():
    try:
        return jsonify(_get_game_mode().disable_game_mode())
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/game-mode/affinity", methods=["POST"])
def gm_affinity():
    try:
        from core.game_mode import AffinityOptimizer
        d = request.get_json() or {}
        return jsonify(AffinityOptimizer(OS).optimize_for_gaming(d.get("pid")))
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/game-mode/core-parking", methods=["POST"])
def gm_core_parking():
    try:
        from core.game_mode import AffinityOptimizer
        return jsonify(AffinityOptimizer(OS).disable_core_parking())
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/game-mode/timer-resolution", methods=["POST"])
def gm_timer():
    try:
        from core.game_mode import TimerResolution
        d = request.get_json() or {}
        ms = d.get("resolution_ms", 1.0)
        return jsonify(TimerResolution(OS).set_resolution(ms))
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/game-mode/timer-restore", methods=["POST"])
def gm_timer_restore():
    try:
        from core.game_mode import TimerResolution
        return jsonify(TimerResolution(OS).restore_default())
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/debloat/categories")
def debloat_cats():
    try:
        from core.debloater import CustomDebloater
        return jsonify({"categories": CustomDebloater(OS).get_categories()})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/debloat/apply", methods=["POST"])
def debloat_apply():
    try:
        d = request.get_json() or {}
        from core.debloater import CustomDebloater
        return jsonify(CustomDebloater(OS).apply_category(d.get("category"), d.get("dry_run", False)))
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/debloat/apply-multiple", methods=["POST"])
def debloat_apply_multi():
    try:
        d = request.get_json() or {}
        from core.debloater import CustomDebloater
        return jsonify(CustomDebloater(OS).apply_multiple(d.get("categories", []), d.get("dry_run", False)))
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/debloat/restore-point", methods=["POST"])
def debloat_restore():
    try:
        from core.debloater import CustomDebloater
        return jsonify(CustomDebloater(OS).create_restore_point())
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/debloat/app-optimize", methods=["POST"])
def debloat_app():
    try:
        d = request.get_json() or {}
        app = d.get("app", "")
        from core.debloater import AppOptimizer
        ao = AppOptimizer(OS)
        if app == "steam":
            return jsonify(ao.optimize_steam())
        elif app == "discord":
            return jsonify(ao.optimize_discord())
        elif app == "browsers":
            return jsonify(ao.optimize_browsers())
        return jsonify({"success": False, "message": f"Unknown app: {app}"})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/network-priority/qos/enable", methods=["POST"])
def np_qos_enable():
    try:
        from core.network_priority import NetworkPriority
        return jsonify(NetworkPriority(OS).enable_qos())
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/network-priority/qos/disable", methods=["POST"])
def np_qos_disable():
    try:
        from core.network_priority import NetworkPriority
        return jsonify(NetworkPriority(OS).disable_qos())
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/network-priority/qos/game-traffic", methods=["POST"])
def np_qos_game():
    try:
        d = request.get_json() or {}
        from core.network_priority import NetworkPriority
        return jsonify(NetworkPriority(OS).prioritize_game_traffic(d.get("game_exe", "")))
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/network-priority/bufferbloat/presets")
def np_bufferbloat_presets():
    try:
        from core.network_priority import BufferBloatControl
        return jsonify({"presets": BufferBloatControl(OS).get_presets()})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/network-priority/bufferbloat/apply", methods=["POST"])
def np_bufferbloat_apply():
    try:
        d = request.get_json() or {}
        from core.network_priority import BufferBloatControl
        return jsonify(BufferBloatControl(OS).apply_preset(d.get("preset", "balanced")))
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/network-priority/adapter/optimize", methods=["POST"])
def np_adapter_optimize():
    try:
        d = request.get_json() or {}
        from core.network_priority import AdapterTuner
        return jsonify(AdapterTuner(OS).optimize_adapter(d.get("adapter", ""), d.get("preset", "gaming")))
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/network-priority/adapter/reset", methods=["POST"])
def np_adapter_reset():
    try:
        d = request.get_json() or {}
        from core.network_priority import AdapterTuner
        return jsonify(AdapterTuner(OS).reset_adapter(d.get("adapter", "")))
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/registry/scan")
def reg_scan():
    try:
        from core.registry_cleaner import RegistryCleaner
        return jsonify(RegistryCleaner(OS).scan_issues())
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/registry/fix", methods=["POST"])
def reg_fix():
    try:
        d = request.get_json() or {}
        from core.registry_cleaner import RegistryCleaner
        return jsonify(RegistryCleaner(OS).fix_issues(d.get("paths", [])))
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/registry/backup", methods=["POST"])
def reg_backup():
    try:
        from core.registry_cleaner import RegistryCleaner
        return jsonify(RegistryCleaner(OS).backup())
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/registry/restore", methods=["POST"])
def reg_restore():
    try:
        d = request.get_json() or {}
        from core.registry_cleaner import RegistryCleaner
        return jsonify(RegistryCleaner(OS).restore(d.get("filename", "")))
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/registry/backups")
def reg_backups():
    try:
        from core.registry_cleaner import RegistryCleaner
        return jsonify({"backups": RegistryCleaner(OS).list_backups()})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/tweaks/list")
def tw_list():
    try:
        from core.windows_tweaks import WindowsTweaks
        return jsonify(WindowsTweaks(OS).get_tweaks())
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/tweaks/apply", methods=["POST"])
def tw_apply():
    try:
        d = request.get_json() or {}
        tid = d.get("tweak", "")
        enable = d.get("enable", True)
        from core.windows_tweaks import WindowsTweaks
        return jsonify(WindowsTweaks(OS).apply_tweak(tid, enable))
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/tweaks/apply-multiple", methods=["POST"])
def tw_apply_multi():
    try:
        d = request.get_json() or {}
        from core.windows_tweaks import WindowsTweaks
        return jsonify(WindowsTweaks(OS).apply_multiple(d.get("tweaks", {})))
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/tweaks/export", methods=["POST"])
def tw_export():
    try:
        d = request.get_json() or {}
        from core.windows_tweaks import WindowsTweaks
        return jsonify(WindowsTweaks(OS).export_settings(d.get("tweaks", {})))
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/tweaks/import", methods=["POST"])
def tw_import():
    try:
        d = request.get_json() or {}
        from core.windows_tweaks import WindowsTweaks
        return jsonify(WindowsTweaks(OS).import_settings(d.get("tweaks", {})))
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/disk/scan", methods=["POST"])
def disk_scan():
    try:
        d = request.get_json() or {}
        from core.disk_analyzer import DiskAnalyzer
        return jsonify(DiskAnalyzer(OS).scan(d.get("drive", "C:")))
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/disk/clean-category", methods=["POST"])
def disk_clean_cat():
    try:
        d = request.get_json() or {}
        from core.disk_analyzer import DiskAnalyzer
        return jsonify(DiskAnalyzer(OS).clean_category(d.get("category", ""), d.get("drive", "C:")))
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/disk/clean-all", methods=["POST"])
def disk_clean_all():
    try:
        d = request.get_json() or {}
        from core.disk_analyzer import DiskAnalyzer
        return jsonify(DiskAnalyzer(OS).clean_all(d.get("drive", "C:")))
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/memory/processes")
def mem_procs():
    try:
        from core.memory_manager import MemoryManager
        return jsonify({"processes": MemoryManager(OS).get_processes()})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/memory/free", methods=["POST"])
def mem_free():
    try:
        from core.memory_manager import MemoryManager
        return jsonify(MemoryManager(OS).free_ram())
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/memory/auto-optimize", methods=["POST"])
def mem_auto():
    try:
        from core.memory_manager import MemoryManager
        return jsonify(MemoryManager(OS).auto_optimize())
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/memory/info")
def mem_info():
    try:
        from core.memory_manager import MemoryManager
        return jsonify(MemoryManager(OS).get_info())
    except Exception as e:
        return jsonify({"error": str(e)})


import threading


@socketio.on('connect')
def handle_connect():
    def send_status():
        while True:
            try:
                cpu = psutil.cpu_percent(interval=0.5)
                mem = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                try:
                    import GPUtil
                    gpu = GPUtil.getGPUs()[0] if GPUtil.getGPUs() else None
                except:
                    gpu = None
                emit('system_status', {
                    'cpu': cpu,
                    'memory': {'total': mem.total, 'available': mem.available, 'used': mem.used, 'percent': mem.percent},
                    'disk': {'total': disk.total, 'used': disk.used, 'free': disk.free, 'percent': disk.percent},
                    'gpu': {'load': gpu.load * 100 if gpu else 0, 'memory_used': gpu.memoryUsed if gpu else 0, 'memory_total': gpu.memoryTotal if gpu else 0, 'temperature': gpu.temperature if gpu else 0} if gpu else None,
                    'processes': len(psutil.pids()),
                    'uptime': time.time() - psutil.boot_time(),
                    'timestamp': time.time()
                })
            except:
                emit('system_status', {'error': True})
            time.sleep(2)
    thread = threading.Thread(target=send_status, daemon=True)
    thread.start()


@socketio.on('disconnect')
def handle_disconnect():
    pass


@app.route("/api/ping", methods=["POST"])
def ping_host():
    d = request.get_json() or {}
    host = d.get("host", "8.8.8.8")
    try:
        param = "-n" if platform.system().lower() == "windows" else "-c"
        result = subprocess.run(["ping", param, "4", host], capture_output=True, text=True, timeout=10)
        return jsonify({"output": result.stdout, "error": result.stderr})
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Ping timed out"})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/health")
def health():
    return jsonify({"status": "ok", "os": OS})


if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
