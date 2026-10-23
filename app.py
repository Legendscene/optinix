import os
import time
import threading
import json
import platform
import subprocess
import psutil
from flask import Flask, send_from_directory, jsonify, abort
from flask_socketio import SocketIO, emit
from werkzeug.exceptions import HTTPException

from core.config import CONFIG
from core.logger import get_logger, cleanup_old_logs
from core.api import register_blueprints
from core.errors import handle_error

# The shipped build has no console of its own, so every tasklist/reg/wmic child
# would flash a black window over the UI. Hide them once, here, before any
# blueprint can shell out.
from core.no_console import install as _install_no_console

_install_no_console()

logger = get_logger("app")
app = Flask(__name__, static_folder=None)
PORT = CONFIG.port

# ---------------------------------------------------------------------------
# Local-only security boundary.
#
# This API mutates Windows system settings, so it must never be reachable
# from another machine, and a web page open in the user's browser must not be
# able to drive it (DNS rebinding / cross-origin requests to localhost).
#
#  - SocketIO allows only the local UI origins instead of "*".
#  - `before_request` rejects mutating methods whose Origin/Referer is present
#    but not local, and rejects any request whose Host is not local. Requests
#    without an Origin (same-origin GETs, curl, tests) are allowed; browsers
#    always attach Origin on cross-site POSTs, which is the vector we close.
# ---------------------------------------------------------------------------
LOCAL_ORIGINS = {
    f"http://127.0.0.1:{PORT}",
    f"http://localhost:{PORT}",
    "http://127.0.0.1:5173",   # vite dev server
    "http://localhost:5173",
}
LOCAL_HOSTS = {"127.0.0.1", "localhost", "[::1]", "::1"}
MUTATING = {"POST", "PUT", "PATCH", "DELETE"}

# async_mode must be explicit: the frozen PyInstaller build cannot run
# python-socketio's auto-detection (no eventlet/gevent bundled, and its
# dynamic probing resolves to nothing), which aborts startup with
# "Invalid async_mode specified". Threading mode is what dev uses anyway.
socketio = SocketIO(app, cors_allowed_origins=sorted(LOCAL_ORIGINS), async_mode="threading")


def _host_of(url):
    """Hostname part of a URL, lowercased; '' when unparsable."""
    try:
        from urllib.parse import urlparse
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


@app.before_request
def _guard_local_only():
    from flask import request
    host = (request.host.split(":")[0] if request.host else "").lower()
    # Host header must be local - blocks DNS rebinding, where the browser
    # resolves an attacker domain to 127.0.0.1 and sends that name in Host.
    if host not in LOCAL_HOSTS:
        logger.warning(f"Blocked non-local host: {request.host}")
        return jsonify({"error": "local access only"}), 403
    origin = request.headers.get("Origin")
    if origin and origin not in LOCAL_ORIGINS:
        logger.warning(f"Blocked cross-origin {request.method} from {origin}")
        return jsonify({"error": "cross-origin requests are not allowed"}), 403
    referer = request.headers.get("Referer")
    if request.method in MUTATING and referer and _host_of(referer) not in LOCAL_HOSTS:
        logger.warning(f"Blocked {request.method} with foreign referer: {referer}")
        return jsonify({"error": "cross-origin requests are not allowed"}), 403
    return None

_socket_gpu_cache = {"load": 0, "memory_used": 0, "memory_total": 0, "temperature": 0}
_socket_gpu_time = 0.0

@app.route("/")
def index():
    return send_from_directory(CONFIG.ui_dir, "index.html")

@app.route("/<path:p>")
def statics(p):
    """Serve a built asset, or fall back to the SPA shell.

    A deep link such as /cpu has no file behind it, and returning 404 for it
    means a refresh or a shared URL lands on a dead page. Anything that is not
    a real file in the bundle and not an API call is handed to index.html so the
    client router can resolve it. Missing assets still 404, otherwise a typo in
    a script URL would silently return HTML and fail in a far more confusing
    way.
    """
    if p.startswith("api/"):
        abort(404)
    full = os.path.join(CONFIG.ui_dir, p)
    if os.path.isfile(full):
        return send_from_directory(CONFIG.ui_dir, p)
    # A missing file under a build directory is a broken reference, not a route.
    if p.startswith("assets/") or os.path.splitext(p)[1]:
        abort(404)
    return send_from_directory(CONFIG.ui_dir, "index.html")

register_blueprints(app)

@socketio.on('connect')
def handle_connect():
    def send_status():
        global _socket_gpu_cache, _socket_gpu_time
        while True:
            try:
                cpu = psutil.cpu_percent(interval=0)
                mem = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                now = time.time()
                if now - _socket_gpu_time > 10:
                    try:
                        import GPUtil
                        gpus = GPUtil.getGPUs()
                        if gpus:
                            g = gpus[0]
                            _socket_gpu_cache = {"load": g.load * 100, "memory_used": g.memoryUsed, "memory_total": g.memoryTotal, "temperature": g.temperature}
                    except:
                        pass
                    _socket_gpu_time = now
                gpu = _socket_gpu_cache
                emit('system_status', {
                    'cpu': cpu,
                    'memory': {'total': mem.total, 'available': mem.available, 'used': mem.used, 'percent': mem.percent},
                    'disk': {'total': disk.total, 'used': disk.used, 'free': disk.free, 'percent': disk.percent},
                    'gpu': gpu,
                    'processes': len(psutil.pids()),
                    'uptime': time.time() - psutil.boot_time(),
                    'timestamp': time.time()
                })
            except:
                emit('system_status', {'error': True})
            time.sleep(3)
    thread = threading.Thread(target=send_status, daemon=True)
    thread.start()

@app.errorhandler(Exception)
def handle_exception(e):
    # A deliberate abort() is a normal 4xx outcome, not a crash. Let Werkzeug
    # render it instead of reporting it as a 500 with a stack trace.
    if isinstance(e, HTTPException):
        return e
    logger.error(f"Unhandled exception: {e}", exc_info=True)
    result = handle_error(e)
    return jsonify(result), result.get("code", 500)

if __name__ == '__main__':
    cleanup_old_logs()
    logger.info(f"Optinix starting on http://127.0.0.1:{CONFIG.port}")
    # Loopback only: never expose the mutation API to the network.
    socketio.run(app, debug=CONFIG.debug, host='127.0.0.1', port=CONFIG.port, allow_unsafe_werkzeug=True)
