import os
import platform

from flask import Blueprint, jsonify, request

OS = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(platform.system(), "unknown")
registry_bp = Blueprint("registry", __name__)


@registry_bp.route("/api/registry/scan")
def reg_scan():
    try:
        from core.registry_cleaner import RegistryCleaner
        return jsonify(RegistryCleaner(OS).scan_issues())
    except Exception as e:
        return jsonify({"error": str(e)})


@registry_bp.route("/api/registry/fix", methods=["POST"])
def reg_fix():
    try:
        d = request.get_json() or {}
        from core.registry_cleaner import RegistryCleaner
        return jsonify(RegistryCleaner(OS).fix_issues(d.get("paths", [])))
    except Exception as e:
        return jsonify({"error": str(e)})


@registry_bp.route("/api/registry/backup", methods=["POST"])
def reg_backup():
    try:
        from core.registry_cleaner import RegistryCleaner
        return jsonify(RegistryCleaner(OS).backup())
    except Exception as e:
        return jsonify({"error": str(e)})


@registry_bp.route("/api/registry/restore", methods=["POST"])
def reg_restore():
    try:
        d = request.get_json() or {}
        from core.registry_cleaner import RegistryCleaner
        return jsonify(RegistryCleaner(OS).restore(d.get("filename", "")))
    except Exception as e:
        return jsonify({"error": str(e)})


@registry_bp.route("/api/registry/backups")
def reg_backups():
    try:
        from core.registry_cleaner import RegistryCleaner
        return jsonify({"backups": RegistryCleaner(OS).list_backups()})
    except Exception as e:
        return jsonify({"error": str(e)})


@registry_bp.route("/api/context-menu")
def ctx_menu_list():
    try:
        from core.system_repair import ContextMenuManager
        return jsonify({"items": ContextMenuManager().get_items()})
    except Exception as e:
        return jsonify({"error": str(e)})


@registry_bp.route("/api/context-menu/disable", methods=["POST"])
def ctx_menu_disable():
    try:
        d = request.get_json() or {}
        from core.system_repair import ContextMenuManager
        return jsonify(ContextMenuManager().disable_item(d.get("key", "")))
    except Exception as e:
        return jsonify({"error": str(e)})


@registry_bp.route("/api/context-menu/enable", methods=["POST"])
def ctx_menu_enable():
    try:
        d = request.get_json() or {}
        from core.system_repair import ContextMenuManager
        return jsonify(ContextMenuManager().enable_item(d.get("key", "")))
    except Exception as e:
        return jsonify({"error": str(e)})
