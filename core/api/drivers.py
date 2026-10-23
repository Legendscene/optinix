import os
import platform
from flask import Blueprint, jsonify, request

OS = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(platform.system(), "unknown")
drivers_bp = Blueprint("drivers", __name__)


@drivers_bp.route("/api/drivers/scan")
def drv_scan():
    try:
        from core.drivers import DriverManager
        return jsonify({"drivers": DriverManager(OS).scan_drivers()[:30]})
    except Exception as e:
        return jsonify({"drivers": [], "error": str(e)})


@drivers_bp.route("/api/drivers/missing")
def drv_miss():
    try:
        from core.drivers import DriverManager
        return jsonify({"missing": DriverManager(OS).get_missing_drivers()})
    except Exception as e:
        return jsonify({"missing": [], "error": str(e)})


@drivers_bp.route("/api/drivers/check-updates")
def drv_check_updates():
    try:
        from core.driver_updater import DriverUpdater
        return jsonify(DriverUpdater(OS).get_scan_summary())
    except Exception as e:
        return jsonify({"error": str(e)})


@drivers_bp.route("/api/drivers/download", methods=["POST"])
def drv_download():
    try:
        d = request.get_json() or {}
        from core.driver_updater import DriverUpdater
        return jsonify(DriverUpdater(OS).download_driver(d.get("name", "")))
    except Exception as e:
        return jsonify({"error": str(e)})


@drivers_bp.route("/api/drivers/install", methods=["POST"])
def drv_install():
    try:
        d = request.get_json() or {}
        from core.driver_updater import DriverUpdater
        return jsonify(DriverUpdater(OS).install_driver(d.get("name", "")))
    except Exception as e:
        return jsonify({"error": str(e)})


@drivers_bp.route("/api/drivers/download-all", methods=["POST"])
def drv_dl_all():
    try:
        from core.driver_updater import DriverUpdater
        return jsonify(DriverUpdater(OS).download_all())
    except Exception as e:
        return jsonify({"error": str(e)})


@drivers_bp.route("/api/drivers/install-all", methods=["POST"])
def drv_inst_all():
    try:
        from core.driver_updater import DriverUpdater
        return jsonify(DriverUpdater(OS).install_all())
    except Exception as e:
        return jsonify({"error": str(e)})
