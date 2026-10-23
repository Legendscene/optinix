from flask import Blueprint, jsonify, request
from ..reports.report_generator import report_generator
from ..logger import get_logger

reports_bp = Blueprint("reports", __name__)
logger = get_logger("api.reports")

_VALID_TYPES = {"health", "optimization", "hardware", "driver", "battery", "network", "all"}
_VALID_FORMATS = {"html", "json"}


@reports_bp.route("/api/reports/types", methods=["GET"])
def list_types():
    try:
        return jsonify({
            "types": sorted(_VALID_TYPES - {"all"}),
            "formats": sorted(_VALID_FORMATS),
            "description": "Generate system reports covering health, optimization, hardware, drivers, battery, network, or all",
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@reports_bp.route("/api/reports/generate", methods=["POST"])
def generate_report():
    try:
        data = request.get_json() or {}
        report_type = data.get("type", "").strip()
        fmt = data.get("format", "html").strip()

        if not report_type:
            return jsonify({"error": "Report type is required"}), 400
        if report_type not in _VALID_TYPES:
            return jsonify({"error": f"Invalid type: {report_type}. Valid: {', '.join(sorted(_VALID_TYPES))}"}), 400
        if fmt not in _VALID_FORMATS:
            return jsonify({"error": f"Invalid format: {fmt}. Valid: {', '.join(sorted(_VALID_FORMATS))}"}), 400

        result = report_generator.generate_report(report_type, fmt)
        if "error" in result:
            return jsonify(result), 500
        return jsonify(result), 201
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        return jsonify({"error": str(e)}), 500


@reports_bp.route("/api/reports", methods=["GET"])
def list_reports():
    try:
        report_type = request.args.get("type")
        limit = request.args.get("limit", 20, type=int)
        if report_type and report_type not in _VALID_TYPES:
            return jsonify({"error": f"Invalid type filter: {report_type}. Valid: {', '.join(sorted(_VALID_TYPES))}"}), 400
        reports = report_generator.list_reports(report_type, limit)
        return jsonify({"reports": reports, "count": len(reports)})
    except Exception as e:
        logger.error(f"Failed to list reports: {e}")
        return jsonify({"error": str(e)}), 500


@reports_bp.route("/api/reports/<report_id>", methods=["GET"])
def get_report(report_id: str):
    try:
        report = report_generator.get_report(report_id)
        if report is None:
            return jsonify({"error": "Report not found"}), 404
        return jsonify(report)
    except Exception as e:
        logger.error(f"Failed to get report {report_id}: {e}")
        return jsonify({"error": str(e)}), 500


@reports_bp.route("/api/reports/<report_id>", methods=["DELETE"])
def delete_report(report_id: str):
    try:
        ok = report_generator.delete_report(report_id)
        if not ok:
            return jsonify({"error": "Report not found"}), 404
        return jsonify({"success": True, "message": f"Report {report_id} deleted"})
    except Exception as e:
        logger.error(f"Failed to delete report {report_id}: {e}")
        return jsonify({"error": str(e)}), 500
