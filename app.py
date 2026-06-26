import os
import json
import subprocess
from flask import Flask, send_from_directory, jsonify, request

PORT = 5420
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=None)

_detector = None
_get_os() = "unknown"
_scanner = None

def get_detector():
    global _detector, _get_os()
    if _detector is None:
        try:
            from core.detector import OSDetector
            _detector = OSDetector()
            _get_os() = _detector.detect()
        except Exception:
            _get_os() = "unknown"
    return _detector

def get_os():
    get_detector()
    return _get_os()

def get_scanner():
    global _scanner
    if _scanner is None:
        try:
            from core.scanner import SystemScanner
            _scanner = SystemScanner(get_os())
        except Exception:
            pass
    return _scanner

def get_optimizer(name):
    try:
        from core.optimizers import (
            CleanupOptimizer, NetworkOptimizer, DiskOptimizer,
            PerformanceOptimizer, GamingOptimizer, SecurityOptimizer,
            DeveloperOptimizer, ServicesOptimizer, OverclockOptimizer
        )
        mapping = {
            "cleanup": CleanupOptimizer, "network": NetworkOptimizer,
            "disk": DiskOptimizer, "performance": PerformanceOptimizer,
            "gaming": GamingOptimizer, "security": SecurityOptimizer,
            "developer": DeveloperOptimizer, "services": ServicesOptimizer,
            "overclock": OverclockOptimizer
        }
        cls = mapping.get(name)
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
            info = {"cpu":{"percent":0,"logical":1,"physical":1},"memory":{"percent":0,"total_gb":0,"used_gb":0},"disk":[],"network":{"bytes_sent":0,"bytes_recv":0,"speed_up":0,"speed_down":0},"gpu":{"name":"N/A","usage":0},"processes":[],"system":{"os":"Unknown","uptime":"N/A"}}
        det = get_detector()
        info["os"] = det.get_info() if det else {"os_name": get_os()}
        return jsonify(info)
    except Exception as e:
        return jsonify({"error": str(e), "cpu":{"percent":0},"memory":{"percent":0},"disk":[],"network":{"speed_up":0,"speed_down":0},"gpu":{"name":"N/A","usage":0},"system":{"os":"Unknown","uptime":"N/A"},"os":{"os_name":get_os()}})


@app.route("/api/services")
def list_services():
    try:
        from core.services_manager import ServicesManager
        mgr = ServicesManager(get_os())
        services = mgr.list_services()
        return jsonify({"services": services})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/services/toggle", methods=["POST"])
def toggle_service():
    try:
        data = request.get_json() or {}
        name = data.get("name")
        enable = data.get("enable", False)
        from core.services_manager import ServicesManager
        mgr = ServicesManager(get_os())
        result = mgr.toggle_service(name, enable)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/startup")
def list_startup():
    try:
        from core.startup_manager import StartupManager
        mgr = StartupManager(get_os())
        apps = mgr.list_startup_apps()
        return jsonify({"apps": apps})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/startup/toggle", methods=["POST"])
def toggle_startup():
    try:
        data = request.get_json() or {}
        name = data.get("name")
        enable = data.get("enable", False)
        from core.startup_manager import StartupManager
        mgr = StartupManager(get_os())
        result = mgr.toggle_startup(name, enable)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/external-disk")
def list_external_disks():
    try:
        from core.external_disk import ExternalDiskManager
        mgr = ExternalDiskManager(get_os())
        disks = mgr.list_external_disks()
        return jsonify({"disks": disks})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/external-disk/optimize", methods=["POST"])
def optimize_external_disk():
    try:
        data = request.get_json() or {}
        device = data.get("device")
        from core.external_disk import ExternalDiskManager
        mgr = ExternalDiskManager(get_os())
        result = mgr.optimize_disk(device)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tuning/extreme", methods=["POST"])
def extreme_tuning():
    try:
        from core.ultimate_tweaks import UltimateTweaks
        tuner = UltimateTweaks(get_os())
        results = tuner.apply_all_optimizations()
        return jsonify({"results": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tuning/list")
def list_tweaks():
    try:
        from core.ultimate_tweaks import UltimateTweaks
        tuner = UltimateTweaks(get_os())
        return jsonify({
            "registry_count": len(tuner.get_all_registry_tweaks()),
            "services_count": len(tuner.get_all_services()),
            "bloatware_count": len(tuner.get_all_bloatware()),
            "tasks_count": len(tuner.get_scheduled_tasks())
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/bloatware/remove", methods=["POST"])
def remove_bloatware():
    try:
        from core.ultimate_tweaks import UltimateTweaks
        tuner = UltimateTweaks(get_os())
        bloatware = tuner.get_all_bloatware()
        removed = 0
        for app_name in bloatware:
            try:
                subprocess.run(
                    ["powershell", "-Command",
                     f"Get-AppxPackage -Name {app_name} -EA SilentlyContinue | Remove-AppxPackage -EA SilentlyContinue"],
                    capture_output=True, timeout=30
                )
                removed += 1
            except Exception:
                continue
        return jsonify({"success": True, "message": f"Removed {removed} bloatware apps"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# === TOOLBOX ENDPOINTS ===
@app.route("/api/toolbox/dns", methods=["POST"])
def toolbox_dns():
    data = request.get_json() or {}
    provider = data.get("provider", "cloudflare")
    from core.toolbox import Toolbox
    tb = Toolbox(get_os())
    return jsonify(tb.set_dns(provider))


@app.route("/api/toolbox/ping", methods=["POST"])
def toolbox_ping():
    data = request.get_json() or {}
    host = data.get("host", "8.8.8.8")
    from core.toolbox import Toolbox
    tb = Toolbox(get_os())
    return jsonify(tb.ping_host(host))


@app.route("/api/toolbox/flush-dns", methods=["POST"])
def toolbox_flush_dns():
    from core.toolbox import Toolbox
    tb = Toolbox(get_os())
    return jsonify(tb.flush_dns())


@app.route("/api/toolbox/windows-update", methods=["POST"])
def toolbox_windows_update():
    data = request.get_json() or {}
    enable = data.get("enable", False)
    from core.toolbox import Toolbox
    tb = Toolbox(get_os())
    return jsonify(tb.toggle_windows_update(enable))


@app.route("/api/toolbox/defender", methods=["POST"])
def toolbox_defender():
    data = request.get_json() or {}
    enable = data.get("enable", False)
    from core.toolbox import Toolbox
    tb = Toolbox(get_os())
    return jsonify(tb.toggle_defender(enable))


@app.route("/api/toolbox/context-menu", methods=["POST"])
def toolbox_context_menu():
    data = request.get_json() or {}
    enable = data.get("enable", True)
    from core.toolbox import Toolbox
    tb = Toolbox(get_os())
    return jsonify(tb.set_classic_context_menu(enable))


@app.route("/api/toolbox/power-plan", methods=["POST"])
def toolbox_power_plan():
    data = request.get_json() or {}
    plan = data.get("plan", "high")
    from core.toolbox import Toolbox
    tb = Toolbox(get_os())
    return jsonify(tb.set_power_plan(plan))


@app.route("/api/toolbox/office-telemetry", methods=["POST"])
def toolbox_office_telemetry():
    from core.toolbox import Toolbox
    tb = Toolbox(get_os())
    return jsonify(tb.disable_office_telemetry())


@app.route("/api/toolbox/hpet", methods=["POST"])
def toolbox_hpet():
    from core.toolbox import Toolbox
    tb = Toolbox(get_os())
    return jsonify(tb.disable_hpet())


@app.route("/api/toolbox/hardware")
def toolbox_hardware():
    from core.toolbox import Toolbox
    tb = Toolbox(get_os())
    return jsonify(tb.get_hardware_info())


@app.route("/api/toolbox/hosts")
def toolbox_hosts():
    from core.toolbox import Toolbox
    tb = Toolbox(get_os())
    return jsonify(tb.get_hosts())


# === DRIVER ENDPOINTS ===
@app.route("/api/drivers/scan")
def drivers_scan():
    from core.drivers import DriverManager
    mgr = DriverManager(get_os())
    return jsonify({"drivers": mgr.scan_drivers()[:50]})


@app.route("/api/drivers/missing")
def drivers_missing():
    from core.drivers import DriverManager
    mgr = DriverManager(get_os())
    return jsonify({"missing": mgr.get_missing_drivers()})


@app.route("/api/drivers/links")
def drivers_links():
    from core.drivers import DriverManager
    mgr = DriverManager(get_os())
    return jsonify(mgr.get_driver_links())


@app.route("/api/optimize/<category>", methods=["POST"])
def optimize(category):
    try:
        if category == "all":
            results = {}
            for name in ["cleanup","network","disk","performance","gaming","security","developer","services","overclock"]:
                opt = get_optimizer(name)
                if opt:
                    results[name] = opt.run()
            return jsonify(results)
        opt = get_optimizer(category)
        if not opt:
            return jsonify({"error": f"Unknown: {category}"}), 400
        return jsonify({"category": category, "results": opt.run()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health")
def health():
    return jsonify({"status": "ok", "os": get_os(), "version": "1.0.0"})


@app.route("/api/settings/theme", methods=["POST"])
def set_theme():
    data = request.get_json() or {}
    theme = data.get("theme", "dark")
    return jsonify({"success": True, "theme": theme})
