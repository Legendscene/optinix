import os
import platform
from flask import Blueprint, jsonify, request

OS = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(platform.system(), "unknown")
repair_bp = Blueprint("repair", __name__)


@repair_bp.route("/api/repair/sfc", methods=["POST"])
def repair_sfc():
    try:
        from core.system_repair import SystemRepair
        return jsonify(SystemRepair(OS).sfc_scan())
    except Exception as e:
        return jsonify({"error": str(e)})


@repair_bp.route("/api/repair/dism", methods=["POST"])
def repair_dism():
    try:
        from core.system_repair import SystemRepair
        return jsonify(SystemRepair(OS).dism_restore())
    except Exception as e:
        return jsonify({"error": str(e)})


@repair_bp.route("/api/repair/check-disk", methods=["POST"])
def repair_chkdsk():
    try:
        d = request.get_json() or {}
        from core.system_repair import SystemRepair
        return jsonify(SystemRepair(OS).check_disk(d.get("drive", "C:")))
    except Exception as e:
        return jsonify({"error": str(e)})
