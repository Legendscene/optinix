import os
import platform
from flask import Blueprint, jsonify, request

speedtest_bp = Blueprint("speedtest", __name__)
OS = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(platform.system(), "unknown")


@speedtest_bp.route("/api/speed-test/ping", methods=["POST"])
def speed_ping():
    try:
        d = request.get_json() or {}
        from core.speed_test import SpeedTest
        return jsonify(SpeedTest().test_ping(d.get("host", "8.8.8.8"), d.get("count", 4)))
    except Exception as e:
        return jsonify({"error": str(e)})


@speedtest_bp.route("/api/speed-test/download", methods=["POST"])
def speed_dl():
    try:
        d = request.get_json() or {}
        from core.speed_test import SpeedTest
        return jsonify(SpeedTest().test_download(d.get("size_mb", 25)))
    except Exception as e:
        return jsonify({"error": str(e)})


@speedtest_bp.route("/api/speed-test/upload", methods=["POST"])
def speed_ul():
    try:
        d = request.get_json() or {}
        from core.speed_test import SpeedTest
        return jsonify(SpeedTest().test_upload(d.get("size_mb", 5)))
    except Exception as e:
        return jsonify({"error": str(e)})


@speedtest_bp.route("/api/speed-test/all", methods=["POST"])
def speed_all():
    try:
        from core.speed_test import SpeedTest
        return jsonify(SpeedTest().test_all())
    except Exception as e:
        return jsonify({"error": str(e)})
