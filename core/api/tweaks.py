import os
import platform

from flask import Blueprint, jsonify, request

OS = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(platform.system(), "unknown")
tweaks_bp = Blueprint("tweaks", __name__)


@tweaks_bp.route("/api/tweaks/list")
def tw_list():
    try:
        from core.windows_tweaks import WindowsTweaks
        return jsonify(WindowsTweaks(OS).get_tweaks())
    except Exception as e:
        return jsonify({"error": str(e)})


@tweaks_bp.route("/api/tweaks/apply", methods=["POST"])
def tw_apply():
    try:
        d = request.get_json() or {}
        tid = d.get("tweak", "")
        enable = d.get("enable", True)
        from core.windows_tweaks import WindowsTweaks
        return jsonify(WindowsTweaks(OS).apply_tweak(tid, enable))
    except Exception as e:
        return jsonify({"error": str(e)})


@tweaks_bp.route("/api/tweaks/apply-multiple", methods=["POST"])
def tw_apply_multi():
    try:
        d = request.get_json() or {}
        from core.windows_tweaks import WindowsTweaks
        return jsonify(WindowsTweaks(OS).apply_multiple(d.get("tweaks", {})))
    except Exception as e:
        return jsonify({"error": str(e)})


@tweaks_bp.route("/api/tweaks/export", methods=["POST"])
def tw_export():
    try:
        d = request.get_json() or {}
        from core.windows_tweaks import WindowsTweaks
        return jsonify(WindowsTweaks(OS).export_settings(d.get("tweaks", {})))
    except Exception as e:
        return jsonify({"error": str(e)})


@tweaks_bp.route("/api/tweaks/import", methods=["POST"])
def tw_import():
    try:
        d = request.get_json() or {}
        from core.windows_tweaks import WindowsTweaks
        return jsonify(WindowsTweaks(OS).import_settings(d.get("tweaks", {})))
    except Exception as e:
        return jsonify({"error": str(e)})
