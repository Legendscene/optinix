from flask import Blueprint, jsonify, request
from ..monitor.monitor_engine import monitor_engine
from ..monitor.metrics_store import metrics_store
from ..logger import get_logger

monitor_bp = Blueprint("monitor", __name__)
logger = get_logger("api.monitor")


@monitor_bp.route("/api/monitor/current", methods=["GET"])
def get_current():
    try:
        data = monitor_engine.collect_once()
        latest = metrics_store.get_all_current()
        return jsonify({"snapshot": data, "latest_tracking": latest})
    except Exception as e:
        logger.error(f"Failed to get current metrics: {e}")
        return jsonify({"error": str(e)}), 500


@monitor_bp.route("/api/monitor/history/<category>", methods=["GET"])
def get_history(category: str):
    period = request.args.get("period", "1h")
    if period not in ("1h", "24h", "7d"):
        return jsonify({"error": "Invalid period. Use 1h, 24h, or 7d"}), 400
    if category not in metrics_store.METRICS:
        return jsonify({"error": f"Unknown category: {category}. Valid: {metrics_store.METRICS}"}), 400
    try:
        entries = metrics_store.get_history(category, period)
        return jsonify({"category": category, "period": period, "count": len(entries), "entries": entries})
    except Exception as e:
        logger.error(f"Failed to get history for {category}: {e}")
        return jsonify({"error": str(e)}), 500


@monitor_bp.route("/api/monitor/history", methods=["GET"])
def get_all_history():
    period = request.args.get("period", "1h")
    if period not in ("1h", "24h", "7d"):
        return jsonify({"error": "Invalid period. Use 1h, 24h, or 7d"}), 400
    try:
        result = {}
        for cat in metrics_store.METRICS:
            entries = metrics_store.get_history(cat, period)
            if entries:
                result[cat] = entries
        return jsonify({"period": period, "categories": result})
    except Exception as e:
        logger.error(f"Failed to get all history: {e}")
        return jsonify({"error": str(e)}), 500


@monitor_bp.route("/api/monitor/status", methods=["GET"])
def get_status():
    try:
        return jsonify(monitor_engine.get_status())
    except Exception as e:
        logger.error(f"Failed to get monitor status: {e}")
        return jsonify({"error": str(e)}), 500


@monitor_bp.route("/api/monitor/start", methods=["POST"])
def start_monitor():
    try:
        monitor_engine.start()
        return jsonify({"success": True, "message": "Monitor engine started"})
    except Exception as e:
        logger.error(f"Failed to start monitor: {e}")
        return jsonify({"error": str(e)}), 500


@monitor_bp.route("/api/monitor/stop", methods=["POST"])
def stop_monitor():
    try:
        monitor_engine.stop()
        return jsonify({"success": True, "message": "Monitor engine stopped"})
    except Exception as e:
        logger.error(f"Failed to stop monitor: {e}")
        return jsonify({"error": str(e)}), 500


@monitor_bp.route("/api/monitor/stats/<category>", methods=["GET"])
def get_stats(category: str):
    period = request.args.get("period", "1h")
    if period not in ("1h", "24h", "7d"):
        return jsonify({"error": "Invalid period. Use 1h, 24h, or 7d"}), 400
    if category not in metrics_store.METRICS:
        return jsonify({"error": f"Unknown category: {category}. Valid: {metrics_store.METRICS}"}), 400
    try:
        return jsonify(metrics_store.get_stats(category, period))
    except Exception as e:
        logger.error(f"Failed to get stats for {category}: {e}")
        return jsonify({"error": str(e)}), 500
