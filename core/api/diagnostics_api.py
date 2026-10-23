from flask import Blueprint, jsonify, request
from ..diagnostics.diagnostics_engine import DiagnosticsEngine
from ..logger import get_logger

diagnostics_bp = Blueprint("diagnostics", __name__)
logger = get_logger("api.diagnostics")


def _get_engine():
    return DiagnosticsEngine()


@diagnostics_bp.route("/api/diagnostics/all", methods=["GET"])
def run_all():
    try:
        engine = _get_engine()
        results = engine.run_all()
        return jsonify({"diagnostics": results, "count": len(results)})
    except Exception as e:
        logger.error(f"Failed to run all diagnostics: {e}")
        return jsonify({"error": str(e)}), 500


@diagnostics_bp.route("/api/diagnostics/event-viewer", methods=["GET"])
def event_viewer():
    try:
        engine = _get_engine()
        return jsonify(engine.analyze_event_viewer())
    except Exception as e:
        logger.error(f"Failed to analyze event viewer: {e}")
        return jsonify({"error": str(e)}), 500


@diagnostics_bp.route("/api/diagnostics/reliability", methods=["GET"])
def reliability():
    try:
        engine = _get_engine()
        return jsonify(engine.analyze_reliability())
    except Exception as e:
        logger.error(f"Failed to analyze reliability: {e}")
        return jsonify({"error": str(e)}), 500


@diagnostics_bp.route("/api/diagnostics/crash-dumps", methods=["GET"])
def crash_dumps():
    try:
        engine = _get_engine()
        return jsonify(engine.analyze_crash_dumps())
    except Exception as e:
        logger.error(f"Failed to analyze crash dumps: {e}")
        return jsonify({"error": str(e)}), 500


@diagnostics_bp.route("/api/diagnostics/bsod", methods=["GET"])
def bsod():
    try:
        engine = _get_engine()
        return jsonify(engine.analyze_bsod())
    except Exception as e:
        logger.error(f"Failed to analyze BSOD: {e}")
        return jsonify({"error": str(e)}), 500


@diagnostics_bp.route("/api/diagnostics/driver-conflicts", methods=["GET"])
def driver_conflicts():
    try:
        engine = _get_engine()
        return jsonify(engine.analyze_driver_conflicts())
    except Exception as e:
        logger.error(f"Failed to analyze driver conflicts: {e}")
        return jsonify({"error": str(e)}), 500


@diagnostics_bp.route("/api/diagnostics/memory-leaks", methods=["GET"])
def memory_leaks():
    try:
        engine = _get_engine()
        return jsonify(engine.analyze_memory_leaks())
    except Exception as e:
        logger.error(f"Failed to analyze memory leaks: {e}")
        return jsonify({"error": str(e)}), 500


@diagnostics_bp.route("/api/diagnostics/startup-delays", methods=["GET"])
def startup_delays():
    try:
        engine = _get_engine()
        return jsonify(engine.analyze_startup_delays())
    except Exception as e:
        logger.error(f"Failed to analyze startup delays: {e}")
        return jsonify({"error": str(e)}), 500


@diagnostics_bp.route("/api/diagnostics/windows-errors", methods=["GET"])
def windows_errors():
    try:
        engine = _get_engine()
        return jsonify(engine.analyze_windows_errors())
    except Exception as e:
        logger.error(f"Failed to analyze windows errors: {e}")
        return jsonify({"error": str(e)}), 500


@diagnostics_bp.route("/api/diagnostics/summary", methods=["GET"])
def summary():
    try:
        engine = _get_engine()
        results = engine.run_all()
        return jsonify(engine.get_summary())
    except Exception as e:
        logger.error(f"Failed to get diagnostics summary: {e}")
        return jsonify({"error": str(e)}), 500
