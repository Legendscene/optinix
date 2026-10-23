from flask import Blueprint, jsonify, request
from ..tools.system_tools import SystemTools

tools_bp = Blueprint("tools", __name__)
tools = SystemTools()


@tools_bp.route("/api/tools/env", methods=["GET"])
def list_env():
    try:
        scope = request.args.get("scope", "both")
        result = tools.list_environment_variables(scope=scope)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@tools_bp.route("/api/tools/env/<name>", methods=["GET"])
def get_env(name: str):
    try:
        result = tools.get_environment_variable(name)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@tools_bp.route("/api/tools/env", methods=["POST"])
def set_env():
    try:
        data = request.get_json() or {}
        name = data.get("name")
        value = data.get("value")
        scope = data.get("scope", "user")
        result = tools.set_environment_variable(name, value, scope=scope)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@tools_bp.route("/api/tools/env/<name>", methods=["DELETE"])
def delete_env(name: str):
    try:
        scope = request.args.get("scope", "user")
        result = tools.delete_environment_variable(name, scope=scope)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@tools_bp.route("/api/tools/hosts", methods=["GET"])
def get_hosts():
    try:
        result = tools.get_hosts_file()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@tools_bp.route("/api/tools/hosts", methods=["POST"])
def add_hosts_entry():
    try:
        data = request.get_json() or {}
        ip = data.get("ip")
        hostname = data.get("hostname")
        comment = data.get("comment", "")
        result = tools.add_hosts_entry(ip, hostname, comment=comment)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@tools_bp.route("/api/tools/hosts/<int:line_number>", methods=["DELETE"])
def remove_hosts_entry(line_number: int):
    try:
        result = tools.remove_hosts_entry(line_number)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@tools_bp.route("/api/tools/hosts/<int:line_number>/toggle", methods=["PUT"])
def toggle_hosts_entry(line_number: int):
    try:
        result = tools.toggle_hosts_entry(line_number)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@tools_bp.route("/api/tools/launch/<tool_name>", methods=["POST"])
def launch_tool(tool_name: str):
    try:
        result = tools.launch_tool(tool_name)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@tools_bp.route("/api/tools/processes", methods=["GET"])
def list_processes():
    try:
        # get(..., type=int) returns None when the param is absent, which
        # then hits comparisons downstream. Give both real defaults.
        sort_by = request.args.get("sort_by", "memory")
        limit = request.args.get("limit", 50, type=int) or 50
        result = tools.list_processes(sort_by=sort_by, limit=limit)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@tools_bp.route("/api/tools/processes/<int:pid>", methods=["GET"])
def get_process(pid: int):
    try:
        result = tools.get_process_details(pid)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@tools_bp.route("/api/tools/processes/<int:pid>", methods=["DELETE"])
def kill_process(pid: int):
    try:
        result = tools.kill_process(pid)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@tools_bp.route("/api/tools/windows-features", methods=["GET"])
def list_windows_features():
    try:
        result = tools.list_windows_features()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@tools_bp.route("/api/tools/windows-features/<name>/enable", methods=["POST"])
def enable_windows_feature(name: str):
    try:
        result = tools.enable_windows_feature(name)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@tools_bp.route("/api/tools/windows-features/<name>/disable", methods=["POST"])
def disable_windows_feature(name: str):
    try:
        result = tools.disable_windows_feature(name)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@tools_bp.route("/api/tools/network/flush-dns", methods=["POST"])
def flush_dns():
    try:
        result = tools.flush_dns()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@tools_bp.route("/api/tools/network/reset-winsock", methods=["POST"])
def reset_winsock():
    try:
        result = tools.reset_winsock()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
