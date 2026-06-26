import os
import json
import time
from flask import Flask, send_from_directory, jsonify, request
from core.detector import OSDetector
from core.scanner import SystemScanner
from core.optimizers import (
    CleanupOptimizer, NetworkOptimizer, DiskOptimizer,
    PerformanceOptimizer, GamingOptimizer, SecurityOptimizer,
    DeveloperOptimizer, ServicesOptimizer, OverclockOptimizer
)

PORT = 5420
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=None)

detector = OSDetector()
os_type = detector.detect()
scanner = SystemScanner(os_type)

OPTIMIZERS = {
    "cleanup": CleanupOptimizer,
    "network": NetworkOptimizer,
    "disk": DiskOptimizer,
    "performance": PerformanceOptimizer,
    "gaming": GamingOptimizer,
    "security": SecurityOptimizer,
    "developer": DeveloperOptimizer,
    "services": ServicesOptimizer,
    "overclock": OverclockOptimizer
}


@app.route("/")
def index():
    return send_from_directory(os.path.join(BASE_DIR, "ui"), "index.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(os.path.join(BASE_DIR, "ui"), path)


@app.route("/api/system-info")
def system_info():
    try:
        info = scanner.full_scan()
        info["os"] = detector.get_info()
        return jsonify(info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/optimize/<category>", methods=["POST"])
def optimize(category):
    try:
        if category == "all":
            results = {}
            for name, cls in OPTIMIZERS.items():
                optimizer = cls(os_type)
                results[name] = optimizer.run()
            return jsonify(results)

        if category not in OPTIMIZERS:
            return jsonify({"error": f"Unknown: {category}"}), 400

        optimizer = OPTIMIZERS[category](os_type)
        results = optimizer.run()
        return jsonify({"category": category, "results": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/optimize/batch", methods=["POST"])
def optimize_batch():
    try:
        data = request.get_json() or {}
        categories = data.get("categories", list(OPTIMIZERS.keys()))
        results = {}
        for cat in categories:
            if cat in OPTIMIZERS:
                optimizer = OPTIMIZERS[cat](os_type)
                results[cat] = optimizer.run()
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health")
def health():
    return jsonify({"status": "ok", "os": os_type, "version": "1.0.0"})
