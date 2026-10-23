import os
import platform
from flask import Blueprint, jsonify, request

OS = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(platform.system(), "unknown")
power_bp = Blueprint("power", __name__)


@power_bp.route("/api/power/plans")
def pw_plans():
    try:
        from core.power_center import PowerCenter
        return jsonify({"plans": PowerCenter().list_plans()})
    except Exception as e:
        return jsonify({"plans": [], "error": str(e)})


@power_bp.route("/api/power/active")
def pw_active():
    try:
        from core.power_center import PowerCenter
        return jsonify({"active": PowerCenter().get_active_plan()})
    except Exception as e:
        return jsonify({"error": str(e)})


@power_bp.route("/api/power/set", methods=["POST"])
def pw_set():
    try:
        d = request.get_json() or {}
        from core.power_center import PowerCenter
        return jsonify(PowerCenter().set_active_plan(d.get("guid", "")))
    except Exception as e:
        return jsonify({"error": str(e)})


@power_bp.route("/api/power/battery")
def pw_battery():
    try:
        from core.power_center import PowerCenter
        return jsonify({"battery": PowerCenter().get_battery_info()})
    except Exception as e:
        return jsonify({"error": str(e)})


@power_bp.route("/api/power/settings")
def pw_settings():
    try:
        plan = request.args.get("plan", "")
        from core.power_center import PowerCenter
        return jsonify({"settings": PowerCenter().get_power_settings(plan)})
    except Exception as e:
        return jsonify({"settings": [], "error": str(e)})


@power_bp.route("/api/power/setting", methods=["POST"])
def pw_setting():
    try:
        d = request.get_json() or {}
        from core.power_center import PowerCenter
        return jsonify(PowerCenter().set_power_setting(d.get("sub_guid", ""), d.get("setting_guid", ""), d.get("value", ""), d.get("plan")))
    except Exception as e:
        return jsonify({"error": str(e)})


@power_bp.route("/api/power/create-high-perf", methods=["POST"])
def pw_create_high_perf():
    try:
        from core.power_center import PowerCenter
        return jsonify(PowerCenter().create_high_performance_plan())
    except Exception as e:
        return jsonify({"error": str(e)})


@power_bp.route("/api/power/sleep", methods=["POST"])
def pw_sleep():
    try:
        d = request.get_json() or {}
        from core.power_center import PowerCenter
        return jsonify(PowerCenter().set_sleep_settings(d.get("ac_minutes"), d.get("dc_minutes")))
    except Exception as e:
        return jsonify({"error": str(e)})


@power_bp.route("/api/power/hibernate", methods=["POST"])
def pw_hibernate():
    try:
        d = request.get_json() or {}
        from core.power_center import PowerCenter
        return jsonify(PowerCenter().toggle_hibernate(d.get("enable", False)))
    except Exception as e:
        return jsonify({"error": str(e)})


@power_bp.route("/api/power/processor", methods=["POST"])
def pw_processor():
    try:
        d = request.get_json() or {}
        from core.power_center import PowerCenter
        return jsonify(PowerCenter().set_processor_power(d.get("min_percent"), d.get("max_percent")))
    except Exception as e:
        return jsonify({"error": str(e)})


@power_bp.route("/api/power/usb-suspend", methods=["POST"])
def pw_usb_suspend():
    try:
        d = request.get_json() or {}
        from core.power_center import PowerCenter
        return jsonify(PowerCenter().toggle_usb_suspend(d.get("enable", False)))
    except Exception as e:
        return jsonify({"error": str(e)})


@power_bp.route("/api/power/pcie-link", methods=["POST"])
def pw_pcie_link():
    try:
        d = request.get_json() or {}
        from core.power_center import PowerCenter
        return jsonify(PowerCenter().set_pcie_link_state(d.get("state", "")))
    except Exception as e:
        return jsonify({"error": str(e)})


@power_bp.route("/api/power/reset-plan", methods=["POST"])
def pw_reset_plan():
    try:
        d = request.get_json() or {}
        from core.power_center import PowerCenter
        return jsonify(PowerCenter().reset_plan_to_defaults(d.get("guid", "")))
    except Exception as e:
        return jsonify({"error": str(e)})
