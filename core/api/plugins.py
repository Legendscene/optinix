import os
import platform
from flask import Blueprint, jsonify, request

from core.plugin_system import PluginDeveloperTools, PluginManager

OS = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(platform.system(), "unknown")
plugins_bp = Blueprint("plugins", __name__)


def _manager():
    return PluginManager()


@plugins_bp.route("/api/plugins/list")
def pl_list():
    try:
        return jsonify({"plugins": _manager().get_all_plugins_info()})
    except Exception as e:
        return jsonify({"plugins": [], "error": str(e)}), 500


@plugins_bp.route("/api/plugins/load", methods=["POST"])
def pl_load():
    try:
        d = request.get_json() or {}
        return jsonify({"loaded": _manager().load_plugin(d.get("name", ""))})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@plugins_bp.route("/api/plugins/unload", methods=["POST"])
def pl_unload():
    try:
        d = request.get_json() or {}
        return jsonify({"unloaded": _manager().unload_plugin(d.get("name", ""))})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@plugins_bp.route("/api/plugins/enable", methods=["POST"])
def pl_enable():
    try:
        d = request.get_json() or {}
        return jsonify({"enabled": _manager().enable_plugin(d.get("name", ""))})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@plugins_bp.route("/api/plugins/disable", methods=["POST"])
def pl_disable():
    try:
        d = request.get_json() or {}
        return jsonify({"disabled": _manager().disable_plugin(d.get("name", ""))})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@plugins_bp.route("/api/plugins/loaded")
def pl_loaded():
    try:
        return jsonify({"loaded": _manager().get_all_plugins_info()})
    except Exception as e:
        return jsonify({"loaded": [], "error": str(e)}), 500


@plugins_bp.route("/api/plugins/create-template", methods=["POST"])
def pl_create_template():
    try:
        d = request.get_json() or {}
        return jsonify(PluginDeveloperTools().create_plugin_template(
            d.get("name", ""), d.get("author", ""), d.get("description", "")))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@plugins_bp.route("/api/plugins/validate", methods=["POST"])
def pl_validate():
    try:
        d = request.get_json() or {}
        return jsonify(PluginDeveloperTools().validate_plugin(d.get("path", "")))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@plugins_bp.route("/api/plugins/check-updates", methods=["GET", "POST"])
def pl_check_updates():
    # Plugins are local folders; there is no remote registry to diff against,
    # so this reports that honestly instead of inventing a version feed.
    try:
        plugins = _manager().get_all_plugins_info()
        return jsonify({
            "updates": 0,
            "checked": len(plugins),
            "source": "local",
            "message": "Plugins are loaded from local folders; no update feed is configured.",
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
