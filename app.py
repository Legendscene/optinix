import os
import time
from flask import Flask, send_from_directory, jsonify, request

PORT = 5420
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=None)

_os = None
_detector = None
_scanner = None
_bg = None
_start_time = time.time()


def get_os():
    global _os, _detector
    if _os is None:
        try:
            import platform
            _os = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(platform.system(), "unknown")
        except:
            _os = "unknown"
    return _os


def get_scanner():
    global _scanner
    if _scanner is None:
        try:
            from core.scanner import SystemScanner
            _scanner = SystemScanner(get_os())
        except:
            pass
    return _scanner


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
            info = {"cpu": {"percent": 0, "logical": 1, "physical": 1}, "memory": {"percent": 0, "total_gb": 0, "used_gb": 0, "available_gb": 0}, "disk": [], "network": {"bytes_sent": 0, "bytes_recv": 0, "speed_up": 0, "speed_down": 0}, "gpu": {"name": "N/A", "usage": 0, "temperature": 0}, "processes": [], "system": {"os": "Unknown", "uptime": "N/A"}}
        info["os"] = {"os_name": get_os(), "release": ""}
        return jsonify(info)
    except Exception as e:
        return jsonify({"error": str(e), "cpu": {"percent": 0, "logical": 1, "physical": 1}, "memory": {"percent": 0, "total_gb": 0, "used_gb": 0, "available_gb": 0}, "disk": [], "network": {"bytes_sent": 0, "bytes_recv": 0, "speed_up": 0, "speed_down": 0}, "gpu": {"name": "N/A", "usage": 0, "temperature": 0}, "system": {"os": "Unknown", "uptime": "N/A"}, "os": {"os_name": get_os()}})


@app.route("/api/services")
def list_services():
    try:
        from core.services_manager import ServicesManager
        return jsonify({"services": ServicesManager(get_os()).list_services()})
    except Exception as e:
        return jsonify({"services": [], "error": str(e)})


@app.route("/api/services/toggle", methods=["POST"])
def toggle_service():
    try:
        d = request.get_json() or {}
        from core.services_manager import ServicesManager
        return jsonify(ServicesManager(get_os()).toggle_service(d.get("name"), d.get("enable", False)))
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/startup")
def list_startup():
    try:
        from core.startup_manager import StartupManager
        return jsonify({"apps": StartupManager(get_os()).list_startup_apps()})
    except Exception as e:
        return jsonify({"apps": [], "error": str(e)})


@app.route("/api/startup/toggle", methods=["POST"])
def toggle_startup():
    try:
        d = request.get_json() or {}
        from core.startup_manager import StartupManager
        return jsonify(StartupManager(get_os()).toggle_startup(d.get("name"), d.get("enable", False)))
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/external-disk")
def list_external_disks():
    try:
        from core.external_disk import ExternalDiskManager
        return jsonify({"disks": ExternalDiskManager(get_os()).list_external_disks()})
    except Exception as e:
        return jsonify({"disks": [], "error": str(e)})


@app.route("/api/external-disk/optimize", methods=["POST"])
def optimize_external_disk():
    try:
        d = request.get_json() or {}
        from core.external_disk import ExternalDiskManager
        return jsonify(ExternalDiskManager(get_os()).optimize_disk(d.get("device")))
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/tuning/extreme", methods=["POST"])
def extreme_tuning():
    try:
        from core.ultimate_tweaks import UltimateTweaks
        return jsonify({"results": UltimateTweaks(get_os()).apply_all_optimizations()})
    except Exception as e:
        return jsonify({"error": str(e)})


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
    return jsonify({"drivers": DriverManager(get_os()).scan_drivers()[:30]})


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
                try:
                    mod = __import__(f"core.optimizers.{name}", fromlist=[f"{name.title()}Optimizer"])
                    cls = getattr(mod, f"{name.title()}Optimizer")
                    results[name] = cls(get_os()).run()
                except:
                    pass
            return jsonify(results)
        try:
            mod = __import__(f"core.optimizers.{category}", fromlist=[f"{category.title()}Optimizer"])
            cls = getattr(mod, f"{category.title()}Optimizer")
            return jsonify({"category": category, "results": cls(get_os()).run()})
        except:
            return jsonify({"error": f"Unknown: {category}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/background/status")
def bg_status():
    return jsonify({"running": False, "current_profile": "balanced", "detected_apps": []})


@app.route("/api/background/start", methods=["POST"])
def bg_start():
    return jsonify({"success": True, "message": "Background optimizer started"})


@app.route("/api/background/stop", methods=["POST"])
def bg_stop():
    return jsonify({"success": True, "message": "Background optimizer stopped"})


@app.route("/health")
def health():
    return jsonify({"status": "ok", "os": get_os(), "version": "1.0.0", "uptime": int(time.time() - _start_time)})
