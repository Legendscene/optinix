import os
import json
import platform
from flask import Blueprint, jsonify, request

rollback_bp = Blueprint("rollback", __name__)
OS = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(platform.system(), "unknown")
_bg_optimizer = None


@rollback_bp.route("/api/rollback/snapshots")
def rollback_snapshots():
    from core.rollback_engine import RollbackEngine
    re = RollbackEngine(OS)
    try:
        files = sorted([f for f in os.listdir(re.log_dir) if f.startswith("snapshot_") and f.endswith(".json")], reverse=True)
        snapshots = []
        for f in files:
            fp = os.path.join(re.log_dir, f)
            try:
                with open(fp) as fh:
                    data = json.load(fh)
                snapshots.append({"file": f, "created": data.get("created", ""), "os": data.get("os", "")})
            except:
                snapshots.append({"file": f, "created": "", "os": ""})
        return jsonify({"snapshots": snapshots[:20]})
    except Exception as e:
        return jsonify({"snapshots": [], "error": str(e)})


@rollback_bp.route("/api/rollback/restore", methods=["POST"])
def rollback_restore():
    from core.rollback_engine import RollbackEngine
    data = request.get_json(silent=True) or {}
    file = data.get("file", "")
    re = RollbackEngine(OS)
    snap_file = os.path.join(re.log_dir, file) if file else re.snapshot_file
    results = re.full_restore(snap_file)
    success = sum(1 for r in results if r.get("success"))
    return jsonify({"success": success == len(results), "results": results, "total": len(results), "ok": success})


@rollback_bp.route("/api/rollback/create-snapshot", methods=["POST"])
def rollback_create():
    from core.rollback_engine import RollbackEngine
    re = RollbackEngine(OS)
    re.snapshot_power_plan()
    fp = re.save_snapshot()
    return jsonify({"success": True, "file": os.path.basename(fp)})


@rollback_bp.route("/api/background/status")
def bg_st():
    global _bg_optimizer
    if not _bg_optimizer:
        from core.background_optimizer import BackgroundOptimizer
        _bg_optimizer = BackgroundOptimizer(OS)
    return jsonify(_bg_optimizer.get_status())


@rollback_bp.route("/api/background/start", methods=["POST"])
def bg_go():
    global _bg_optimizer
    if not _bg_optimizer:
        from core.background_optimizer import BackgroundOptimizer
        _bg_optimizer = BackgroundOptimizer(OS)
    _bg_optimizer.start()
    return jsonify({"success": True})


@rollback_bp.route("/api/background/stop", methods=["POST"])
def bg_no():
    global _bg_optimizer
    if _bg_optimizer:
        _bg_optimizer.stop()
    return jsonify({"success": True})
