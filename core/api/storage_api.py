import time

from flask import Blueprint, jsonify, request
from ..storage_viz.storage_map import storage_map_analyzer

storage_bp = Blueprint("storage", __name__)

# Drive walks are expensive, so identical requests reuse the last result.
_DRIVE_INFO_CACHE = {}
_DRIVE_INFO_TTL = 300


@storage_bp.route("/api/storage/scan", methods=["POST"])
def start_scan():
    try:
        data = request.get_json() or {}
        drive = data.get("drive", "C:\\")
        # start_scan() drives the background scan and has no depth knob; the
        # depth/max_folders limits belong to analyze_drive().
        result = storage_map_analyzer.start_scan(drive=drive)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@storage_bp.route("/api/storage/scan-status", methods=["GET"])
def scan_status():
    try:
        # There is no get_scan_status(); the scan state is is_scanning() plus
        # whatever get_results() has produced so far.
        results = storage_map_analyzer.get_results()
        return jsonify({
            "scanning": storage_map_analyzer.is_scanning,
            "has_results": results is not None,
            "error": None if results is None else results.get("error"),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@storage_bp.route("/api/storage/results", methods=["GET"])
def get_results():
    try:
        result = storage_map_analyzer.get_results()
        return jsonify(result if result is not None else {"status": "no_scan_yet"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@storage_bp.route("/api/storage/cancel-scan", methods=["POST"])
def cancel_scan():
    try:
        result = storage_map_analyzer.cancel_scan()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@storage_bp.route("/api/storage/drive-info", methods=["GET"])
def get_drive_info():
    try:
        # A single drive analysis; StorageMapAnalyzer exposes analyze_drive(),
        # not a drive-info lookup.
        drive = request.args.get("drive", "C:\\")
        depth = request.args.get("max_depth", 2, type=int)
        folders = request.args.get("max_folders", 900, type=int)

        # A full-depth C:\ walk takes minutes and produces megabytes of JSON,
        # which always trips the client timeout, so results are cached briefly
        # and the walk is bounded.
        key = (drive.lower(), depth, folders)
        now = time.time()
        cached = _DRIVE_INFO_CACHE.get(key)
        if cached and now - cached[0] < _DRIVE_INFO_TTL:
            return jsonify(cached[1])

        result = storage_map_analyzer.analyze_drive(
            drive=drive, max_depth=depth, max_folders=folders
        )
        _DRIVE_INFO_CACHE[key] = (now, result)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
