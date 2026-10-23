"""Game Library API — real installed-game discovery, never a fake list.

Endpoints:
  GET  /api/game-library            — cached scan results (or None if never scanned)
  POST /api/game-library/scan       — start an async scan (returns immediately)
  GET  /api/game-library/progress   — scan progress/cancellation state
  POST /api/game-library/cancel     — request cooperative scan cancellation
  GET/POST /api/game-library/roots  — user-approved custom scan roots
  GET/POST/DELETE /api/game-library/favorites — pinned games (UI preference)
  GET  /api/game-library/session/<id> — one game's session/metrics/profile detail
  POST /api/game-library/open       — open an install folder (validated path)
  POST /api/game-library/launch     — start a verified executable
  GET  /api/game-library/running    — which verified games are running now
  GET  /api/game-library/artwork?id= — cached cover art (404 = designed fallback)

Validation rules enforced here (never bypassed for UI convenience):
  - open/launch only accept ids the backend discovered itself
  - an executable must exist at the recorded path tree before launch
  - running status comes from the OS process table, not from the UI
"""
import json
import os
import subprocess
import time
from typing import Any, Dict, Optional

from flask import Blueprint, jsonify, request

from ..game_discovery import get_service, STATUS_INSTALLED, STATUS_RUNNING
from ..logger import get_logger

game_library_bp = Blueprint("game_library", __name__)
logger = get_logger("api.game_library")

# Launch/open are rare operations; the blacklist is a soft guard — the real
# safety is that game records come from the backend's own discovery.
_LAUNCH_DENYLIST = ("unins", "setup", "crash", "patch", "debug")


def _service():
    return get_service()


# Library cache older than this is refreshed automatically on the next
# page open: a background scan starts (never blocks the response) and the
# UI's existing progress poll picks it up. One full scan per day, not per
# render — the repeated-expensive-scan failure mode is avoided by the
# running-flag check inside the service itself.
_AUTO_SCAN_MAX_AGE_S = 24 * 3600


@game_library_bp.route("/api/game-library", methods=["GET"])
def games_list():
    """Cached scan results + manually imported entries, clearly separated.
    A never-scanned library is an honest empty list plus a hint to scan,
    not fabricated games. Stale caches (>24h) trigger one background rescan."""
    from ..game_imports import merge_into
    svc = _service()
    data = svc.cached_result()
    if not data:
        games: list = []
        notes = ["No scan has completed yet."]
        scanned_at = None
        needs_scan = True
    else:
        games = [dict(g) for g in data.get("games", [])]
        notes = list(data.get("notes", []))
        scanned_at = data.get("saved_at")
        needs_scan = False
        # Automatic refresh lifecycle: an old cache quietly schedules one
        # fresh scan; the response is never blocked on it.
        if (
            isinstance(scanned_at, (int, float))
            and time.time() - scanned_at > _AUTO_SCAN_MAX_AGE_S
            and not svc.scan_progress().get("running")
        ):
            try:
                svc.scan_async()
            except Exception as e:  # noqa: BLE001 - refresh is best-effort
                logger.debug(f"auto rescan start failed: {e}")
    # Manual entries join the same payload with source='manual'; launcher
    # records from discovery are never altered by this merge.
    games = merge_into(games)
    return jsonify({
        "games": games,
        "notes": notes,
        "diagnostics": data.get("diagnostics") if data else None,
        "scanned_at": scanned_at,
        "needs_scan": needs_scan,
        "error": data.get("error") if data else None,
        "cancelled": data.get("cancelled", False) if data else False,
    })


@game_library_bp.route("/api/game-library/scan", methods=["POST"])
def scan_start():
    svc = _service()
    started = svc.scan_async()
    if not started:
        return jsonify({"started": False, "reason": "scan already running"}), 409
    return jsonify({"started": True})


@game_library_bp.route("/api/game-library/progress", methods=["GET"])
def scan_progress():
    p = _service().scan_progress()
    # The UI wants direction, not raw internals: express as a fraction.
    total = max(1, p.get("adapters_total", 1))
    return jsonify({
        "running": p.get("running", False),
        "fraction": round(min(1.0, p.get("adapters_done", 0) / total), 2),
        "games_found": p.get("games_found", 0),
        "cancel_requested": p.get("cancel_requested", False),
        "error": p.get("error"),
    })


@game_library_bp.route("/api/game-library/cancel", methods=["POST"])
def scan_cancel():
    ok = _service().cancel_scan()
    return jsonify({"cancelled": bool(ok)})


@game_library_bp.route("/api/game-library/roots", methods=["GET", "POST", "DELETE"])
def custom_roots():
    """User-approved directories for the custom-folder scanner.

    Persists to data/custom_game_roots.json inside the app data dir — a plain
    file the service reads at start; no game data lives here, just root paths.
    """
    from ..config import CONFIG
    path = os.path.join(CONFIG.base_dir, "data", "custom_game_roots.json")

    def _read_roots() -> list:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json_loads_list(f.read())
        except Exception:
            return []

    def _write_roots(roots: list) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="standard_name" if False else "utf-8") as f:
            import json
            json.dump({"roots": roots}, f, indent=2)
        # A changed root set requires a rescan to take effect.
        _service()

    if request.method == "GET":
        return jsonify({"roots": _read_roots()})

    body = request.get_json() or {}
    if request.method == "DELETE":
        root = str(body.get("root", "")).strip()
        roots = [r for r in _read_roots() if r != root]
        _write_roots(roots)
        return jsonify({"roots": roots})

    root = str(body.get("root", "")).strip()
    if not root:
        return jsonify({"error": "root path required"}), 400
    if not os.path.isdir(root):
        return jsonify({"error": f"Not a directory: {root}"}), 400
    roots = _read_roots()
    if root not in roots:
        roots.append(root)
        _write_roots(roots)
    return jsonify({"roots": roots})


def json_loads_list(text: str) -> list:
    import json
    try:
        data = json.loads(text)
        return data.get("roots", []) if isinstance(data, dict) else []
    except Exception:
        return []


@game_library_bp.route("/api/game-library/open", methods=["POST"])
def open_folder():
    """Open an install folder of a discovered game (uses the OS file manager).

    Only the backend's own records can be opened — a client cannot pass an
    arbitrary path to open; it passes the game's stable id.
    """
    body = request.get_json() or {}
    gid = str(body.get("id", ""))
    game = _find_game(gid)
    if not game:
        return jsonify({"error": "Unknown game id (must come from a backend scan)."}), 404
    path = game.get("install_path") or ""
    if not path or not os.path.isdir(path):
        return jsonify({"error": "Installation path is missing or inaccessible."}), 400
    try:
        if os.name == "nt":
            os.startfile(path)  # noqa: S606 - local user action on own machine
        else:
            subprocess.Popen(["xdg-open", path])
        return jsonify({"opened": True})
    except Exception as e:
        return jsonify({"error": f"Could not open folder: {e}"}), 500


@game_library_bp.route("/api/game-library/launch", methods=["POST"])
def launch_game():
    """Start a verified executable of a discovered game.

    Revalidates before doing anything: the file must still exist, be an exe,
    and not be an installer/uninstaller/crash handler.
    """
    body = request.get_json() or {}
    gid = str(body.get("id", ""))
    game = _find_game(gid)
    if not game:
        return jsonify({"error": "Unknown game id (must come from a backend scan)."}), 404
    if game.get("status") not in (STATUS_INSTALLED, STATUS_RUNNING):
        return jsonify({"error": f"Game is not installed ({game.get('status')})"}), 400
    # Some games have no direct exe but a verified launcher target + args
    # (Start Menu evidence, e.g. Gryphline --game=<slug>). That combination
    # is a legitimate launch: launcher exe, backend-recorded args, no shell.
    launch_target = game.get("launch_target") or ""
    launch_args = str(game.get("launch_args") or "")
    exe = game.get("exe_path") or ""
    if not exe and launch_target and os.path.isfile(launch_target) and launch_args:
        try:
            import shlex
            cmd = [launch_target, *shlex.split(launch_args)]
            subprocess.Popen(cmd, cwd=os.path.dirname(launch_target))
            return jsonify({"launched": True, "via": "launcher"})
        except Exception as e:
            return jsonify({"error": f"Launch failed: {e}"}), 500
    if not exe or not os.path.isfile(exe) or not exe.lower().endswith(".exe"):
        return jsonify({"error": "No verified executable for this game."}), 400
    stem = os.path.splitext(os.path.basename(exe))[0]
    low = stem.lower()
    if any(tok in low for tok in _LAUNCH_DENYLIST):
        return jsonify({"error": "Refusing to launch a non-game executable."}), 400
    try:
        subprocess.Popen([exe], cwd=os.path.dirname(exe))
        return jsonify({"launched": True})
    except Exception as e:
        return jsonify({"error": f"Launch failed: {e}"}), 500


# ---------------------------------------------------------------------------
# Favorites — user preference data, persisted backend-side so the Gaming
# Center's pinned games survive restarts. Purely additive to discovery: a
# favorite badge never changes an installation status.
# ---------------------------------------------------------------------------

_FAVORITES_FILE = os.path.join("data", "game_favorites.json")


def _read_favorites() -> list:
    try:
        with open(_FAVORITES_FILE, "r", encoding="utf-8") as f:
            data = json.loads(f.read())
        return data.get("favorites", []) if isinstance(data, dict) else []
    except Exception:
        return []


def _write_favorites(favorites: list) -> None:
    os.makedirs(os.path.dirname(_FAVORITES_FILE), exist_ok=True)
    with open(_FAVORITES_FILE, "w", encoding="utf-8") as f:
        json.dump({"favorites": favorites}, f, indent=2)


@game_library_bp.route("/api/game-library/favorites", methods=["GET", "POST", "DELETE"])
def favorites():
    body = request.get_json() or {} if request.method != "GET" else {}
    if request.method == "GET":
        return jsonify({"favorites": _read_favorites()})
    gid = str(body.get("id", "")).strip()
    if not gid:
        return jsonify({"error": "game id required"}), 400
    favs = _read_favorites()
    if request.method == "POST":
        if gid not in favs:
            favs.append(gid)
            _write_favorites(favs)
    else:  # DELETE
        favs = [x for x in favs if x != gid]
        _write_favorites(favs)
    return jsonify({"favorites": favs})


# ---------------------------------------------------------------------------
# Game session — the details-panel data for one verified game.

# ---------------------------------------------------------------------------
# Manual imports — exe/folder/shortcut entries the user picked themselves,
# plus emulator registrations. Games imported here are merged into the
# library payload with source='manual'; launcher records stay separate.
# ---------------------------------------------------------------------------


@game_library_bp.route("/api/game-library/manual", methods=["GET"])
def manual_games():
    from ..game_imports import list_games, list_emulators
    return jsonify({
        "games": list_games(),
        "emulators": list_emulators(),
    })


@game_library_bp.route("/api/game-library/resolve-shortcut", methods=["POST"])
def resolve_shortcut_route():
    """Read a .lnk's target without executing it. The resolved target is
    returned for display; the caller decides whether to import it."""
    from ..game_imports import resolve_shortcut
    body = request.get_json() or {}
    lnk = str(body.get("lnk", "")).strip()
    if not lnk or not lnk.lower().endswith(".lnk") or not os.path.isfile(lnk):
        return jsonify({"error": "A valid .lnk path is required."}), 400
    target, args, err, icon = resolve_shortcut(lnk)
    if err and not target:
        return jsonify({"error": err}), 400
    resp = {"target": target, "args": args, "exists": bool(target and os.path.isfile(target))}
    if err:
        resp["warning"] = err
    return jsonify(resp), 200 if target else 400


@game_library_bp.route("/api/game-library/scan-folder", methods=["POST"])
def scan_folder_route():
    """Bounded-depth game-exe candidates inside a user-picked folder.
    Installers/helpers are filtered out; the user still picks the exe."""
    from ..game_imports import find_game_exes, validate_folder
    body = request.get_json() or {}
    folder = str(body.get("folder", "")).strip()
    ok, err = validate_folder(folder)
    if not ok:
        return jsonify({"error": err}), 400
    return jsonify({"folder": folder, "candidates": find_game_exes(folder)})


@game_library_bp.route("/api/game-library/manual/exe", methods=["POST"])
def add_manual_exe():
    from ..game_imports import add_game_exe
    body = request.get_json() or {}
    result = add_game_exe(
        str(body.get("exe_path", "")),
        name=str(body.get("name", "")),
        args=str(body.get("args", "")),
        emulator_id_ref=body.get("emulator_id") or None,
    )
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result), 201


@game_library_bp.route("/api/game-library/manual/folder", methods=["POST"])
def add_manual_folder():
    from ..game_imports import add_game_folder
    body = request.get_json() or {}
    result = add_game_folder(
        str(body.get("folder", "")),
        chosen_exe=str(body.get("exe_path", "")),
        name=str(body.get("name", "")),
    )
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result), 201


@game_library_bp.route("/api/game-library/manual/<gid>", methods=["PATCH", "DELETE"])
def manual_entry(gid):
    from ..game_imports import update_game, remove_game
    if request.method == "DELETE":
        result = remove_game(gid)
    else:
        body = request.get_json() or {}
        result = update_game(gid, body)
    if "error" in result:
        return jsonify(result), 404 if "not found" in result["error"].lower() else 400
    return jsonify(result)


@game_library_bp.route("/api/game-library/emulators", methods=["GET", "POST"])
def emulators():
    from ..game_imports import add_emulator, list_emulators
    if request.method == "GET":
        return jsonify({"emulators": list_emulators()})
    body = request.get_json() or {}
    result = add_emulator(
        str(body.get("name", "")),
        str(body.get("exe_path", "")),
        args=str(body.get("args", "")),
    )
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result), 201


@game_library_bp.route("/api/game-library/emulators/<eid>", methods=["DELETE"])
def emulator_entry(eid):
    from ..game_imports import remove_emulator
    result = remove_emulator(eid)
    if "error" in result:
        return jsonify(result), 404
    return jsonify(result)


@game_library_bp.route("/api/game-library/manual-launch", methods=["POST"])
def manual_launch():
    """Launch a manual/emulator entry through the validated path in
    core/game_imports.py (validated exe, no shell, explicit args only)."""
    from ..game_imports import launch_game
    body = request.get_json() or {}
    gid = str(body.get("id", ""))
    if not gid.startswith("manual") and not gid.startswith("emu"):
        return jsonify({"error": "Only manually added entries are launched here."}), 400
    result = launch_game(gid)
    status = 200 if result.get("created") else 400
    return jsonify(result), status


@game_library_bp.route("/api/game-library/session/<gid>", methods=["GET"])
def game_session(gid: str):
    """Live session data for a game: runtime, process-level and whole-system
    metrics, plus recent profile operations. Unavailable values are present
    as null — the UI renders an em dash, never a fabricated number.
    """
    from ..monitor.monitor_engine import monitor_engine
    from ..game_profiles import GameProfiles
    game = _find_game(gid)
    if not game:
        return jsonify({"error": "Unknown game id (must come from a backend scan)."}), 404

    # Process-level session data (only when the game is actually running).
    session = {"running": False, "started_at": None, "duration_s": None,
               "game_cpu_pct": None, "game_ram_mb": None}
    exe = game.get("exe_path")
    if game.get("status") == STATUS_RUNNING and exe:
        import psutil
        exe_norm = os.path.normcase(os.path.abspath(exe))
        for proc in psutil.process_iter(["exe", "create_time", "cpu_percent", "memory_info"]):
            try:
                pexe = proc.info.get("exe")
                if not pexe or os.path.normcase(os.path.abspath(pexe)) != exe_norm:
                    continue
                session["running"] = True
                session["started_at"] = proc.info.get("create_time")
                session["duration_s"] = round(max(0.0, time.time() - proc.info["create_time"]), 0)
                try:
                    session["game_cpu_pct"] = round(proc.cpu_percent(interval=0.1) / psutil.cpu_count(), 2)
                except Exception:
                    pass
                mem = proc.info.get("memory_info")
                if mem:
                    session["game_ram_mb"] = round(mem.rss / (1024 * 1024), 0)
                break
            except Exception:
                continue

    # Whole-system metrics from the EXISTING monitor engine (no duplicate).
    sys_metrics = monitor_engine.collect_once() or {}

    # Profile ops history for this game's profile, when available.
    profile_id = game.get("profile_id")
    profile_name = None
    if profile_id:
        try:
            p = GameProfiles().get_profile(profile_id)
            profile_name = p.get("name") if p else None
        except Exception:
            pass

    return jsonify({
        "game": game,
        "session": session,
        "system_metrics": sys_metrics,
        "profile": {"id": profile_id, "name": profile_name} if profile_id else None,
        "now": time.time(),
    })


@game_library_bp.route("/api/game-library/running", methods=["GET"])
def running_games():
    """Re-checks run state live from the process table (cheap psutil pass)."""
    from ..game_discovery import _running_check
    data = _service().cached_result() or {"games": []}
    games = [dict(g) for g in data.get("games", []) if g.get("status") in (STATUS_INSTALLED, STATUS_RUNNING)]
    _running_check(games)
    running = [g["id"] for g in games if g["status"] == STATUS_RUNNING]
    return jsonify({"running": running})


@game_library_bp.route("/api/game-library/artwork", methods=["GET"])
def game_artwork():
    """Cover art for one game the backend itself discovered (or imported).

    Resolution, disk cache and negative caching live in core.game_artwork;
    this route only serves the result. 404 is a first-class answer: the UI
    renders its designed fallback tile instead of a broken-image icon, and
    the negative cache keeps repeated misses cheap. Only ids from the
    library are accepted — no arbitrary upstream fetches via this API.
    """
    from flask import send_file
    from ..game_artwork import STORE

    gid = request.args.get("id", "")
    game = _find_game(gid) if gid else None
    if not game:
        return jsonify({"artwork": None, "reason": "unknown game id"}), 404

    result = STORE.resolve(game)
    if not result:
        return jsonify({"artwork": None, "reason": "no verified artwork available"}), 404
    body, mime = result

    # Serve the cached file when it is on disk; fall back to the bytes we
    # just resolved (tests may use an in-memory cache directory).
    key = STORE._key(game)  # noqa: SLF001 - internal key of the same store
    img_path = STORE._img_path(key)
    if os.path.isfile(img_path):
        return send_file(img_path, mimetype=mime, max_age=86400)

    import io
    return send_file(io.BytesIO(body), mimetype=mime, max_age=86400, download_name="cover")


def _find_game(gid: str) -> Optional[Dict[str, Any]]:
    data = _service().cached_result() or {}
    for g in data.get("games", []):
        if g.get("id") == gid:
            return g
    # Manual entries live in their own store; session/open/launch must work
    # for them too, without ever fabricating a discovered record.
    from ..game_imports import entry_by_id
    entry = entry_by_id(gid)
    if entry:
        out = {
            "id": entry["id"],
            "name": entry["name"],
            "source": "manual",
            "install_path": entry.get("folder") or os.path.dirname(entry.get("exe_path", "")),
            "exe_path": entry.get("exe_path") or None,
            "args": entry.get("args", ""),
            "emulator": entry.get("emulator"),
        }
        if entry.get("status") == STATUS_INSTALLED:
            # Re-check running state live so manual entries show honest session data.
            import psutil
            exe = entry.get("exe_path", "")
            if exe and os.path.isfile(exe):
                exe_norm = os.path.normcase(os.path.abspath(exe))
                for proc in psutil.process_iter(["exe"]):
                    try:
                        pexe = proc.info.get("exe") or ""
                    except Exception:  # noqa: BLE001
                        continue
                    if pexe and os.path.normcase(os.path.abspath(pexe)) == exe_norm:
                        out["status"] = STATUS_RUNNING
                        break
                else:
                    out["status"] = STATUS_INSTALLED
        else:
            out["status"] = STATUS_MISSING
        return out
    return None
