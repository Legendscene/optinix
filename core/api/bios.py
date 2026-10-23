import os
import platform
from flask import Blueprint, jsonify, request

OS = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(platform.system(), "unknown")
bios_bp = Blueprint("bios", __name__)


@bios_bp.route("/api/bios/info")
def bios_info():
    try:
        from core.bios_optimizer import BIOSOptimizer
        return jsonify(BIOSOptimizer(OS).get_bios_info())
    except Exception as e:
        return jsonify({"error": str(e)})


@bios_bp.route("/api/bios/recommendations")
def bios_recs():
    try:
        from core.bios_optimizer import BIOSOptimizer
        return jsonify({"recommendations": BIOSOptimizer(OS).get_recommended_settings()})
    except Exception as e:
        return jsonify({"error": str(e)})


@bios_bp.route("/api/bios/apply", methods=["POST"])
def bios_apply():
    try:
        d = request.get_json() or {}
        from core.bios_optimizer import BIOSOptimizer
        return jsonify(BIOSOptimizer(OS).apply_settings(d.get("settings", [])))
    except Exception as e:
        return jsonify({"error": str(e)})
