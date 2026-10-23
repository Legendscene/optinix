from flask import Blueprint, jsonify
from ..device_info.device_details import device_info_provider

device_info_bp = Blueprint("device_info", __name__)


@device_info_bp.route("/api/device-info/all", methods=["GET"])
def get_all():
    try:
        result = device_info_provider.get_all()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@device_info_bp.route("/api/device-info/cpu", methods=["GET"])
def get_cpu():
    try:
        result = device_info_provider.get_cpu_info()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@device_info_bp.route("/api/device-info/gpu", methods=["GET"])
def get_gpu():
    try:
        result = device_info_provider.get_gpu_info()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@device_info_bp.route("/api/device-info/motherboard", methods=["GET"])
def get_motherboard():
    try:
        result = device_info_provider.get_motherboard_info()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@device_info_bp.route("/api/device-info/ram", methods=["GET"])
def get_ram():
    try:
        result = device_info_provider.get_ram_info()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@device_info_bp.route("/api/device-info/storage", methods=["GET"])
def get_storage():
    try:
        result = device_info_provider.get_storage_info()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@device_info_bp.route("/api/device-info/battery", methods=["GET"])
def get_battery():
    try:
        result = device_info_provider.get_battery_info()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@device_info_bp.route("/api/device-info/network", methods=["GET"])
def get_network():
    try:
        result = device_info_provider.get_network_info()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@device_info_bp.route("/api/device-info/bios", methods=["GET"])
def get_bios():
    try:
        result = device_info_provider.get_bios_info()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@device_info_bp.route("/api/device-info/drivers", methods=["GET"])
def get_drivers():
    try:
        result = device_info_provider.get_driver_info()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@device_info_bp.route("/api/device-info/summary", methods=["GET"])
def get_summary():
    try:
        result = device_info_provider.get_system_summary()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
