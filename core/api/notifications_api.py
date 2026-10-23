from flask import Blueprint, jsonify, request
from ..notifications.notification_manager import notification_manager

notifications_bp = Blueprint("notifications", __name__)


@notifications_bp.route("/api/notifications", methods=["GET"])
def list_notifications():
    try:
        include_dismissed = request.args.get("include_dismissed", "false").lower() == "true"
        limit = request.args.get("limit", 50, type=int)
        notif_type = request.args.get("type")

        # get_all() has no type filter; get_by_type() is the filtered variant.
        if notif_type:
            result = notification_manager.get_by_type(notif_type)
        else:
            result = notification_manager.get_all(
                include_dismissed=include_dismissed,
                limit=limit,
            )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@notifications_bp.route("/api/notifications/unread-count", methods=["GET"])
def unread_count():
    try:
        count = notification_manager.get_unread_count()
        return jsonify({"unread_count": count})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@notifications_bp.route("/api/notifications/<notif_id>/read", methods=["PUT"])
def mark_read(notif_id: str):
    try:
        notification_manager.mark_read(notif_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@notifications_bp.route("/api/notifications/read-all", methods=["PUT"])
def mark_all_read():
    try:
        notification_manager.mark_all_read()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@notifications_bp.route("/api/notifications/<notif_id>/dismiss", methods=["PUT"])
def dismiss_notification(notif_id: str):
    try:
        notification_manager.dismiss(notif_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@notifications_bp.route("/api/notifications/dismiss-all", methods=["PUT"])
def dismiss_all():
    try:
        notification_manager.dismiss_all()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@notifications_bp.route("/api/notifications/<notif_id>", methods=["DELETE"])
def delete_notification(notif_id: str):
    try:
        notification_manager.delete(notif_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@notifications_bp.route("/api/notifications/recent", methods=["GET"])
def recent_notifications():
    try:
        result = notification_manager.get_recent()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
