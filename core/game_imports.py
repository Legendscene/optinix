"""Manually imported games and emulators — the user-owned side of the library.

Everything here is evidence the user supplied themselves; nothing pretends a
file the user picked came from a launcher. An entry is labeled 'manual' until
its path is re-verified, and a missing file is reported as 'missing', never
silently deleted.

Persistence is a single JSON file (`data/manual_games.json`) holding two
sections:

  emulators: { id, name, exe_path, args, added_at }
  games:     { id, name, exe_path, args, workdir, emulator_id, source,
               added_at, shortcut_path? }

Games may be plain PCs executables, folder imports (with a chosen exe), or
games launched through a registered emulator (emulator_id set). Stable ids
are derived from the normalized install path so re-importing the same exe
updates the existing entry instead of duplicating it.
"""
import json
import os
import re
import shlex
import subprocess
import threading
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from .logger import get_logger

logger = get_logger("game_imports")

STATUS_INSTALLED = "installed"
STATUS_MISSING = "missing"
STATUS_RUNNING = "running"  # only set live by the discovery run-check merge

STORE_FILE = os.path.join("data", "manual_games.json")

# Files that are obviously not game executables inside a picked folder.
_NOT_GAME_EXE = re.compile(
    r"unins|setup|install|redist|directx|vc_?redist|crash|report|updater?|"
    r"patcher|eula|readme|uninstall|helper|crs|editor|debug",
    re.I,
)
_MIN_GAME_EXE_BYTES = 1 * 1024 * 1024

_LOCK = threading.Lock()
_cache: Optional[Dict[str, Any]] = None


def _load() -> Dict[str, Any]:
    global _cache
    with _LOCK:
        if _cache is not None:
            return _cache
        try:
            with open(STORE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                data = {}
        except (OSError, json.JSONDecodeError, ValueError) as e:
            logger.debug(f"manual games store unavailable: {e}")
            data = {}
        data.setdefault("emulators", [])
        data.setdefault("games", [])
        _cache = data
        return _cache


def _save(data: Dict[str, Any]) -> bool:
    try:
        os.makedirs(os.path.dirname(STORE_FILE), exist_ok=True)
        tmp = STORE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=1)
        os.replace(tmp, STORE_FILE)
        return True
    except OSError as e:
        logger.error(f"manual games store write failed: {e}")
        return False


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def norm_path(path: str) -> str:
    """Case- and separator-stable id material for an executable path."""
    return os.path.normcase(os.path.normpath(path or "").strip())


def exe_id(exe_path: str) -> str:
    return f"manual:{uuid.uuid5(uuid.NAMESPACE_URL, norm_path(exe_path)).hex[:12]}"


def emulator_id(exe_path: str) -> str:
    return f"emu:{uuid.uuid5(uuid.NAMESPACE_URL, norm_path(exe_path)).hex[:12]}"


def folder_id(path: str) -> str:
    return f"manualfolder:{uuid.uuid5(uuid.NAMESPACE_URL, norm_path(path)).hex[:12]}"


# ---------------------------------------------------------------------------
# Validation helpers (each returns (ok, error))
# ---------------------------------------------------------------------------


def validate_exe(exe_path: str) -> Tuple[bool, str]:
    p = _norm(exe_path)
    if not p:
        return False, "Path is empty."
    if not os.path.isabs(p):
        return False, "Path must be absolute."
    if os.path.splitext(p)[1].lower() != ".exe":
        return False, "Not an .exe file."
    if not os.path.isfile(p):
        return False, "File does not exist."
    return True, ""


def validate_folder(folder: str) -> Tuple[bool, str]:
    p = _norm(folder)
    if not p:
        return False, "Path is empty."
    if not os.path.isabs(p):
        return False, "Path must be absolute."
    if not os.path.isdir(p):
        return False, "Folder does not exist."
    return True, ""


# ---------------------------------------------------------------------------
# Shortcut parsing (pythoncom only; guarded so imports stay testable)
# ---------------------------------------------------------------------------


def resolve_shortcut(lnk_path: str) -> Tuple[Optional[str], str, str, Optional[str]]:
    """Resolve a .lnk to (target_path, arguments, error, icon_path).

    Never executes anything — reading the shortcut structure is safe. Returns
    a friendly error when the target is missing/deleted so the UI can show it.
    """
    try:
        import pythoncom  # type: ignore
        from win32com.client import Dispatch  # type: ignore
    except ImportError:
        return None, "", "Shortcut resolution needs pywin32 (pythoncom).", None
    try:
        pythoncom.CoInitialize()
        shell = Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(lnk_path)
        target = str(shortcut.Targetpath or "").strip()
        args = str(shortcut.Arguments or "")
        icon = str(shortcut.IconLocation or "").split(",")[0].strip() or None
        pythoncom.CoUninitialize()
    except Exception as e:  # noqa: BLE001 - COM surfaces many exception types
        return None, "", f"Shortcut could not be read: {e}", None
    if not target:
        return None, "", "Shortcut has no target.", icon
    if not os.path.isfile(target):
        return target, args, f"Shortcut target is missing on disk: {target}", icon
    return target, args, "", icon


# ---------------------------------------------------------------------------
# Folder import: find plausible game executables inside a picked folder
# ---------------------------------------------------------------------------


def find_game_exes(folder: str, max_depth: int = 2) -> List[Dict[str, Any]]:
    """Bounded-depth scan for game-looking exes in a user-picked folder.

    Installers/updaters/crash handlers are rejected by name and size. Returns
    a candidate list; the user must pick which one is the game.
    """
    ok, err = validate_folder(folder)
    if not ok:
        return []
    out: List[Dict[str, Any]] = []
    seen: set = set()

    def _walk(path: str, depth: int) -> None:
        try:
            entries = os.listdir(path)
        except OSError:
            return
        for e in sorted(entries):
            full = os.path.join(path, e)
            if os.path.isdir(full):
                if depth < max_depth:
                    _walk(full, depth + 1)
                continue
            if os.path.splitext(e)[1].lower() != ".exe":
                continue
            if _NOT_GAME_EXE.search(e):
                continue
            try:
                size = os.path.getsize(full)
            except OSError:
                continue
            if size < _MIN_GAME_EXE_BYTES:
                continue
            key = norm_path(full)
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "path": full,
                "name": os.path.splitext(e)[0],
                "size_mb": round(size / (1024 * 1024), 1),
            })

    _walk(folder, 0)
    # Most plausible first: name hints, then larger binaries.
    def _score(c: Dict[str, Any]) -> Tuple[int, int]:
        stem = (_norm(os.path.splitext(os.path.basename(c["path"]))[0])).lower()
        hint = 1 if any(w in stem for w in ("game", "client", "bin", "shipping")) else 0
        return (-hint, -int(c["size_mb"] * 1000))

    out.sort(key=_score)
    return out[:25]


# ---------------------------------------------------------------------------
# Persistence: emulators
# ---------------------------------------------------------------------------


def add_emulator(name: str, exe_path: str, args: str = "") -> Dict[str, Any]:
    name_n = _norm(name) or os.path.splitext(os.path.basename(exe_path))[0]
    ok, err = validate_exe(exe_path)
    if not ok:
        return {"error": err}
    eid = emulator_id(exe_path)
    data = _load()
    with _LOCK:
        existing = next((e for e in data["emulators"] if e["id"] == eid), None)
        if existing:
            existing.update({"name": name_n, "args": args, "added_at": existing["added_at"]})
            entry = existing
        else:
            entry = {
                "id": eid,
                "name": name_n,
                "exe_path": os.path.normpath(exe_path),
                "args": args,
                "added_at": time.time(),
            }
            data["emulators"].append(entry)
        saved = _save(data)
    if not saved:
        return {"error": "Could not persist the emulator entry."}
    return {"emulator": dict(entry)}


def list_emulators() -> List[Dict[str, Any]]:
    data = _load()
    return [dict(e) for e in data["emulators"]]


def remove_emulator(em_id: str) -> Dict[str, Any]:
    data = _load()
    with _LOCK:
        before = len(data["emulators"])
        data["emulators"] = [e for e in data["emulators"] if e["id"] != em_id]
        removed = before != len(data["emulators"])
        # Associations must not dangle: games pointing at a removed emulator
        # keep their launch exe but lose the emulator tag, and are NOT deleted.
        for g in data["games"]:
            if g.get("emulator_id") == em_id:
                g.pop("emulator_id", None)
        saved = _save(data)
    if not removed:
        return {"error": "Emulator not found."}
    if not saved:
        return {"error": "Could not persist the removal."}
    return {"removed": em_id}


def get_emulator(em_id: str) -> Optional[Dict[str, Any]]:
    return next((e for e in _load()["emulators"] if e["id"] == em_id), None)


# ---------------------------------------------------------------------------
# Persistence: games (manual entries)
# ---------------------------------------------------------------------------


def _dedupe_index(data: Dict[str, Any], exe_path: str) -> Optional[Dict[str, Any]]:
    key = norm_path(exe_path)
    return next(
        (g for g in data["games"] if norm_path(g.get("exe_path", "")) == key),
        None,
    )


def add_game_exe(
    exe_path: str,
    name: str = "",
    args: str = "",
    emulator_id_ref: Optional[str] = None,
) -> Dict[str, Any]:
    """Register a manually picked executable as a game entry."""
    ok, err = validate_exe(exe_path)
    if not ok:
        return {"error": err}
    display = _norm(name) or os.path.splitext(os.path.basename(exe_path))[0]
    if emulator_id_ref and not get_emulator(emulator_id_ref):
        return {"error": "Unknown emulator id."}
    gid = exe_id(exe_path if not emulator_id_ref else "")
    if emulator_id_ref:
        # Same exe may be associated with one emulator context; the id stays
        # exe-derived so duplicates never appear for one emulator+exe pair.
        gid = f"manual:{uuid.uuid5(uuid.NAMESPACE_URL, norm_path(exe_path) + '|' + emulator_id_ref).hex[:12]}"
    data = _load()
    with _LOCK:
        dup = _dedupe_index(data, exe_path)
        if dup and (dup.get("emulator_id") or "") != (emulator_id_ref or ""):
            # Same exe, different context — allowed (emulator vs native).
            pass
        elif dup:
            dup.update({
                "name": display,
                "args": args,
                "emulator_id": emulator_id_ref if emulator_id_ref else dup.get("emulator_id"),
            })
            entry = dup
            saved = _save(data)
            if not saved:
                return {"error": "Could not persist the game entry."}
            return {"game": dict(entry), "updated": True}
        entry = {
            "id": gid,
            "name": display,
            "exe_path": os.path.normpath(exe_path),
            "args": args,
            "workdir": os.path.dirname(exe_path),
            "emulator_id": emulator_id_ref,
            "source": "manual",
            "added_at": time.time(),
        }
        data["games"].append(entry)
        saved = _save(data)
    if not saved:
        return {"error": "Could not persist the game entry."}
    return {"game": dict(entry), "updated": False}


def add_game_folder(
    folder: str,
    chosen_exe: str = "",
    name: str = "",
) -> Dict[str, Any]:
    """Import a picked game folder; optionally pin the user-chosen exe."""
    ok, err = validate_folder(folder)
    if not ok:
        return {"error": err}
    folder_n = os.path.normpath(folder)
    if chosen_exe:
        ok, err = validate_exe(chosen_exe)
        if not ok:
            return {"error": err}
        chosen_exe = os.path.normpath(chosen_exe)
        if not norm_path(chosen_exe).startswith(norm_path(folder_n)):
            return {"error": "Chosen executable is not inside the picked folder."}
    display = _norm(name) or os.path.basename(folder_n)
    gid = folder_id(folder_n)
    data = _load()
    with _LOCK:
        existing = next(
            (g for g in data["games"] if g.get("id") == gid
             or norm_path(g.get("folder", "")) == norm_path(folder_n)),
            None,
        )
        if existing:
            existing.update({
                "name": display,
                "exe_path": chosen_exe or existing.get("exe_path", ""),
            })
            entry = existing
            saved = _save(data)
            if not saved:
                return {"error": "Could not persist the folder entry."}
            return {"game": dict(entry), "updated": True}
        entry = {
            "id": gid,
            "name": display,
            "folder": folder_n,
            "exe_path": chosen_exe,
            "args": "",
            "workdir": folder_n,
            "source": "manual",
            "added_at": time.time(),
        }
        data["games"].append(entry)
        saved = _save(data)
    if not saved:
        return {"error": "Could not persist the folder entry."}
    return {"game": dict(entry), "updated": False}


def update_game(gid: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    """Edit a manual entry. Only user-visible fields are editable."""
    data = _load()
    with _LOCK:
        entry = next((g for g in data["games"] if g.get("id") == gid), None)
        if not entry:
            return {"error": "Game not found."}
        if "name" in fields:
            name = _norm(str(fields["name"]))
            if not name:
                return {"error": "Name cannot be empty."}
            entry["name"] = name
        if "args" in fields:
            entry["args"] = str(fields["args"] or "")
        if "exe_path" in fields:
            new_exe = _norm(str(fields["exe_path"] or ""))
            if new_exe:
                ok, err = validate_exe(new_exe)
                if not ok:
                    return {"error": err}
                entry["exe_path"] = os.path.normpath(new_exe)
                entry.setdefault("workdir", os.path.dirname(new_exe))
        if "emulator_id" in fields:
            ref = fields["emulator_id"]
            if ref and not get_emulator(ref):
                return {"error": "Unknown emulator id."}
            if ref:
                entry["emulator_id"] = ref
            else:
                entry.pop("emulator_id", None)
        saved = _save(data)
    if not saved:
        return {"error": "Could not persist the edit."}
    return {"game": dict(entry)}


def remove_game(gid: str) -> Dict[str, Any]:
    data = _load()
    with _LOCK:
        before = len(data["games"])
        data["games"] = [g for g in data["games"] if g.get("id") != gid]
        removed = before != len(data["games"])
        saved = _save(data)
    if not removed:
        return {"error": "Game not found."}
    if not saved:
        return {"error": "Could not persist the removal."}
    return {"removed": gid}


def list_games() -> List[Dict[str, Any]]:
    """All manual entries, annotated with live file existence."""
    out: List[Dict[str, Any]] = []
    for g in _load()["games"]:
        entry = dict(g)
        exe = entry.get("exe_path", "")
        entry["status"] = (
            STATUS_INSTALLED if exe and os.path.isfile(exe) else STATUS_MISSING
        )
        emu = entry.get("emulator_id")
        entry["emulator"] = get_emulator(emu) if emu else None
        out.append(entry)
    return out


def entry_by_id(gid: str) -> Optional[Dict[str, Any]]:
    entry = next((g for g in _load()["games"] if g.get("id") == gid), None)
    if not entry:
        return None
    out = dict(entry)
    exe = out.get("exe_path", "")
    out["status"] = STATUS_INSTALLED if (exe and os.path.isfile(exe)) else STATUS_MISSING
    emu = out.get("emulator_id")
    out["emulator"] = get_emulator(emu) if emu else None
    return out


def entry_status(gid: str) -> Optional[str]:
    e = entry_by_id(gid)
    return e.get("status") if e else None


# ---------------------------------------------------------------------------
# Safe launching
# ---------------------------------------------------------------------------


def launch_game(gid: str) -> Dict[str, Any]:
    """Launch a manual entry with validated arguments only.

    subprocess.Popen(list) with shell=False; no string concatenation into a
    shell. Returns created=False with a readable reason on every failure —
    permission, missing file, missing emulator, or OSError from CreateProcess.
    """
    entry = entry_by_id(gid)
    if not entry:
        return {"created": False, "error": "Game not found."}

    emu = entry.get("emulator")
    game_exe = entry.get("exe_path", "")
    extra_args = str(entry.get("args", "") or "")

    if emu:
        emu_exe = emu.get("exe_path", "")
        if not emu_exe or not os.path.isfile(emu_exe):
            return {"created": False, "error": "The configured emulator executable is missing."}
        target_exe = emu_exe
        full_args = " ".join(
            a for a in (emu.get("args"), game_exe, extra_args) if a
        )
        workdir = os.path.dirname(emu_exe)
    else:
        if not game_exe or not os.path.isfile(game_exe):
            return {"created": False,
                    "error": "Executable is missing on disk (game may have been moved or uninstalled)."}
        target_exe = game_exe
        full_args = extra_args
        workdir = entry.get("workdir") or os.path.dirname(game_exe)
    if workdir and not os.path.isdir(workdir):
        workdir = os.path.dirname(target_exe)

    cmd = [target_exe]
    streaming = shlex.split(extra_args) if (not emu and extra_args) else []

    if emu:
        # Emulator args come from the emulator config the user stored; the
        # game exe is passed as a single argument, never via a shell string.
        for a in shlex.split(str(emu.get("args", "") or "")):
            cmd.append(a)
        cmd.append(game_exe)
        for a in streaming:
            cmd.append(a)
    else:
        cmd.extend(streaming)

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=workdir or None,
            shell=False,
            creationflags=getattr(subprocess, "DETACHED_PROCESS", 0),
        )
    except OSError as e:
        logger.warning(f"launch failed for {gid}: {e}")
        return {"created": False, "error": f"Process creation failed: {e}"}
    return {"created": True, "pid": proc.pid}


# ---------------------------------------------------------------------------
# Merge into discovery output (the one place pessimism applies)
# ---------------------------------------------------------------------------


def merge_into(games: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Append manual entries to a discovery result list.

    Launcher-detected records stay separate; the manual records keep
    source='manual' forever. Running state is intentionally NOT added here —
    discovery's process probe owns that.
    """
    for g in list_games():
        games.append({
            "id": g["id"],
            "name": g["name"],
            "source": "manual",
            "install_path": g.get("folder") or os.path.dirname(g.get("exe_path", "")),
            "exe_path": g.get("exe_path") or None,
            "args": g.get("args", ""),
            "emulator_id": g.get("emulator_id"),
            "emulator": g.get("emulator"),
            "status": g.get("status", STATUS_MISSING),
            "label": "manually added",
        })
    return games


def reset_cache_for_tests() -> None:
    global _cache
    with _LOCK:
        _cache = None
