import os
import platform
from flask import Blueprint, jsonify, request

OS = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(platform.system(), "unknown")
scheduler_bp = Blueprint("scheduler", __name__)
_scheduler = None


@scheduler_bp.route("/api/scheduler/status")
def sched_status():
    global _scheduler
    if not _scheduler:
        from core.scheduler import MaintenanceScheduler
        _scheduler = MaintenanceScheduler(OS)
    return jsonify(_scheduler.get_config())


@scheduler_bp.route("/api/scheduler/update", methods=["POST"])
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
