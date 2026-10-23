from flask import Blueprint, jsonify, request
from ..marketplace.marketplace_manager import marketplace_manager

marketplace_bp = Blueprint("marketplace", __name__)


@marketplace_bp.route("/api/marketplace/modules", methods=["GET"])
def list_modules():
    try:
        category = request.args.get("category")
        installed_only = request.args.get("installed_only", "false").lower() == "true"
        result = marketplace_manager.list_modules(category=category, installed_only=installed_only)
        # The client reads res.modules / res.categories, so the payload is
        # enveloped rather than a bare list.
        return jsonify({"modules": result, "count": len(result)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@marketplace_bp.route("/api/marketplace/modules/<module_id>", methods=["GET"])
def get_module(module_id: str):
    try:
        result = marketplace_manager.get_module(module_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@marketplace_bp.route("/api/marketplace/categories", methods=["GET"])
def list_categories():
    try:
        result = marketplace_manager.get_categories()
        return jsonify({"categories": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@marketplace_bp.route("/api/marketplace/modules/<module_id>/install", methods=["POST"])
def install_module(module_id: str):
    try:
        result = marketplace_manager.install_module(module_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@marketplace_bp.route("/api/marketplace/modules/<module_id>/uninstall", methods=["POST"])
def uninstall_module(module_id: str):
    try:
        result = marketplace_manager.uninstall_module(module_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@marketplace_bp.route("/api/marketplace/installed-count", methods=["GET"])
def installed_count():
    try:
        count = marketplace_manager.get_installed_count()
        return jsonify({"installed_count": count})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
