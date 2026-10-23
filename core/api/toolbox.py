import os
import platform

from flask import Blueprint, jsonify, request

OS = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(platform.system(), "unknown")
toolbox_bp = Blueprint("toolbox", __name__)


@toolbox_bp.route("/api/toolbox/dns", methods=["POST"])
def tb_dns():
    try:
        from core.toolbox import Toolbox
        return jsonify(Toolbox(OS).set_dns((request.get_json() or {}).get("provider", "cloudflare")))
    except Exception as e:
        return jsonify({"error": str(e)})


@toolbox_bp.route("/api/toolbox/ping", methods=["POST"])
def tb_ping():
    try:
        from core.toolbox import Toolbox
        return jsonify(Toolbox(OS).ping_host((request.get_json() or {}).get("host", "8.8.8.8")))
    except Exception as e:
        return jsonify({"error": str(e)})


@toolbox_bp.route("/api/toolbox/flush-dns", methods=["POST"])
def tb_flush():
    try:
        from core.toolbox import Toolbox
        return jsonify(Toolbox(OS).flush_dns())
    except Exception as e:
        return jsonify({"error": str(e)})


@toolbox_bp.route("/api/toolbox/windows-update", methods=["POST"])
def tb_up():
    try:
        from core.toolbox import Toolbox
        return jsonify(Toolbox(OS).toggle_windows_update((request.get_json() or {}).get("enable", False)))
    except Exception as e:
        return jsonify({"error": str(e)})


@toolbox_bp.route("/api/toolbox/defender", methods=["POST"])
def tb_def():
    try:
        from core.toolbox import Toolbox
        return jsonify(Toolbox(OS).toggle_defender((request.get_json() or {}).get("enable", False)))
    except Exception as e:
        return jsonify({"error": str(e)})


@toolbox_bp.route("/api/toolbox/context-menu", methods=["POST"])
def tb_ctx():
    try:
        from core.toolbox import Toolbox
        return jsonify(Toolbox(OS).set_classic_context_menu((request.get_json() or {}).get("enable", True)))
    except Exception as e:
        return jsonify({"error": str(e)})


@toolbox_bp.route("/api/toolbox/power-plan", methods=["POST"])
def tb_power():
    try:
        from core.toolbox import Toolbox
        return jsonify(Toolbox(OS).set_power_plan((request.get_json() or {}).get("plan", "high")))
    except Exception as e:
        return jsonify({"error": str(e)})


@toolbox_bp.route("/api/toolbox/office-telemetry", methods=["POST"])
def tb_office():
    try:
        from core.toolbox import Toolbox
        return jsonify(Toolbox(OS).disable_office_telemetry())
    except Exception as e:
        return jsonify({"error": str(e)})


@toolbox_bp.route("/api/toolbox/hpet", methods=["POST"])
def tb_hpet():
    try:
        from core.toolbox import Toolbox
        return jsonify(Toolbox(OS).disable_hpet())
    except Exception as e:
        return jsonify({"error": str(e)})


@toolbox_bp.route("/api/toolbox/hardware")
def tb_hw():
    try:
        from core.toolbox import Toolbox
        return jsonify(Toolbox(OS).get_hardware_info())
    except Exception as e:
        return jsonify({"error": str(e)})
