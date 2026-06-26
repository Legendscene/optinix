import os
import time
import platform
import psutil
from flask import Flask, send_from_directory, jsonify, request

PORT = 5420
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=None)
_boot = time.time()
_prev_net = None
_prev_net_time = None
_gpu_cache = None
_gpu_time = 0
OS = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(platform.system(), "unknown")


@app.route("/")
def index():
    return send_from_directory(os.path.join(BASE_DIR, "ui"), "index.html")


@app.route("/<path:p>")
def statics(p):
    return send_from_directory(os.path.join(BASE_DIR, "ui"), p)


@app.route("/api/system-info")
def sysinfo():
    global _prev_net, _prev_net_time, _gpu_cache, _gpu_time
    out = {}
    try:
        out["cpu"] = {"percent": psutil.cpu_percent(interval=None), "logical": psutil.cpu_count(), "physical": psutil.cpu_count(False) or 1, "temperature": None}
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
                disks.append({"device": p.device, "mountpoint": p.mountpoint, "fstype": p.fstype, "total": u.total, "used": u.used, "free": u.free, "percent": u.percent})
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
    if not _gpu_cache or (now - _gpu_time) > 10:
        gpu = {"name": "N/A", "usage": 0, "memory_total": 0, "memory_used": 0, "temperature": 0, "driver": "N/A"}
        try:
            import subprocess
            r = subprocess.run(["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu,driver_version", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=2)
            if r.returncode == 0 and r.stdout.strip():
                p = r.stdout.strip().split(", ")
                if len(p) >= 6:
                    gpu = {"name": p[0].strip(), "usage": int(p[1]), "memory_used": int(p[2]), "memory_total": int(p[3]), "temperature": int(p[4]), "driver": p[5].strip()}
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
    try:
        if cat == "all":
            results = {}
            for n in ["cleanup", "network", "disk", "performance", "gaming", "security", "developer", "services", "overclock"]:
                try:
                    mod = __import__(f"core.optimizers.{n}", fromlist=[f"{n.title()}Optimizer"])
                    results[n] = getattr(mod, f"{n.title()}Optimizer")(OS).run()
                except:
                    pass
            return jsonify(results)
        mod = __import__(f"core.optimizers.{cat}", fromlist=[f"{cat.title()}Optimizer"])
        return jsonify({"category": cat, "results": getattr(mod, f"{cat.title()}Optimizer")(OS).run()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/background/status")
def bg_st():
    return jsonify({"running": False, "profile": "balanced"})


@app.route("/api/background/start", methods=["POST"])
def bg_go():
    return jsonify({"success": True})


@app.route("/api/background/stop", methods=["POST"])
def bg_no():
    return jsonify({"success": True})


@app.route("/health")
def health():
    return jsonify({"status": "ok", "os": OS})
