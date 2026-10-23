import os
import platform
from flask import Blueprint, jsonify, request

OS = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(platform.system(), "unknown")
memory_bp = Blueprint("memory", __name__)


@memory_bp.route("/api/memory/processes")
def mem_procs():
    try:
        from core.memory_manager import MemoryManager
        return jsonify({"processes": MemoryManager(OS).get_processes()})
    except Exception as e:
        return jsonify({"error": str(e)})


@memory_bp.route("/api/memory/free", methods=["POST"])
def mem_free():
    try:
        from core.memory_manager import MemoryManager
        return jsonify(MemoryManager(OS).free_ram())
    except Exception as e:
        return jsonify({"error": str(e)})


@memory_bp.route("/api/memory/auto-optimize", methods=["POST"])
def mem_auto():
    try:
        from core.memory_manager import MemoryManager
        return jsonify(MemoryManager(OS).auto_optimize())
    except Exception as e:
        return jsonify({"error": str(e)})


@memory_bp.route("/api/memory/info")
def mem_info():
    try:
        from core.memory_manager import MemoryManager
        return jsonify(MemoryManager(OS).get_info())
    except Exception as e:
        return jsonify({"error": str(e)})
