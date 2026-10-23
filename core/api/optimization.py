import os
import json
import platform
import threading
from flask import Blueprint, jsonify, request

optimization_bp = Blueprint("optimization", __name__)
OS = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(platform.system(), "unknown")

# category key -> (module, class name). Constructors take no arguments.
OPTIMIZERS = {
    "cleanup": ("core.optimizers.cleanup", "CleanupOptimizer"),
    "network": ("core.optimizers.network", "NetworkOptimizer"),
    "network_boost": ("core.optimizers.network_boost", "NetworkBoostOptimizer"),
    "disk": ("core.optimizers.disk", "DiskOptimizer"),
    "performance": ("core.optimizers.performance", "PerformanceOptimizer"),
    "gaming": ("core.optimizers.gaming", "GamingOptimizer"),
    "game_mode": ("core.optimizers.game_mode", "GameModeOptimizer"),
    "security": ("core.optimizers.security", "SecurityOptimizer"),
    "developer": ("core.optimizers.developer", "DeveloperOptimizer"),
    "services": ("core.optimizers.services", "ServicesOptimizer"),
    "overclock": ("core.optimizers.overclock", "OverclockOptimizer"),
    "startup": ("core.optimizers.startup", "StartupOptimizer"),
    "startup_timer": ("core.optimizers.startup_timer", "StartupTimerOptimizer"),
    "gpu": ("core.optimizers.gpu", "GPUOptimizer"),
    "peripheral": ("core.optimizers.peripheral", "PeripheralOptimizer"),
    "affinity": ("core.optimizers.affinity", "AffinityOptimizer"),
    "debloat": ("core.optimizers.debloat", "DebloatOptimizer"),
    "process_optimizer": ("core.optimizers.process_optimizer", "ProcessOptimizer"),
    "speed_test": ("core.optimizers.speed_test", "SpeedTestOptimizer"),
    "bios_recs": ("core.optimizers.bios_recs", "BIOSRecommendationOptimizer"),
    "system_report": ("core.optimizers.system_report", "SystemReportOptimizer"),
}

# Ordered list used by /api/optimize/all
ALL_CATEGORIES = [
    "cleanup", "network", "disk", "performance", "gaming", "security",
    "developer", "services", "startup", "overclock", "gpu", "peripheral",
    "affinity", "debloat",
]


def _run_category(cat):
    """Run one optimizer by key. Returns its full execute() payload."""
    import importlib
    if cat not in OPTIMIZERS:
        return {"error": f"Unknown optimizer '{cat}'", "known": sorted(OPTIMIZERS)}
    module_name, class_name = OPTIMIZERS[cat]
    try:
        mod = importlib.import_module(module_name)
        optimizer = getattr(mod, class_name)()
        result = optimizer.execute()
        result["category"] = cat
        return result
    except Exception as e:
        return {"category": cat, "error": str(e)}


@optimization_bp.route("/api/optimize/<cat>", methods=["POST"])
def optimize(cat):
    if cat == "all":
        _out = {"error": "Optimizer failed"}
        limit = 420 if len(ALL_CATEGORIES) > 1 else 120

        def _work_all():
            nonlocal _out
            results = {}
            for n in ALL_CATEGORIES:
                results[n] = _run_category(n)
            _out = results

        thr = threading.Thread(target=_work_all, daemon=True)
        thr.start()
        thr.join(timeout=limit)
        if thr.is_alive():
            return jsonify({"error": "Optimizer timed out"}), 504
        return jsonify(_out)

    _out = {"error": "Optimizer failed"}

    def _work(c):
        nonlocal _out
        _out = _run_category(c)

    thr = threading.Thread(target=_work, args=(cat,), daemon=True)
    thr.start()
    thr.join(timeout=180)
    if thr.is_alive():
        return jsonify({"error": "Optimizer timed out"}), 504
    if isinstance(_out, dict) and _out.get("error"):
        return jsonify(_out), 500
    return jsonify(_out)


@optimization_bp.route("/api/optimize/gpu", methods=["POST"])
def optimize_gpu():
    try:
        from core.optimizers.gpu import GPUOptimizer
        return jsonify({"results": GPUOptimizer().run()})
    except Exception as e:
        return jsonify({"error": str(e)})


@optimization_bp.route("/api/optimize/peripheral", methods=["POST"])
def optimize_peripheral():
    try:
        from core.optimizers.peripheral import PeripheralOptimizer
        return jsonify({"results": PeripheralOptimizer().run()})
    except Exception as e:
        return jsonify({"error": str(e)})


@optimization_bp.route("/api/optimize/affinity", methods=["POST"])
def optimize_affinity():
    try:
        from core.optimizers.affinity import AffinityOptimizer
        return jsonify({"results": AffinityOptimizer().run()})
    except Exception as e:
        return jsonify({"error": str(e)})


@optimization_bp.route("/api/tuning/extreme", methods=["POST"])
def extreme():
    try:
        from core.ultimate_tweaks import UltimateTweaks
        return jsonify({"results": UltimateTweaks(OS).apply_all_optimizations()})
    except Exception as e:
        return jsonify({"error": str(e)})


@optimization_bp.route("/api/services/debloat", methods=["POST"])
def svc_debloat():
    try:
        d = request.get_json() or {}
        preset = d.get("preset", "basic")
        from core.optimizers.services import ServicesOptimizer
        o = ServicesOptimizer()
        if preset == "basic":
            o.disable_basic_debloat()
        else:
            o.disable_advanced_debloat()
        return jsonify({"results": o.results})
    except Exception as e:
        return jsonify({"error": str(e)})


@optimization_bp.route("/api/extreme", methods=["POST"])
def extreme_tuner():
    try:
        from core.extreme_tuner import ExtremeTuner
        return jsonify({"results": ExtremeTuner(OS).apply_all()})
    except Exception as e:
        return jsonify({"error": str(e)})


@optimization_bp.route("/api/optimize/debloat", methods=["POST"])
def opt_debloat():
    try:
        from core.optimizers.debloat import DebloatOptimizer
        o = DebloatOptimizer()
        return jsonify(o.execute())
    except Exception as e:
        return jsonify({"error": str(e)})


@optimization_bp.route("/api/optimize/game_mode", methods=["POST"])
def opt_game_mode():
    try:
        from core.optimizers.game_mode import GameModeOptimizer
        o = GameModeOptimizer()
        return jsonify(o.execute())
    except Exception as e:
        return jsonify({"error": str(e)})


@optimization_bp.route("/api/optimize/network_boost", methods=["POST"])
def opt_network_boost():
    try:
        from core.optimizers.network_boost import NetworkBoostOptimizer
        o = NetworkBoostOptimizer()
        return jsonify(o.execute())
    except Exception as e:
        return jsonify({"error": str(e)})


@optimization_bp.route("/api/optimize/speed_test", methods=["POST"])
def opt_speed_test():
    try:
        from core.optimizers.speed_test import SpeedTestOptimizer
        o = SpeedTestOptimizer()
        return jsonify(o.execute())
    except Exception as e:
        return jsonify({"error": str(e)})


@optimization_bp.route("/api/optimize/bios_recs", methods=["POST"])
def opt_bios_recs():
    try:
        from core.optimizers.bios_recs import BIOSRecommendationOptimizer
        o = BIOSRecommendationOptimizer()
        return jsonify(o.execute())
    except Exception as e:
        return jsonify({"error": str(e)})


@optimization_bp.route("/api/optimize/system_report", methods=["POST"])
def opt_system_report():
    try:
        from core.optimizers.system_report import SystemReportOptimizer
        o = SystemReportOptimizer()
        return jsonify(o.execute())
    except Exception as e:
        return jsonify({"error": str(e)})


@optimization_bp.route("/api/optimize/startup_timer", methods=["POST"])
def opt_startup_timer():
    try:
        from core.optimizers.startup_timer import StartupTimerOptimizer
        o = StartupTimerOptimizer()
        return jsonify(o.execute())
    except Exception as e:
        return jsonify({"error": str(e)})


@optimization_bp.route("/api/optimize/process_optimizer", methods=["POST"])
def opt_process_optimizer():
    try:
        from core.optimizers.process_optimizer import ProcessOptimizer
        o = ProcessOptimizer()
        return jsonify(o.execute())
    except Exception as e:
        return jsonify({"error": str(e)})


@optimization_bp.route("/api/optimize/list", methods=["GET"])
def list_optimizers():
    return jsonify({
        "optimizers": sorted(OPTIMIZERS),
        "all_categories": ALL_CATEGORIES,
    })
