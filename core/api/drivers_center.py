import os
import platform
from flask import Blueprint, jsonify, request

from core.driver_center import DriverBackupManager, DriverHealthChecker

OS = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(platform.system(), "unknown")
drivers_center_bp = Blueprint("drivers_center", __name__)


def _checker():
    return DriverHealthChecker()


def _backup():
    return DriverBackupManager()


@drivers_center_bp.route("/api/drivers-center/health")
def dc_health():
    try:
        return jsonify({"health": _checker().check_outdated_drivers()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@drivers_center_bp.route("/api/drivers-center/all")
def dc_all():
    try:
        return jsonify({"drivers": _checker().get_all_drivers()})
    except Exception as e:
        return jsonify({"drivers": [], "error": str(e)}), 500


@drivers_center_bp.route("/api/drivers-center/problems")
def dc_problems():
    try:
        # The client reads res.devices, so that is the key we send.
        return jsonify({"devices": _checker().find_problem_devices()})
    except Exception as e:
        return jsonify({"devices": [], "error": str(e)}), 500


@drivers_center_bp.route("/api/drivers-center/signatures")
def dc_signatures():
    try:
        return jsonify({"signatures": _checker().check_driver_signatures()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@drivers_center_bp.route("/api/drivers-center/vulnerable")
def dc_vulnerable():
    try:
        return jsonify({"vulnerable": _checker().scan_for_vulnerable_drivers()})
    except Exception as e:
        return jsonify({"vulnerable": [], "error": str(e)}), 500


@drivers_center_bp.route("/api/drivers-center/backup", methods=["POST"])
def dc_backup():
    try:
        return jsonify(_backup().backup_all_drivers())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@drivers_center_bp.route("/api/drivers-center/backup-driver", methods=["POST"])
def dc_backup_driver():
    try:
        d = request.get_json() or {}
        return jsonify(_backup().backup_driver(d.get("name", "")))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@drivers_center_bp.route("/api/drivers-center/restore", methods=["POST"])
def dc_restore():
    try:
        d = request.get_json() or {}
        return jsonify(_backup().restore_drivers(d.get("backup_id", "")))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@drivers_center_bp.route("/api/drivers-center/backups")
def dc_backups():
    try:
        return jsonify({"backups": _backup().list_backups()})
    except Exception as e:
        return jsonify({"backups": [], "error": str(e)}), 500


@drivers_center_bp.route("/api/drivers-center/details")
def dc_details():
    try:
        name = request.args.get("name", "")
        return jsonify({"details": _backup().get_driver_details(name)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
