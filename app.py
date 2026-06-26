import os
import json
import subprocess
from flask import Flask, send_from_directory, jsonify, request
from core.detector import OSDetector
from core.scanner import SystemScanner
from core.optimizers import (
    CleanupOptimizer, NetworkOptimizer, DiskOptimizer,
    PerformanceOptimizer, GamingOptimizer, SecurityOptimizer,
    DeveloperOptimizer, ServicesOptimizer, OverclockOptimizer
)

PORT = 5420
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=None)

detector = OSDetector()
os_type = detector.detect()
scanner = SystemScanner(os_type)

OPTIMIZERS = {
    "cleanup": CleanupOptimizer,
    "network": NetworkOptimizer,
    "disk": DiskOptimizer,
    "performance": PerformanceOptimizer,
    "gaming": GamingOptimizer,
    "security": SecurityOptimizer,
    "developer": DeveloperOptimizer,
    "services": ServicesOptimizer,
    "overclock": OverclockOptimizer
}


@app.route("/")
def index():
    return send_from_directory(os.path.join(BASE_DIR, "ui"), "index.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(os.path.join(BASE_DIR, "ui"), path)


@app.route("/api/system-info")
def system_info():
    try:
        info = scanner.full_scan()
        info["os"] = detector.get_info()
        return jsonify(info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/services")
def list_services():
    try:
        from core.services_manager import ServicesManager
        mgr = ServicesManager(os_type)
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
        mgr = ServicesManager(os_type)
        result = mgr.toggle_service(name, enable)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/startup")
def list_startup():
    try:
        from core.startup_manager import StartupManager
        mgr = StartupManager(os_type)
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
        mgr = StartupManager(os_type)
        result = mgr.toggle_startup(name, enable)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/external-disk")
def list_external_disks():
    try:
        from core.external_disk import ExternalDiskManager
        mgr = ExternalDiskManager(os_type)
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
        mgr = ExternalDiskManager(os_type)
        result = mgr.optimize_disk(device)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tuning/extreme", methods=["POST"])
def extreme_tuning():
    try:
        from core.ultimate_tweaks import UltimateTweaks
        tuner = UltimateTweaks(os_type)
        results = tuner.apply_all_optimizations()
        return jsonify({"results": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tuning/list")
def list_tweaks():
    try:
        from core.ultimate_tweaks import UltimateTweaks
        tuner = UltimateTweaks(os_type)
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
        tuner = UltimateTweaks(os_type)
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
    tb = Toolbox(os_type)
    return jsonify(tb.set_dns(provider))


@app.route("/api/toolbox/ping", methods=["POST"])
def toolbox_ping():
    data = request.get_json() or {}
    host = data.get("host", "8.8.8.8")
    from core.toolbox import Toolbox
    tb = Toolbox(os_type)
    return jsonify(tb.ping_host(host))


@app.route("/api/toolbox/flush-dns", methods=["POST"])
def toolbox_flush_dns():
    from core.toolbox import Toolbox
    tb = Toolbox(os_type)
    return jsonify(tb.flush_dns())


@app.route("/api/toolbox/windows-update", methods=["POST"])
def toolbox_windows_update():
    data = request.get_json() or {}
    enable = data.get("enable", False)
    from core.toolbox import Toolbox
    tb = Toolbox(os_type)
    return jsonify(tb.toggle_windows_update(enable))


@app.route("/api/toolbox/defender", methods=["POST"])
def toolbox_defender():
    data = request.get_json() or {}
    enable = data.get("enable", False)
    from core.toolbox import Toolbox
    tb = Toolbox(os_type)
    return jsonify(tb.toggle_defender(enable))


@app.route("/api/toolbox/context-menu", methods=["POST"])
def toolbox_context_menu():
    data = request.get_json() or {}
    enable = data.get("enable", True)
    from core.toolbox import Toolbox
    tb = Toolbox(os_type)
    return jsonify(tb.set_classic_context_menu(enable))


@app.route("/api/toolbox/power-plan", methods=["POST"])
def toolbox_power_plan():
    data = request.get_json() or {}
    plan = data.get("plan", "high")
    from core.toolbox import Toolbox
    tb = Toolbox(os_type)
    return jsonify(tb.set_power_plan(plan))


@app.route("/api/toolbox/office-telemetry", methods=["POST"])
def toolbox_office_telemetry():
    from core.toolbox import Toolbox
    tb = Toolbox(os_type)
    return jsonify(tb.disable_office_telemetry())


@app.route("/api/toolbox/hpet", methods=["POST"])
def toolbox_hpet():
    from core.toolbox import Toolbox
    tb = Toolbox(os_type)
    return jsonify(tb.disable_hpet())


@app.route("/api/toolbox/hardware")
def toolbox_hardware():
    from core.toolbox import Toolbox
    tb = Toolbox(os_type)
    return jsonify(tb.get_hardware_info())


@app.route("/api/toolbox/hosts")
def toolbox_hosts():
    from core.toolbox import Toolbox
    tb = Toolbox(os_type)
    return jsonify(tb.get_hosts())


# === DRIVER ENDPOINTS ===
@app.route("/api/drivers/scan")
def drivers_scan():
    from core.drivers import DriverManager
    mgr = DriverManager(os_type)
    return jsonify({"drivers": mgr.scan_drivers()[:50]})


@app.route("/api/drivers/missing")
def drivers_missing():
    from core.drivers import DriverManager
    mgr = DriverManager(os_type)
    return jsonify({"missing": mgr.get_missing_drivers()})


@app.route("/api/drivers/links")
def drivers_links():
    from core.drivers import DriverManager
    mgr = DriverManager(os_type)
    return jsonify(mgr.get_driver_links())


@app.route("/api/optimize/<category>", methods=["POST"])
def optimize(category):
    try:
        if category == "all":
            results = {}
            for name, cls in OPTIMIZERS.items():
                optimizer = cls(os_type)
                results[name] = optimizer.run()
            return jsonify(results)

        if category not in OPTIMIZERS:
            return jsonify({"error": f"Unknown: {category}"}), 400

        optimizer = OPTIMIZERS[category](os_type)
        results = optimizer.run()
        return jsonify({"category": category, "results": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health")
def health():
    return jsonify({"status": "ok", "os": os_type, "version": "1.0.0"})
