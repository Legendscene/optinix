import os
import platform

from flask import Blueprint, jsonify, request

OS = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(platform.system(), "unknown")
services_bp = Blueprint("services", __name__)


@services_bp.route("/api/services")
def svc_list():
    try:
        from core.services_manager import ServicesManager
        return jsonify({"services": ServicesManager(OS).list_services()})
    except Exception as e:
        return jsonify({"services": [], "error": str(e)})


@services_bp.route("/api/services/toggle", methods=["POST"])
def svc_toggle():
    try:
        d = request.get_json() or {}
        from core.services_manager import ServicesManager
        return jsonify(ServicesManager(OS).toggle_service(d.get("name"), d.get("enable", False)))
    except Exception as e:
        return jsonify({"error": str(e)})
