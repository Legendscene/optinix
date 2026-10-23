import os
import platform

from flask import Blueprint, jsonify, request

OS = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(platform.system(), "unknown")
startup_bp = Blueprint("startup", __name__)


@startup_bp.route("/api/startup")
def st_list():
    try:
        from core.startup_manager import StartupManager
        return jsonify({"apps": StartupManager(OS).list_startup_apps()})
    except Exception as e:
        return jsonify({"apps": [], "error": str(e)})


@startup_bp.route("/api/startup/toggle", methods=["POST"])
def st_toggle():
    try:
        d = request.get_json() or {}
        from core.startup_manager import StartupManager
        return jsonify(StartupManager(OS).toggle_startup(d.get("name"), d.get("enable", False)))
    except Exception as e:
        return jsonify({"error": str(e)})


@startup_bp.route("/api/startup/timer")
def startup_timer():
    try:
        from core.system_repair import StartupTimer
        return jsonify(StartupTimer().get_startup_times())
    except Exception as e:
        return jsonify({"error": str(e)})
