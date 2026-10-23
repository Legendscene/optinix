import os
import platform
from flask import Blueprint, jsonify, request

OS = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(platform.system(), "unknown")
background_bp = Blueprint("background", __name__)


@background_bp.route("/api/external-disk")
def ext_disk():
    try:
        from core.external_disk import ExternalDiskManager
        return jsonify({"disks": ExternalDiskManager(OS).list_external_disks()})
    except Exception as e:
        return jsonify({"disks": [], "error": str(e)})


@background_bp.route("/api/external-disk/optimize", methods=["POST"])
def ext_opt():
    try:
        d = request.get_json() or {}
        from core.external_disk import ExternalDiskManager
        return jsonify(ExternalDiskManager(OS).optimize_disk(d.get("device")))
    except Exception as e:
        return jsonify({"error": str(e)})
