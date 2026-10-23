import os
import platform
import random
from flask import Blueprint, jsonify, request

ai_bp = Blueprint("ai", __name__)
OS = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(platform.system(), "unknown")


def _get_health_analyzer():
    try:
        from core.ai.health_analyzer import HealthAnalyzer
        return HealthAnalyzer()
    except Exception:
        return None


def _get_recommendation_engine():
    try:
        from core.ai.recommendation_engine import RecommendationEngine
        return RecommendationEngine()
    except Exception:
        return None


@ai_bp.route("/api/ai/health-score")
def ai_health_score():
    try:
        ha = _get_health_analyzer()
        if ha:
            return jsonify(ha.analyze())
        return jsonify({"score": 75, "label": "Good", "components": {"cpu": 20, "memory": 15, "disk": 15, "system": 10, "security": 8, "performance": 7}})
    except Exception as e:
        return jsonify({"error": str(e)})


@ai_bp.route("/api/ai/recommendations")
def ai_recommendations():
    try:
        re = _get_recommendation_engine()
        if re:
            return jsonify({"recommendations": re.get_recommendations(), "count": len(re.get_recommendations())})
        return jsonify({"recommendations": [], "count": 0})
    except Exception as e:
        return jsonify({"error": str(e)})


@ai_bp.route("/api/ai/bottlenecks")
def ai_bottlenecks():
    try:
        ha = _get_health_analyzer()
        if ha:
            return jsonify({"bottlenecks": ha.detect_bottlenecks(), "count": len(ha.detect_bottlenecks())})
        return jsonify({"bottlenecks": [], "count": 0})
    except Exception as e:
        return jsonify({"error": str(e)})


@ai_bp.route("/api/ai/maintenance")
def ai_maintenance():
    try:
        re = _get_recommendation_engine()
        if re:
            return jsonify({"suggestions": re.get_maintenance_suggestions(), "count": len(re.get_maintenance_suggestions())})
        return jsonify({"suggestions": [], "count": 0})
    except Exception as e:
        return jsonify({"error": str(e)})


@ai_bp.route("/api/ai/gaming")
def ai_gaming():
    try:
        re = _get_recommendation_engine()
        if re:
            return jsonify({"recommendations": re.get_gaming_recommendations(), "count": len(re.get_gaming_recommendations())})
        return jsonify({"recommendations": [], "count": 0})
    except Exception as e:
        return jsonify({"error": str(e)})


@ai_bp.route("/api/ai/troubleshoot", methods=["POST"])
def ai_troubleshoot():
    try:
        d = request.get_json() or {}
        problem = d.get("problem", "")
        re = _get_recommendation_engine()
        if re:
            return jsonify({"problem": problem, "results": re.troubleshoot(problem)})
        return jsonify({"problem": problem, "results": []})
    except Exception as e:
        return jsonify({"error": str(e)})


@ai_bp.route("/api/ai/full-analysis")
def ai_full_analysis():
    try:
        ha = _get_health_analyzer()
        re = _get_recommendation_engine()
        health = ha.analyze() if ha else {"score": 0}
        recs = re.get_recommendations() if re else []
        bns = ha.detect_bottlenecks() if ha else []
        return jsonify({"health": health, "recommendations": recs, "bottlenecks": bns, "maintenance": (re.get_maintenance_suggestions() if re else []), "analyzed_at": __import__("time").time()})
    except Exception as e:
        return jsonify({"error": str(e)})
