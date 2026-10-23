import os
import platform
from flask import Blueprint, jsonify, request

OS = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(platform.system(), "unknown")
automation_bp = Blueprint("automation", __name__)


@automation_bp.route("/api/automation/tasks")
def at_tasks():
    try:
        from core.automation_center import AutomationCenter
        return jsonify({"tasks": AutomationCenter().list_tasks()})
    except Exception as e:
        return jsonify({"tasks": [], "error": str(e)})


@automation_bp.route("/api/automation/tasks", methods=["POST"])
def at_add_task():
    try:
        d = request.get_json() or {}
        from core.automation_center import AutomationCenter
        return jsonify(AutomationCenter().add_task(d.get("name", ""), d.get("action", ""), d.get("interval_hours"), d.get("config")))
    except Exception as e:
        return jsonify({"error": str(e)})


@automation_bp.route("/api/automation/tasks/<task_id>")
def at_task_detail(task_id):
    try:
        from core.automation_center import AutomationCenter
        return jsonify({"task": AutomationCenter().get_task(task_id)})
    except Exception as e:
        return jsonify({"error": str(e)})


@automation_bp.route("/api/automation/tasks/<task_id>", methods=["PUT"])
def at_update_task(task_id):
    try:
        d = request.get_json() or {}
        from core.automation_center import AutomationCenter
        return jsonify(AutomationCenter().update_task(task_id, d))
    except Exception as e:
        return jsonify({"error": str(e)})


@automation_bp.route("/api/automation/tasks/<task_id>", methods=["DELETE"])
def at_remove_task(task_id):
    try:
        from core.automation_center import AutomationCenter
        return jsonify(AutomationCenter().remove_task(task_id))
    except Exception as e:
        return jsonify({"error": str(e)})


@automation_bp.route("/api/automation/tasks/<task_id>/run", methods=["POST"])
def at_run_task(task_id):
    try:
        from core.automation_center import AutomationCenter
        return jsonify(AutomationCenter().run_task_now(task_id))
    except Exception as e:
        return jsonify({"error": str(e)})


@automation_bp.route("/api/automation/tasks/<task_id>/enable", methods=["POST"])
def at_enable_task(task_id):
    try:
        from core.automation_center import AutomationCenter
        return jsonify(AutomationCenter().enable_task(task_id))
    except Exception as e:
        return jsonify({"error": str(e)})


@automation_bp.route("/api/automation/tasks/<task_id>/disable", methods=["POST"])
def at_disable_task(task_id):
    try:
        from core.automation_center import AutomationCenter
        return jsonify(AutomationCenter().disable_task(task_id))
    except Exception as e:
        return jsonify({"error": str(e)})


@automation_bp.route("/api/automation/tasks/<task_id>/history")
def at_task_history(task_id):
    try:
        from core.automation_center import AutomationCenter
        return jsonify({"history": AutomationCenter().get_task_history(task_id)})
    except Exception as e:
        return jsonify({"history": [], "error": str(e)})


@automation_bp.route("/api/automation/scheduler/status")
def at_scheduler_status():
    try:
        from core.automation_center import AutomationCenter
        return jsonify({"status": AutomationCenter().get_scheduler_status()})
    except Exception as e:
        return jsonify({"error": str(e)})


@automation_bp.route("/api/automation/scheduler/start", methods=["POST"])
def at_scheduler_start():
    try:
        from core.automation_center import AutomationCenter
        return jsonify(AutomationCenter().start_scheduler())
    except Exception as e:
        return jsonify({"error": str(e)})


@automation_bp.route("/api/automation/scheduler/stop", methods=["POST"])
def at_scheduler_stop():
    try:
        from core.automation_center import AutomationCenter
        return jsonify(AutomationCenter().stop_scheduler())
    except Exception as e:
        return jsonify({"error": str(e)})


@automation_bp.route("/api/automation/presets")
def at_presets():
    try:
        from core.automation_center import AutomationCenter
        return jsonify({"presets": AutomationCenter().get_presets()})
    except Exception as e:
        return jsonify({"presets": [], "error": str(e)})


@automation_bp.route("/api/automation/presets/apply", methods=["POST"])
def at_apply_preset():
    try:
        d = request.get_json() or {}
        from core.automation_center import AutomationCenter
        return jsonify(AutomationCenter().apply_preset(d.get("preset_name", "")))
    except Exception as e:
        return jsonify({"error": str(e)})
