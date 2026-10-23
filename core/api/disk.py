import os
import platform
from flask import Blueprint, jsonify, request

disk_bp = Blueprint("disk", __name__)
OS = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(platform.system(), "unknown")


@disk_bp.route("/api/disk/scan", methods=["POST"])
def disk_scan():
    try:
        d = request.get_json() or {}
        from core.disk_analyzer import DiskAnalyzer
        return jsonify(DiskAnalyzer(OS).scan(d.get("drive", "C:")))
    except Exception as e:
        return jsonify({"error": str(e)})


@disk_bp.route("/api/disk/clean-category", methods=["POST"])
def disk_clean_cat():
    try:
        d = request.get_json() or {}
        from core.disk_analyzer import DiskAnalyzer
        return jsonify(DiskAnalyzer(OS).clean_category(d.get("category", ""), d.get("drive", "C:")))
    except Exception as e:
        return jsonify({"error": str(e)})


@disk_bp.route("/api/disk/clean-all", methods=["POST"])
def disk_clean_all():
    try:
        d = request.get_json() or {}
        from core.disk_analyzer import DiskAnalyzer
        return jsonify(DiskAnalyzer(OS).clean_all(d.get("drive", "C:")))
    except Exception as e:
        return jsonify({"error": str(e)})


@disk_bp.route("/api/disk/defrag", methods=["POST"])
def disk_defrag():
    try:
        d = request.get_json() or {}
        from core.disk_tools import DiskTools
        return jsonify(DiskTools(OS).defragment(d.get("drive", "C:")))
    except Exception as e:
        return jsonify({"error": str(e)})


@disk_bp.route("/api/disk/trim", methods=["POST"])
def disk_trim():
    try:
        d = request.get_json() or {}
        from core.disk_tools import DiskTools
        return jsonify(DiskTools(OS).trim(d.get("drive", "C:")))
    except Exception as e:
        return jsonify({"error": str(e)})


@disk_bp.route("/api/disk/drive-info", methods=["POST"])
def disk_drive_info():
    try:
        d = request.get_json() or {}
        from core.disk_tools import DiskTools
        return jsonify(DiskTools(OS).get_drive_info(d.get("drive", "C:")))
    except Exception as e:
        return jsonify({"error": str(e)})
