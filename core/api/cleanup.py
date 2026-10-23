import os
import platform
from flask import Blueprint, jsonify

cleanup_bp = Blueprint("cleanup", __name__)
OS = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(platform.system(), "unknown")
