import os
import subprocess
from flask import Flask, send_from_directory, jsonify, request

PORT = 5420
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=None)

_detector = None
_os_type = "unknown"
_scanner = None


def get_detector():
    global _detector, _os_type
    if _detector is None:
        try:
            from core.detector import OSDetector
            _detector = OSDetector()
            _os_type = _detector.detect()
        except Exception:
            _os_type = "unknown"
    return _detector


def get_os():
    get_detector()
    return _os_type


def get_scanner():
    global _scanner
    if _scanner is None:
        try:
            from core.scanner import SystemScanner
            _scanner = SystemScanner(get_os())
        except Exception:
            pass
    return _scanner


def get_opt(name):
    try:
        from core.optimizers import (
            CleanupOptimizer, NetworkOptimizer, DiskOptimizer,
            PerformanceOptimizer, GamingOptimizer, SecurityOptimizer,
            DeveloperOptimizer, ServicesOptimizer, OverclockOptimizer
        )
        m = {
            "cleanup": CleanupOptimizer, "network": NetworkOptimizer,
            "disk": DiskOptimizer, "performance": PerformanceOptimizer,
            "gaming": GamingOptimizer, "security": SecurityOptimizer,
            "developer": DeveloperOptimizer, "services": ServicesOptimizer,
            "overclock": OverclockOptimizer
        }
        cls = m.get(name)
        if cls:
            return cls(get_os())
    except Exception:
        pass
    return None


@app.route("/")
def index():
    return send_from_directory(os.path.join(BASE_DIR, "ui"), "index.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(os.path.join(BASE_DIR, "ui"), path)


@app.route("/api/system-info")
def system_info():
    try:
        scanner = get_scanner()
        if scanner:
            info = scanner.full_scan()
        else:
            info = {"cpu": {"percent": 0, "logical": 1}, "memory": {"percent": 0, "total_gb": 0, "used_gb": 0},
                    "disk": [], "network": {"speed_up": 0, "speed_down": 0, "bytes_sent": 0, "bytes_recv": 0},
                    "gpu": {"name": "N/A", "usage": 0}, "system": {"os": "Unknown", "uptime": "N/A"}}
        det = get_detector()
        info["os"] = det.get_info() if det else {"os_name": get_os()}
        return jsonify(info)
    except Exception as e:
        return jsonify({"error": str(e), "cpu": {"percent": 0}, "memory": {"percent": 0}, "disk": [],
                        "network": {"speed_up": 0, "speed_down": 0}, "gpu": {"name": "N/A", "usage": 0},
                        "system": {"os": "Unknown", "uptime": "N/A"}, "os": {"os_name": get_os()}})


@app.route("/api/services")
def list_services():
    try:
        from core.services_manager import ServicesManager
        return jsonify({"services": ServicesManager(get_os()).list_services()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/services/toggle", methods=["POST"])
def toggle_service():
    try:
        d = request.get_json() or {}
        from core.services_manager import ServicesManager
        return jsonify(ServicesManager(get_os()).toggle_service(d.get("name"), d.get("enable", False)))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/startup")
def list_startup():
    try:
        from core.startup_manager import StartupManager
        return jsonify({"apps": StartupManager(get_os()).list_startup_apps()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/startup/toggle", methods=["POST"])
def toggle_startup():
    try:
        d = request.get_json() or {}
        from core.startup_manager import StartupManager
        return jsonify(StartupManager(get_os()).toggle_startup(d.get("name"), d.get("enable", False)))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/external-disk")
def list_external_disks():
    try:
        from core.external_disk import ExternalDiskManager
        return jsonify({"disks": ExternalDiskManager(get_os()).list_external_disks()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/external-disk/optimize", methods=["POST"])
def optimize_external_disk():
    try:
        d = request.get_json() or {}
        from core.external_disk import ExternalDiskManager
        return jsonify(ExternalDiskManager(get_os()).optimize_disk(d.get("device")))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tuning/extreme", methods=["POST"])
def extreme_tuning():
    try:
        from core.ultimate_tweaks import UltimateTweaks
        return jsonify({"results": UltimateTweaks(get_os()).apply_all_optimizations()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tuning/list")
def list_tweaks():
    try:
        from core.ultimate_tweaks import UltimateTweaks
        t = UltimateTweaks(get_os())
        return jsonify({"registry_count": len(t.get_all_registry_tweaks()),
                        "services_count": len(t.get_all_services()),
                        "bloatware_count": len(t.get_all_bloatware()),
                        "tasks_count": len(t.get_scheduled_tasks())})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/bloatware/remove", methods=["POST"])
def remove_bloatware():
    try:
        from core.ultimate_tweaks import UltimateTweaks
        bloatware = UltimateTweaks(get_os()).get_all_bloatware()
        removed = 0
        for app_name in bloatware:
            try:
                subprocess.run(["powershell", "-Command",
                    f"Get-AppxPackage -Name {app_name} -EA SilentlyContinue | Remove-AppxPackage -EA SilentlyContinue"],
                    capture_output=True, timeout=30)
                removed += 1
            except Exception:
                continue
        return jsonify({"success": True, "message": f"Removed {removed} bloatware apps"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/toolbox/dns", methods=["POST"])
def toolbox_dns():
    d = request.get_json() or {}
    from core.toolbox import Toolbox
    return jsonify(Toolbox(get_os()).set_dns(d.get("provider", "cloudflare")))


@app.route("/api/toolbox/ping", methods=["POST"])
def toolbox_ping():
    d = request.get_json() or {}
    from core.toolbox import Toolbox
    return jsonify(Toolbox(get_os()).ping_host(d.get("host", "8.8.8.8")))


@app.route("/api/toolbox/flush-dns", methods=["POST"])
def toolbox_flush_dns():
    from core.toolbox import Toolbox
    return jsonify(Toolbox(get_os()).flush_dns())


@app.route("/api/toolbox/windows-update", methods=["POST"])
def toolbox_windows_update():
    d = request.get_json() or {}
    from core.toolbox import Toolbox
    return jsonify(Toolbox(get_os()).toggle_windows_update(d.get("enable", False)))


@app.route("/api/toolbox/defender", methods=["POST"])
def toolbox_defender():
    d = request.get_json() or {}
    from core.toolbox import Toolbox
    return jsonify(Toolbox(get_os()).toggle_defender(d.get("enable", False)))


@app.route("/api/toolbox/context-menu", methods=["POST"])
def toolbox_context_menu():
    d = request.get_json() or {}
    from core.toolbox import Toolbox
    return jsonify(Toolbox(get_os()).set_classic_context_menu(d.get("enable", True)))


@app.route("/api/toolbox/power-plan", methods=["POST"])
def toolbox_power_plan():
    d = request.get_json() or {}
    from core.toolbox import Toolbox
    return jsonify(Toolbox(get_os()).set_power_plan(d.get("plan", "high")))


@app.route("/api/toolbox/office-telemetry", methods=["POST"])
def toolbox_office_telemetry():
    from core.toolbox import Toolbox
    return jsonify(Toolbox(get_os()).disable_office_telemetry())


@app.route("/api/toolbox/hpet", methods=["POST"])
def toolbox_hpet():
    from core.toolbox import Toolbox
    return jsonify(Toolbox(get_os()).disable_hpet())


@app.route("/api/toolbox/hardware")
def toolbox_hardware():
    from core.toolbox import Toolbox
    return jsonify(Toolbox(get_os()).get_hardware_info())


@app.route("/api/drivers/scan")
def drivers_scan():
    from core.drivers import DriverManager
    return jsonify({"drivers": DriverManager(get_os()).scan_drivers()[:50]})


@app.route("/api/drivers/missing")
def drivers_missing():
    from core.drivers import DriverManager
    return jsonify({"missing": DriverManager(get_os()).get_missing_drivers()})


@app.route("/api/optimize/<category>", methods=["POST"])
def optimize(category):
    try:
        if category == "all":
            results = {}
            for name in ["cleanup", "network", "disk", "performance", "gaming", "security", "developer", "services", "overclock"]:
                opt = get_opt(name)
                if opt:
                    results[name] = opt.run()
            return jsonify(results)
        opt = get_opt(category)
        if not opt:
            return jsonify({"error": f"Unknown: {category}"}), 400
        return jsonify({"category": category, "results": opt.run()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health")
def health():
    return jsonify({"status": "ok", "os": get_os(), "version": "1.0.0"})


# === BACKGROUND OPTIMIZER ===
_bg_optimizer = None

def get_bg_optimizer():
    global _bg_optimizer
    if _bg_optimizer is None:
        try:
            from core.background_optimizer import BackgroundOptimizer
            _bg_optimizer = BackgroundOptimizer(get_os())
        except Exception:
            pass
    return _bg_optimizer


@app.route("/api/background/status")
def bg_status():
    try:
        opt = get_bg_optimizer()
        if opt:
            return jsonify(opt.get_status())
        return jsonify({"running": False, "current_profile": "unknown", "detected_apps": []})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/background/start", methods=["POST"])
def bg_start():
    try:
        opt = get_bg_optimizer()
        if opt:
            opt.start()
            return jsonify({"success": True, "message": "Background optimizer started"})
        return jsonify({"success": False, "message": "Failed to initialize"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/background/stop", methods=["POST"])
def bg_stop():
    try:
        opt = get_bg_optimizer()
        if opt:
            opt.stop()
            return jsonify({"success": True, "message": "Background optimizer stopped"})
        return jsonify({"success": False, "message": "Not running"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
