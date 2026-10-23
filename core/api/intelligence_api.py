from flask import Blueprint, jsonify, request
from ..intelligence.health_scorer import HealthScorer
from ..logger import get_logger

intelligence_bp = Blueprint("intelligence", __name__)
logger = get_logger("api.intelligence")


@intelligence_bp.route("/api/intelligence/scores", methods=["GET"])
def get_all_scores():
    try:
        scorer = HealthScorer()
        return jsonify(scorer.score_all())
    except Exception as e:
        logger.error(f"Failed to get all scores: {e}")
        return jsonify({"error": str(e)}), 500


@intelligence_bp.route("/api/intelligence/scores/<name>", methods=["GET"])
def get_score(name: str):
    valid_names = {"pc_health", "windows_health", "gaming", "developer", "security", "storage", "battery"}
    if name not in valid_names:
        return jsonify({"error": f"Unknown score: {name}. Valid: {', '.join(sorted(valid_names))}"}), 400
    try:
        scorer = HealthScorer()
        return jsonify(scorer.get_score(name))
    except Exception as e:
        logger.error(f"Failed to get score {name}: {e}")
        return jsonify({"error": str(e)}), 500


@intelligence_bp.route("/api/intelligence/overall", methods=["GET"])
def get_overall_score():
    try:
        scorer = HealthScorer()
        data = scorer.score_all()
        return jsonify({"overall": data.get("overall", 0), "timestamp": data.get("timestamp", "")})
    except Exception as e:
        logger.error(f"Failed to get overall score: {e}")
        return jsonify({"error": str(e)}), 500
