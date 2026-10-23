import os
import platform
from flask import Blueprint, jsonify, request

OS = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(platform.system(), "unknown")
debloat_bp = Blueprint("debloat", __name__)


@debloat_bp.route("/api/debloat/categories")
def debloat_cats():
    try:
        from core.debloater import CustomDebloater
        return jsonify({"categories": CustomDebloater(OS).get_categories()})
    except Exception as e:
        return jsonify({"error": str(e)})


@debloat_bp.route("/api/debloat/apply", methods=["POST"])
def debloat_apply():
    try:
        d = request.get_json() or {}
        from core.debloater import CustomDebloater
        return jsonify(CustomDebloater(OS).apply_category(d.get("category"), d.get("dry_run", False)))
    except Exception as e:
        return jsonify({"error": str(e)})


@debloat_bp.route("/api/debloat/apply-multiple", methods=["POST"])
def debloat_apply_multi():
    try:
        d = request.get_json() or {}
        from core.debloater import CustomDebloater
        return jsonify(CustomDebloater(OS).apply_multiple(d.get("categories", []), d.get("dry_run", False)))
    except Exception as e:
        return jsonify({"error": str(e)})


@debloat_bp.route("/api/debloat/restore-point", methods=["POST"])
def debloat_restore():
    try:
        from core.debloater import CustomDebloater
        return jsonify(CustomDebloater(OS).create_restore_point())
    except Exception as e:
        return jsonify({"error": str(e)})


@debloat_bp.route("/api/debloat/app-optimize", methods=["POST"])
def debloat_app():
    try:
        d = request.get_json() or {}
        app = d.get("app", "")
        from core.debloater import AppOptimizer
        ao = AppOptimizer(OS)
        if app == "steam":
            return jsonify(ao.optimize_steam())
        elif app == "discord":
            return jsonify(ao.optimize_discord())
        elif app == "browsers":
            return jsonify(ao.optimize_browsers())
        return jsonify({"success": False, "message": f"Unknown app: {app}"})
    except Exception as e:
        return jsonify({"error": str(e)})
