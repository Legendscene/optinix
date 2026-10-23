from flask import Blueprint, jsonify, request
from core.optimization_history import OptimizationHistory
from core.benchmark_engine import BenchmarkEngine
from core.logger import get_logger

history_bp = Blueprint("history", __name__)
logger = get_logger("api.history")


@history_bp.route("/api/history", methods=["GET"])
def get_history():
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    category = request.args.get("category")
    try:
        history = OptimizationHistory()
        data = history.get_all(limit=limit, offset=offset, category=category)
        summary = history.get_summary()
        data["summary"] = summary
        return jsonify(data)
    except Exception as e:
        logger.error(f"History fetch failed: {e}")
        return jsonify({"error": str(e)}), 500


@history_bp.route("/api/history/summary", methods=["GET"])
def get_summary():
    try:
        history = OptimizationHistory()
        return jsonify(history.get_summary())
    except Exception as e:
        logger.error(f"Summary fetch failed: {e}")
        return jsonify({"error": str(e)}), 500


@history_bp.route("/api/history/<entry_id>", methods=["GET"])
def get_entry(entry_id: str):
    try:
        history = OptimizationHistory()
        entry = history.get_entry(entry_id)
        if entry is None:
            return jsonify({"error": "Entry not found"}), 404
        return jsonify(entry.__dict__ if hasattr(entry, '__dict__') else entry)
    except Exception as e:
        logger.error(f"Entry fetch failed: {e}")
        return jsonify({"error": str(e)}), 500


@history_bp.route("/api/history", methods=["DELETE"])
def clear_history():
    try:
        history = OptimizationHistory()
        ok = history.clear()
        return jsonify({"success": ok, "message": "History cleared" if ok else "Failed to clear history"})
    except Exception as e:
        logger.error(f"History clear failed: {e}")
        return jsonify({"error": str(e)}), 500


@history_bp.route("/api/history/compare/<optimizer_name>", methods=["GET"])
def compare_optimizer(optimizer_name: str):
    count = request.args.get("count", 2, type=int)
    try:
        history = OptimizationHistory()
        comparison = history.compare_optimizer(optimizer_name, count)
        return jsonify(comparison)
    except Exception as e:
        logger.error(f"Compare failed: {e}")
        return jsonify({"error": str(e)}), 500


@history_bp.route("/api/benchmark", methods=["POST"])
def run_benchmark():
    try:
        engine = BenchmarkEngine()
        results = engine.benchmark_all_with_gpu()
        entry_id = engine.save_history(results)
        return jsonify({
            "entry_id": entry_id,
            "results": {
                category: {
                    "value": r.value if hasattr(r, 'value') else r.get('value', 0),
                    "unit": r.unit if hasattr(r, 'unit') else r.get('unit', ''),
                    "name": r.name if hasattr(r, 'name') else r.get('name', category),
                    "lower_is_better": r.lower_is_better if hasattr(r, 'lower_is_better') else r.get('lower_is_better', True),
                    "metadata": r.metadata if hasattr(r, 'metadata') else r.get('metadata', {}),
                }
                for category, r in results.items()
            }
        })
    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
        return jsonify({"error": str(e)}), 500


@history_bp.route("/api/benchmark/history", methods=["GET"])
def benchmark_history():
    try:
        engine = BenchmarkEngine()
        history = engine.get_history(limit=20)
        return jsonify({"history": history})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@history_bp.route("/api/benchmark/compare-history", methods=["POST"])
def compare_history():
    try:
        data = request.get_json() or {}
        id1 = data.get("entry_id_1", "")
        id2 = data.get("entry_id_2", "")
        if not id1 or not id2:
            return jsonify({"error": "entry_id_1 and entry_id_2 required"}), 400
        engine = BenchmarkEngine()
        comparison = engine.compare_history(id1, id2)
        return jsonify({"comparison": comparison})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@history_bp.route("/api/benchmark/compare", methods=["POST"])
def compare_benchmarks():
    try:
        data = request.get_json() or {}
        before = data.get("before", {})
        after = data.get("after", {})
        engine = BenchmarkEngine()
        comparison = engine.compare(before, after)
        return jsonify(comparison)
    except Exception as e:
        logger.error(f"Benchmark compare failed: {e}")
        return jsonify({"error": str(e)}), 500


@history_bp.route("/api/benchmark/report", methods=["POST"])
def benchmark_report():
    try:
        data = request.get_json() or {}
        before = data.get("before", {})
        after = data.get("after", {})
        engine = BenchmarkEngine()
        comparison = engine.compare(before, after)
        report = engine.format_report(comparison)
        return jsonify({"report": report, "comparison": comparison})
    except Exception as e:
        logger.error(f"Benchmark report failed: {e}")
        return jsonify({"error": str(e)}), 500
