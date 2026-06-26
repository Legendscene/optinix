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
