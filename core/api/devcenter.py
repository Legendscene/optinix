import os
import platform
from flask import Blueprint, jsonify, request

from core.developer_center import (
    DevCacheCleaner,
    DevEnvironmentChecker,
    DevEnvironmentRepair,
    PackageManager,
)

OS = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(platform.system(), "unknown")
devcenter_bp = Blueprint("devcenter", __name__)


def _checker():
    return DevEnvironmentChecker()


def _packages():
    return PackageManager()


@devcenter_bp.route("/api/devcenter/check")
def dc_check():
    try:
        return jsonify({"environments": _checker().check_all()})
    except Exception as e:
        return jsonify({"environments": {}, "error": str(e)}), 500


@devcenter_bp.route("/api/devcenter/python")
def dc_python():
    try:
        return jsonify({"python": _checker().check_python()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@devcenter_bp.route("/api/devcenter/node")
def dc_node():
    try:
        return jsonify({"node": _checker().check_node()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@devcenter_bp.route("/api/devcenter/git")
def dc_git():
    try:
        return jsonify({"git": _checker().check_git()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@devcenter_bp.route("/api/devcenter/docker")
def dc_docker():
    try:
        return jsonify({"docker": _checker().check_docker()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@devcenter_bp.route("/api/devcenter/install", methods=["POST"])
def dc_install():
    try:
        d = request.get_json() or {}
        return jsonify(_packages().install_package(d.get("manager", ""), d.get("package", "")))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@devcenter_bp.route("/api/devcenter/update", methods=["POST"])
def dc_update():
    try:
        d = request.get_json() or {}
        return jsonify(_packages().update_package(d.get("manager", ""), d.get("package", "")))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@devcenter_bp.route("/api/devcenter/remove", methods=["POST"])
def dc_remove():
    try:
        d = request.get_json() or {}
        return jsonify(_packages().remove_package(d.get("manager", ""), d.get("package", "")))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@devcenter_bp.route("/api/devcenter/search")
def dc_search():
    try:
        # The client calls this without a manager, so default to the manager
        # Windows ships with instead of rejecting the request.
        manager = request.args.get("manager", "winget")
        query = request.args.get("q", "")
        # The client reads res.packages.
        return jsonify({"packages": _packages().search_packages(manager, query)})
    except Exception as e:
        return jsonify({"packages": [], "error": str(e)}), 500


@devcenter_bp.route("/api/devcenter/installed")
def dc_installed():
    try:
        manager = request.args.get("manager", "winget")
        # The client reads res.tools.
        return jsonify({"tools": _packages().list_installed(manager)})
    except Exception as e:
        return jsonify({"tools": [], "error": str(e)}), 500


@devcenter_bp.route("/api/devcenter/update-all", methods=["POST"])
def dc_update_all():
    try:
        return jsonify(_packages().update_all())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@devcenter_bp.route("/api/devcenter/clean-caches", methods=["POST"])
def dc_clean_caches():
    try:
        return jsonify(DevCacheCleaner().execute())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@devcenter_bp.route("/api/devcenter/repair-path", methods=["POST"])
def dc_repair_path():
    try:
        return jsonify(DevEnvironmentRepair().fix_path_issues())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@devcenter_bp.route("/api/devcenter/reset-npm", methods=["POST"])
def dc_reset_npm():
    try:
        return jsonify(DevEnvironmentRepair().reset_npm_cache())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@devcenter_bp.route("/api/devcenter/fix-pip", methods=["POST"])
def dc_fix_pip():
    try:
        return jsonify(DevEnvironmentRepair().fix_pip_issues())
    except Exception as e:
        return jsonify({"error": str(e)}), 500
