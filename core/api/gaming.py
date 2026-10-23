import os
import platform
from flask import Blueprint, jsonify, request

OS = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(platform.system(), "unknown")
gaming_bp = Blueprint("gaming", __name__)
_game_mode_instance = None


def _get_game_mode():
    global _game_mode_instance
    if not _game_mode_instance:
        from core.game_mode import GameMode
        _game_mode_instance = GameMode(OS)
    return _game_mode_instance


@gaming_bp.route("/api/game-mode/status")
def gm_status():
    try:
        return jsonify(_get_game_mode().get_status())
    except Exception as e:
        return jsonify({"error": str(e)})


@gaming_bp.route("/api/game-mode/games")
def gm_games():
    try:
        return jsonify({"games": _get_game_mode().get_game_processes()})
    except Exception as e:
        return jsonify({"games": [], "error": str(e)})


@gaming_bp.route("/api/game-mode/enable", methods=["POST"])
def gm_enable():
    try:
        return jsonify(_get_game_mode().enable_game_mode())
    except Exception as e:
        return jsonify({"error": str(e)})


@gaming_bp.route("/api/game-mode/disable", methods=["POST"])
def gm_disable():
    try:
        return jsonify(_get_game_mode().disable_game_mode())
    except Exception as e:
        return jsonify({"error": str(e)})


@gaming_bp.route("/api/game-mode/affinity", methods=["POST"])
def gm_affinity():
    try:
        from core.game_mode import AffinityOptimizer
        d = request.get_json() or {}
        return jsonify(AffinityOptimizer().optimize_for_gaming(d.get("pid")))
    except Exception as e:
        return jsonify({"error": str(e)})


@gaming_bp.route("/api/game-mode/core-parking", methods=["POST"])
def gm_core_parking():
    try:
        from core.game_mode import AffinityOptimizer
        return jsonify(AffinityOptimizer().disable_core_parking())
    except Exception as e:
        return jsonify({"error": str(e)})


@gaming_bp.route("/api/game-mode/timer-resolution", methods=["POST"])
def gm_timer():
    try:
        from core.game_mode import TimerResolution
        d = request.get_json() or {}
        ms = d.get("resolution_ms", 1.0)
        return jsonify(TimerResolution(OS).set_resolution(ms))
    except Exception as e:
        return jsonify({"error": str(e)})


@gaming_bp.route("/api/game-mode/timer-restore", methods=["POST"])
def gm_timer_restore():
    try:
        from core.game_mode import TimerResolution
        return jsonify(TimerResolution(OS).restore_default())
    except Exception as e:
        return jsonify({"error": str(e)})
