import os
import json
import uuid
import threading
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from ..config import CONFIG
from ..logger import get_logger

maintenance_bp = Blueprint("maintenance", __name__)
logger = get_logger("api.maintenance")

_DATA_DIR = os.path.join(CONFIG.base_dir, "data", "maintenance")
_TASKS_PATH = os.path.join(_DATA_DIR, "tasks.json")
_HISTORY_PATH = os.path.join(_DATA_DIR, "history.json")
_lock = threading.Lock()

_VALID_TYPES = {"daily", "weekly", "monthly"}
_VALID_ACTIONS = {"cleanup", "disk_cleanup", "defrag", "update_check", "registry_clean", "temp_clean", "health_check"}

os.makedirs(_DATA_DIR, exist_ok=True)


def _load_json(path: str) -> list:
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Failed to load {path}: {e}")
        return []


def _save_json(path: str, data: list) -> bool:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        return True
    except OSError as e:
        logger.error(f"Failed to save {path}: {e}")
        return False


def _compute_next_run(task: dict) -> str:
    now = datetime.now()
    schedule = task.get("schedule", "daily")
    last_run = task.get("last_run")
    base = datetime.fromisoformat(last_run) if last_run else now
    if schedule == "monthly":
        next_run = base + timedelta(days=30)
    elif schedule == "weekly":
        next_run = base + timedelta(weeks=1)
    else:
        next_run = base + timedelta(days=1)
    return next_run.isoformat()


@maintenance_bp.route("/api/maintenance/tasks", methods=["GET"])
def list_tasks():
    try:
        with _lock:
            tasks = _load_json(_TASKS_PATH)
        return jsonify({"tasks": tasks, "count": len(tasks)})
    except Exception as e:
        logger.error(f"Failed to list tasks: {e}")
        return jsonify({"error": str(e)}), 500


@maintenance_bp.route("/api/maintenance/tasks", methods=["POST"])
def create_task():
    try:
        data = request.get_json() or {}
        name = data.get("name", "").strip()
        task_type = data.get("type", "").strip()
        schedule = data.get("schedule", "daily").strip()
        actions = data.get("actions", [])
        enabled = data.get("enabled", True)

        if not name:
            return jsonify({"error": "Task name is required"}), 400
        if not actions:
            return jsonify({"error": "At least one action is required"}), 400
        if task_type and task_type not in _VALID_TYPES:
            return jsonify({"error": f"Invalid type: {task_type}. Valid: {', '.join(_VALID_TYPES)}"}), 400
        if schedule not in _VALID_TYPES:
            return jsonify({"error": f"Invalid schedule: {schedule}. Valid: {', '.join(_VALID_TYPES)}"}), 400
        invalid = [a for a in actions if a not in _VALID_ACTIONS]
        if invalid:
            return jsonify({"error": f"Invalid actions: {invalid}. Valid: {', '.join(_VALID_ACTIONS)}"}), 400

        now = datetime.now().isoformat()
        task = {
            "id": str(uuid.uuid4()),
            "name": name,
            "type": task_type or schedule,
            "schedule": schedule,
            "actions": actions,
            "enabled": enabled,
            "last_run": None,
            "next_run": _compute_next_run({"schedule": schedule, "last_run": None}),
            "created_at": now,
        }

        with _lock:
            tasks = _load_json(_TASKS_PATH)
            tasks.append(task)
            _save_json(_TASKS_PATH, tasks)

        return jsonify(task), 201
    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        return jsonify({"error": str(e)}), 500


@maintenance_bp.route("/api/maintenance/tasks/<task_id>", methods=["PUT"])
def update_task(task_id: str):
    try:
        data = request.get_json() or {}

        with _lock:
            tasks = _load_json(_TASKS_PATH)
            task = next((t for t in tasks if t["id"] == task_id), None)
            if not task:
                return jsonify({"error": "Task not found"}), 404

            if "name" in data:
                task["name"] = data["name"].strip()
            if "type" in data:
                t = data["type"].strip()
                if t and t not in _VALID_TYPES:
                    return jsonify({"error": f"Invalid type: {t}"}), 400
                task["type"] = t
            if "schedule" in data:
                s = data["schedule"].strip()
                if s not in _VALID_TYPES:
                    return jsonify({"error": f"Invalid schedule: {s}"}), 400
                task["schedule"] = s
            if "actions" in data:
                invalid = [a for a in data["actions"] if a not in _VALID_ACTIONS]
                if invalid:
                    return jsonify({"error": f"Invalid actions: {invalid}"}), 400
                task["actions"] = data["actions"]
            if "enabled" in data:
                task["enabled"] = bool(data["enabled"])

            task["next_run"] = _compute_next_run(task)
            _save_json(_TASKS_PATH, tasks)

        return jsonify(task)
    except Exception as e:
        logger.error(f"Failed to update task {task_id}: {e}")
        return jsonify({"error": str(e)}), 500


@maintenance_bp.route("/api/maintenance/tasks/<task_id>", methods=["DELETE"])
def delete_task(task_id: str):
    try:
        with _lock:
            tasks = _load_json(_TASKS_PATH)
            task = next((t for t in tasks if t["id"] == task_id), None)
            if not task:
                return jsonify({"error": "Task not found"}), 404
            tasks.remove(task)
            _save_json(_TASKS_PATH, tasks)
        return jsonify({"success": True, "message": f"Task {task_id} deleted"})
    except Exception as e:
        logger.error(f"Failed to delete task {task_id}: {e}")
        return jsonify({"error": str(e)}), 500


@maintenance_bp.route("/api/maintenance/tasks/<task_id>/run", methods=["POST"])
def run_task(task_id: str):
    try:
        with _lock:
            tasks = _load_json(_TASKS_PATH)
            task = next((t for t in tasks if t["id"] == task_id), None)
            if not task:
                return jsonify({"error": "Task not found"}), 404

            now = datetime.now().isoformat()
            task["last_run"] = now
            task["next_run"] = _compute_next_run(task)
            _save_json(_TASKS_PATH, tasks)

            history = _load_json(_HISTORY_PATH)
            entry = {
                "id": str(uuid.uuid4()),
                "task_id": task_id,
                "task_name": task["name"],
                "actions": task["actions"],
                "status": "completed",
                "started_at": now,
                "completed_at": datetime.now().isoformat(),
            }
            history.append(entry)
            _save_json(_HISTORY_PATH, history)

        return jsonify({"success": True, "message": f"Task '{task['name']}' executed", "task": task})
    except Exception as e:
        logger.error(f"Failed to run task {task_id}: {e}")
        return jsonify({"error": str(e)}), 500


@maintenance_bp.route("/api/maintenance/status", methods=["GET"])
def get_status():
    try:
        with _lock:
            tasks = _load_json(_TASKS_PATH)
        total = len(tasks)
        enabled = sum(1 for t in tasks if t.get("enabled"))
        pending = sum(1 for t in tasks if t.get("enabled") and t.get("next_run") and t["next_run"] <= datetime.now().isoformat())
        return jsonify({
            "total_tasks": total,
            "enabled_tasks": enabled,
            "pending_tasks": pending,
            "status": "running" if enabled > 0 else "idle",
        })
    except Exception as e:
        logger.error(f"Failed to get maintenance status: {e}")
        return jsonify({"error": str(e)}), 500


@maintenance_bp.route("/api/maintenance/run", methods=["POST"])
def run_all_pending():
    try:
        with _lock:
            tasks = _load_json(_TASKS_PATH)
            now = datetime.now().isoformat()
            pending = [t for t in tasks if t.get("enabled") and t.get("next_run") and t["next_run"] <= now]

            executed = []
            for task in pending:
                task["last_run"] = now
                task["next_run"] = _compute_next_run(task)
                executed.append(task["id"])

            _save_json(_TASKS_PATH, tasks)

            history = _load_json(_HISTORY_PATH)
            for task in pending:
                entry = {
                    "id": str(uuid.uuid4()),
                    "task_id": task["id"],
                    "task_name": task["name"],
                    "actions": task["actions"],
                    "status": "completed",
                    "started_at": now,
                    "completed_at": datetime.now().isoformat(),
                }
                history.append(entry)
            _save_json(_HISTORY_PATH, history)

        return jsonify({"success": True, "executed_count": len(pending), "task_ids": executed})
    except Exception as e:
        logger.error(f"Failed to run pending tasks: {e}")
        return jsonify({"error": str(e)}), 500


@maintenance_bp.route("/api/maintenance/history", methods=["GET"])
def get_history():
    try:
        limit = request.args.get("limit", 50, type=int)
        with _lock:
            history = _load_json(_HISTORY_PATH)
        history.sort(key=lambda h: h.get("started_at", ""), reverse=True)
        return jsonify({"history": history[:limit], "count": min(len(history), limit), "total": len(history)})
    except Exception as e:
        logger.error(f"Failed to get maintenance history: {e}")
        return jsonify({"error": str(e)}), 500
