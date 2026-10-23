from flask import Blueprint, jsonify, request
from ..timeline.timeline_store import timeline_store

timeline_bp = Blueprint("timeline", __name__)


@timeline_bp.route("/api/timeline/metrics/<metric>", methods=["GET"])
def get_metric_history(metric: str):
    try:
        hours = request.args.get("hours", 24, type=int)
        result = timeline_store.get_metric_history(metric, hours=hours)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@timeline_bp.route("/api/timeline/events", methods=["GET"])
def get_events():
    try:
        limit = request.args.get("limit", 50, type=int)
        event_type = request.args.get("type")
        result = timeline_store.get_events(limit=limit, event_type=event_type)
        # Wrapped to match the API contract the clients consume ({events: [...]}).
        return jsonify({"events": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@timeline_bp.route("/api/timeline/health-scores", methods=["GET"])
def get_health_scores():
    try:
        days = request.args.get("days", 7, type=int)
        result = timeline_store.get_health_score_history(days=days)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@timeline_bp.route("/api/timeline/summary", methods=["GET"])
def get_summary():
    try:
        result = timeline_store.get_timeline_summary()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@timeline_bp.route("/api/timeline/optimization-impact", methods=["GET"])
def get_optimization_impact():
    try:
        result = timeline_store.get_optimization_impact()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@timeline_bp.route("/api/timeline/boot-times", methods=["GET"])
def get_boot_times():
    try:
        days = request.args.get("days", 7, type=int)
        result = timeline_store.get_boot_time_history(days=days)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
