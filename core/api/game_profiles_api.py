"""Game Profiles API Blueprint"""
from flask import Blueprint, jsonify, request

game_profiles_bp = Blueprint('game_profiles', __name__)


def _get_engine():
    from ..game_profiles import GameProfiles
    return GameProfiles()


@game_profiles_bp.route('/api/game-profiles', methods=['GET'])
def list_profiles():
    try:
        engine = _get_engine()
        profiles = engine.get_all_profiles()
        return jsonify({"profiles": profiles})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@game_profiles_bp.route('/api/game-profiles/installed', methods=['GET'])
def installed_games():
    """Games verified on this PC, split by profile coverage.

    `matched` contains verified installs only; `unverified` carries records
    whose installation could not be proven (stale/moved paths, name-only
    registry entries) for diagnostics — never as installed games.
    """
    try:
        from ..installed_games import scan_installed_games
        engine = _get_engine()
        scan = scan_installed_games(engine.get_all_profiles())
        return jsonify(scan)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@game_profiles_bp.route('/api/game-profiles/<profile_id>', methods=['GET'])
def get_profile(profile_id):
    try:
        engine = _get_engine()
        profile = engine.get_profile(profile_id)
        if not profile:
            return jsonify({"error": "Profile not found"}), 404
        return jsonify({"profile": profile})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@game_profiles_bp.route('/api/game-profiles/detect', methods=['GET'])
def detect_game():
    try:
        from ..installed_games import STEAM_APPID_FALLBACK
        engine = _get_engine()
        running = engine.detect_running_games()
        if running:
            hit = running[0]
            profile = engine.get_profile(hit["id"])
            appid = STEAM_APPID_FALLBACK.get((profile.get("name", "") if profile else "").strip().lower())
            response = {
                "detected": True,
                "state": "running",
                "verified": True,
                "game_id": hit["id"],
                "game_name": profile.get("name", hit["id"]) if profile else hit["id"],
                "evidence": {"pid": hit.get("pid"), "exe": hit.get("exe")},
            }
            if appid:
                response["appid"] = appid
            return jsonify(response)
        return jsonify({"detected": False})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@game_profiles_bp.route('/api/game-profiles/apply', methods=['POST'])
def apply_profile():
    try:
        data = request.get_json() or {}
        profile_id = data.get("profile_id", "")
        if not profile_id:
            return jsonify({"error": "profile_id required"}), 400
        engine = _get_engine()
        results = engine.apply_profile(profile_id)
        # A refusal is a failed preflight, not a successful apply with a
        # message: the client can then render one honest state.
        if results and all(not r.get("success") for r in results):
            return jsonify({"results": results, "error": results[0].get("message", "Profile blocked")}), 409
        return jsonify({"results": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@game_profiles_bp.route('/api/game-profiles/revert', methods=['POST'])
def revert_profile():
    try:
        engine = _get_engine()
        results = engine.revert_profile()
        return jsonify({"results": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@game_profiles_bp.route('/api/game-profiles/save', methods=['POST'])
def save_profile():
    try:
        data = request.get_json() or {}
        profile_id = data.get("profile_id", "")
        profile = data.get("profile", {})
        if not profile_id or not profile:
            return jsonify({"error": "profile_id and profile required"}), 400
        engine = _get_engine()
        ok = engine.save_custom_profile(profile_id, profile)
        return jsonify({"success": ok})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@game_profiles_bp.route('/api/game-profiles/<profile_id>', methods=['DELETE'])
def delete_profile(profile_id):
    try:
        engine = _get_engine()
        ok = engine.delete_custom_profile(profile_id)
        return jsonify({"success": ok})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
