import os
import platform
from flask import Blueprint, jsonify, request

files_bp = Blueprint("files", __name__)
OS = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(platform.system(), "unknown")


@files_bp.route("/api/files/duplicates", methods=["POST"])
def file_dupes():
    try:
        from core.duplicate_finder import DuplicateFinder
        return jsonify({"duplicates": DuplicateFinder(OS).find_duplicates()})
    except Exception as e:
        return jsonify({"error": str(e)})


@files_bp.route("/api/files/large", methods=["POST"])
def file_large():
    try:
        d = request.get_json() or {}
        from core.duplicate_finder import DuplicateFinder
        return jsonify({"large_files": DuplicateFinder(OS).find_large_files(d.get("min_size_mb", 500))})
    except Exception as e:
        return jsonify({"error": str(e)})


@files_bp.route("/api/files/delete", methods=["POST"])
def file_del():
    try:
        d = request.get_json() or {}
        from core.duplicate_finder import DuplicateFinder
        return jsonify(DuplicateFinder(OS).delete_file(d.get("path", "")))
    except Exception as e:
        return jsonify({"error": str(e)})


@files_bp.route("/api/files/shred", methods=["POST"])
def file_shred():
    try:
        d = request.get_json() or {}
        from core.disk_tools import DiskTools
        return jsonify(DiskTools(OS).shred_file(d.get("path", ""), d.get("passes", 3)))
    except Exception as e:
        return jsonify({"error": str(e)})


@files_bp.route("/api/files/shred-folder", methods=["POST"])
def file_shred_folder():
    try:
        d = request.get_json() or {}
        from core.disk_tools import DiskTools
        return jsonify(DiskTools(OS).shred_folder(d.get("path", ""), d.get("passes", 3)))
    except Exception as e:
        return jsonify({"error": str(e)})
