import os
import platform
from flask import Blueprint, jsonify

software_bp = Blueprint("software", __name__)
OS = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(platform.system(), "unknown")


@software_bp.route("/api/software/check-updates")
def sw_check():
    try:
        from core.software_updater import SoftwareUpdater
        return jsonify(SoftwareUpdater(OS).get_updates_summary())
    except Exception as e:
        return jsonify({"error": str(e)})
