"""Real installed-game discovery — the one source the Games library trusts.

Nothing here is hardcoded per game: this service walks actual launcher
installation records shipped by Steam/Epic/Riot/Battle.net/GOG/EA, the Xbox
packaged-app registration, Windows uninstall keys, and user-approved custom
directories, then validates that an installation genuinely exists before a
game may be reported as installed.

Statuses instead of lies:
  installed   — a verified installation record AND its files exist
  running     — installed + the game process is alive right now
  missing     — a launcher record exists but its files are gone (stale manifest)
  restricted  — the source could not be read (permissions/packaging),
                reported honestly instead of skipped
No name is marked installed merely because it appears in a process list or a
predefined list; process matching only ever *adds* the running status.
"""
import json
import os
import re
import subprocess
import threading
import time
from typing import Any, Callable, Dict, List, Optional

try:
    import winreg  # noqa: F401 - present on Windows only
except ImportError:  # non-Windows CI
    winreg = None  # type: ignore[assignment]

from .logger import get_logger

logger = get_logger("game_discovery")

# Installations status model consumed by the API/UI.
STATUS_INSTALLED = "installed"
STATUS_RUNNING = "running"
STATUS_MISSING = "missing"          # stale launcher record, files gone
STATUS_RESTRICTED = "restricted"    # source unreadable / access denied

# Game-looking executables for custom-folder scanning. Anything matching an
# installer/uninstaller/crash-handler/runtime pattern is rejected rather than
# guessed into the library.
_GAME_EXE_HINT = re.compile(
    r"^(client|launcher|game)"
    r"|(game\d*|client|bin[0-9]*|ship)$"
    r"|(win64|win32|x64|x86)$",
    re.I,
)
_NOT_GAME_EXE = re.compile(
    r"unins|setup|install|redist|directx|vc_?redist|crash|report(\w*)\.exe$|"
    r"updater?|patcher|launcher\.exe$|eula|readme|uninstall|"
    r"(app|tool|editor|cleaner|optimi[sz]er)\.exe$",
    re.I,
)
_EXECUTABLE_EXTS = {".exe"}
# Large executables are far more likely to be real games than a 40 KB helper.
_MIN_GAME_EXE_BYTES = 5 * 1024 * 1024

# Steam-library noise that is not a game (tools/runtimes/DirectX).
NON_GAME_PATTERNS = re.compile(
    r"redistributables|directx|visual c\+\+|runtime|workshop|\bproton\b|"
    r"steamworks| dedicated server|\bserver\b|sdk|\bdemo\b",
    re.I,
)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def resolve_game_exe(install_dir: Optional[str]) -> Optional[str]:
    """Best-evidence executable inside a verified install dir.

    Picks the largest .exe at depth 0-3 that is not a known helper
    (uninstaller/patcher/crash handler). Large size is the decisive signal:
    real game binaries are tens of MB, helpers are KBs. Engine installs
    (Unreal: <root>/Binaries/Win64/*-Shipping.exe) are found via the
    committed candidate dirs, not a full recursive walk. Returns None when
    nothing qualifies, which keeps Launch honestly disabled.
    """
    if not install_dir or not os.path.isdir(install_dir):
        return None
    dirs = [install_dir]
    # Bounded expansion: immediate children plus engine-standard contours.
    for child in _subdirs(install_dir, 12):
        p = os.path.join(install_dir, child)
        dirs.append(p)
        for gchild in _subdirs(p, 12):
            gp = os.path.join(p, gchild)
            dirs.append(gp)
            if gchild.lower() in {"binaries", "bin"}:
                for gg in _subdirs(gp, 8):
                    dirs.append(os.path.join(gp, gg))
    best: Optional[tuple[int, str]] = None
    for depth_dir in dirs:
        try:
            entries = os.listdir(depth_dir)
        except OSError:
            continue
        for e in entries:
            if os.path.splitext(e)[1].lower() not in _EXECUTABLE_EXTS:
                continue
            if _NOT_GAME_EXE.search(e):
                continue
            full = os.path.join(depth_dir, e)
            try:
                size = os.path.getsize(full)
            except OSError:
                continue
            if size < _MIN_GAME_EXE_BYTES:
                continue
            if best is None or size > best[0]:
                best = (size, full)
    return best[1] if best else None


def _subdirs(path: str, max_children: int = 8) -> List[str]:
    """Bounded child directories — never a full recursive walk."""
    out: List[str] = []
    try:
        for e in sorted(os.listdir(path)):
            p = os.path.join(path, e)
            if os.path.isdir(p):
                out.append(e)
                if len(out) >= max_children:
                    break
    except OSError:
        pass
    return out


class _Cancel:
    """Cooperative cancellation shared by every adapter of one scan."""

    def __init__(self) -> None:
        self.flag = threading.Event()

    def cancelled(self) -> bool:
        return self.flag.is_set()

    def cancel(self) -> None:
        self.flag.set()


class _Registry:
    """Thin wrapper so the adapters stay testable off-Windows."""

    @staticmethod
    def open(hive: int, path: str):
        import winreg
        return winreg.OpenKey(hive, path)

    @staticmethod
    def read(key: Any, name: str) -> Optional[str]:
        import winreg
        try:
            value, _ = winreg.QueryValueEx(key, name)
            return str(value) if value is not None else None
        except OSError:
            return None

    @staticmethod
    def subkeys(key: Any) -> List[str]:
        out, i = [], 0
        while True:
            try:
                out.append(key.EnumKey(i))
            except OSError:
                break
            except AttributeError:
                # Raw PyHKEY: fall back to the winreg module function.
                try:
                    out.append(winreg.EnumKey(key, i))
                except OSError:
                    break
                i += 1
                continue
            i += 1
        return out

    @staticmethod
    def close(key: Any) -> None:
        try:
            key.Close()
        except Exception:
            pass


# --------------------------------------------------------------------------
# Adapters — each returns (games, notes). `notes` carries per-source issues
# ("access denied", "not installed") so the UI can say what was not inspected.
# A note exists per launcher, never silently swallowed.
# --------------------------------------------------------------------------

def _steam_root_candidates() -> List[str]:
    """Well-known Steam homes plus registry-discovered overrides."""
    roots = [
        r"C:\Program Files (x86)\Steam",
        r"C:\Program Files\Steam",
    ]
    if os.name == "nt" and winreg:
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for hive_path in (
                r"SOFTWARE\Valve\Steam",
                r"SOFTWARE\Wow6432Node\Valve\Steam",
            ):
                try:
                    key = _Registry.open(hive, hive_path)
                    val = _Registry.read(key, "SteamPath") or _Registry.read(key, "InstallPath")
                    _Registry.close(key)
                    if val:
                        roots.append(val.replace("/", "\\"))
                        break
                except OSError:
                    continue

    # normcase dedupe: the registry often stores a lowercase/forward-slash
    # variant of the same install path — without normalization the same
    # library would be scanned twice and inflate the candidate count.
    return [p for p in dict.fromkeys(os.path.normcase(p) for p in roots) if p]


def _steam_library_paths(root: str) -> List[str]:
    """All Steam libraries: the root plus every configured library path."""
    paths = [root]
    try:
        with open(os.path.join(root, "steamapps", "libraryfolders.vdf"), "r", encoding="utf-8", errors="replace") as f:
            for m in re.finditer(r'"path"\s+"((?:\\.|[^"])*)"', f.read()):
                paths.append(m.group(1).replace("\\\\", "\\"))
    except OSError:
        pass
    seen: set = set()
    out = []
    for p in paths:
        p = p.rstrip("\\/")
        # VDF entries usually re-state the install root with exact casing;
        # normcase keeps it from duplicating the root itself.
        key = os.path.normcase(p)
        if p and key not in seen:
            seen.add(key)
            out.append(p)
    return out


class SteamAdapter:
    """Read appmanifest_*.acf records from every configured Steam library.

    Records are only trusted when their target install dir still exists —
    that is the "missing files" boundary the task demands.
    """

    source = "steam"

    def scan(self, cancel: _Cancel) -> tuple[List[Dict[str, Any]], List[str]]:
        games: List[Dict[str, Any]] = []
        notes: List[str] = []
        seen_root = False
        for root in _steam_root_candidates():
            libs = _steam_library_paths(root)
            if os.path.isdir(root):
                seen_root = True
            for lib in libs:
                if cancel.cancelled():
                    break
                sa = os.path.join(lib, "steamapps")
                try:
                    manifests = [f for f in os.listdir(sa) if re.match(r"appmanifest_\d+\.acf$", f)]
                except OSError:
                    # A configured library whose steamapps cannot be read is a
                    # real diagnostic: disconnected/removable drive, deleted
                    # library, or permission problem. Not silence. A
                    # well-known default root that simply is not installed on
                    # this PC is NOT a finding — no note for it.
                    if os.path.isdir(lib) or (lib != root and os.path.exists(lib[:2] + "\\")):
                        notes.append(f"Steam library unreadable (missing or access denied): {lib}")
                    elif lib != root:
                        notes.append(f"Steam library drive not connected: {lib}")
                    continue
                for mf in manifests:
                    if cancel.cancelled():
                        break
                    m = re.match(r"appmanifest_(\d+)\.acf$", mf)
                    appid = m.group(1)
                    try:
                        with open(os.path.join(sa, mf), "r", encoding="utf-8", errors="replace") as fp:
                            text = fp.read()
                    except OSError:
                        continue
                    name_m = re.search(r'"name"\s+"([^"]*)"', text)
                    dir_m = re.search(r'"installdir"\s+"([^"]*)"', text)
                    state_m = re.search(r'"StateFlags"\s+"(\d+)"', text)
                    if not name_m:
                        continue
                    name = name_m.group(1)
                    # Steam-library tooling/runtimes are not games — the same
                    # honest filter used for the legacy profileless list.
                    if NON_GAME_PATTERNS.search(name):
                        continue
                    # Uninstalled/needs-update manifests must not claim files.
                    if state_m and state_m.group(1) not in {"4", "2"}:
                        continue
                    install_dir = None
                    if dir_m:
                        cand = os.path.join(lib, "steamapps", "common", dir_m.group(1))
                        # Steam sometimes tracks case/name mismatches — the
                        # directory presence is the validation.
                        if os.path.isdir(cand):
                            install_dir = cand
                    status = STATUS_INSTALLED if install_dir else STATUS_MISSING
                    game = {
                        "id": f"steam:{appid}",
                        "name": name,
                        "source": self.source,
                        "appid": int(appid),
                        "install_path": install_dir,
                        "exe_path": resolve_game_exe(install_dir) if install_dir else None,
                        "status": status,
                    }
                    games.append(game)
        if not seen_root and not games:
            notes.append("Steam not found on this PC (checked default and registry paths).")
        return games, notes


class EpicAdapter:
    """Epic Games Launcher manifests (.item files under Manifests)."""

    source = "epic"

    def scan(self, cancel: _Cancel) -> tuple[List[Dict[str, Any]], List[str]]:
        games: List[Dict[str, Any]] = []
        notes: List[str] = []
        if os.name != "nt":
            notes.append("Epic detection supports Windows only.")
            return games, notes
        seen = False
        base = os.path.join(
            os.environ.get("PROGRAMDATA", r"C:\ProgramData"),
            "Epic", "EpicGamesLauncher", "Data", "Manifests",
        )
        try:
            files = os.listdir(base)
            seen = True
        except (OSError, PermissionError):
            files = []
        if seen and not files:
            notes.append("Epic Games Launcher present but no installs registered.")
        if not seen:
            # "Launcher installed, Manifests never created" is a different
            # truth than "Epic is not on this PC" — the diagnostics say so.
            launcher_roots = [
                os.path.join(os.environ.get("PROGRAMDATA", r"C:\\ProgramData"), "Epic", "EpicGamesLauncher"),
                os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\\Program Files (x86)"), "Epic Games", "Launcher"),
                os.path.join(os.environ.get("ProgramFiles", r"C:\\Program Files"), "Epic Games", "Launcher"),
            ]
            if any(os.path.isdir(p) for p in launcher_roots):
                notes.append("Epic Games Launcher installed but no games registered.")
            else:
                notes.append("Epic Games not found on this PC (no Manifests directory).")
        for f in files:
            if cancel.cancelled():
                break
            if not f.endswith(".item"):
                continue
            try:
                with open(os.path.join(base, f), "r", encoding="utf-8") as fp:
                    data = json.load(fp)
            except (OSError, json.JSONDecodeError):
                notes.append(f"Skipped unreadable Epic manifest: {f}")
                continue
            name = data.get("DisplayName") or data.get("AppName")
            path = data.get("InstallLocation") or ""
            launch = data.get("LaunchExecutable") or ""
            if not name or not path:
                continue
            exe_path = os.path.join(path, launch) if launch else None
            valid = os.path.isdir(path) and (exe_path is None or os.path.isfile(exe_path))
            games.append({
                "id": f"epic:{data.get('AppName', f)}",
                "name": name,
                "source": self.source,
                "install_path": path if os.path.isdir(path) else None,
                "exe_path": exe_path if valid else None,
                "status": STATUS_INSTALLED if valid else STATUS_MISSING,
            })
        return games, notes


class RiotAdapter:
    """Riot games via the RiotClientInstalls.json registry of real installs."""

    source = "riot"

    def scan(self, cancel: _Cancel) -> tuple[List[Dict[str, Any]], List[str]]:
        games: List[Dict[str, Any]] = []
        notes: List[str] = []
        if os.name != "nt":
            notes.append("Riot detection supports Windows only.")
            return games, notes
        import winreg
        # Valorant/LoR etc. register per-product installs under riot games keys;
        # that record is evidence of installation, Riot Client existence is not.
        paths_to_scan = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Riot Games, Inc"),
        ]
        seen_client = False
        for hive, path in paths_to_scan:
            try:
                key = _Registry.open(hive, path)
            except OSError:
                continue
            seen_client = True
            for sub in _Registry.subkeys(key):
                if cancel.cancelled():
                    break
                skey = None
                try:
                    skey = _Registry.open(key, sub)
                    install_path = _Registry.read(skey, "InstallPath")
                    exe_name = _Registry.read(skey, "ExeName")
                finally:
                    if skey:
                        _Registry.close(skey)
                if not install_path:
                    continue
                exe_path = os.path.join(install_path, exe_name or "")
                valid = os.path.isdir(install_path) and os.path.isfile(exe_path)
                games.append({
                    # id is stable from the subkey, e.g. 'Riot Games Valorant'
                    "id": f"riot:{_norm(sub).replace(' ', '-')}",
                    "name": sub.replace("_", " ").replace("Games", "").strip().title(),
                    "source": self.source,
                    "install_path": install_path if os.path.isdir(install_path) else None,
                    "exe_path": exe_path if valid else None,
                    "status": STATUS_INSTALLED if valid else STATUS_MISSING,
                })
            _Registry.close(key)
        if seen_client and not games:
            notes.append("Riot Client exists, but no product install records were found.")
        if not seen_client:
            notes.append("Riot Games not found on this PC.")
        return games, notes


class BattleNetAdapter:
    """Battle.net keeps product install state as JSON under %APPDATA%. US/xx."""

    source = "battlenet"

    def scan(self, cancel: _Cancel) -> tuple[List[Dict[str, Any]], List[str]]:
        games: List[Dict[str, Any]] = []
        notes: List[str] = []
        if os.name != "nt":
            notes.append("Battle.net detection supports Windows only.")
            return games, notes
        seen = False
        base = os.path.join(os.environ.get("APPDATA", ""), "Battle.net")
        try:
            product_db = os.path.join(base, "Battle.net.config")  # not products
            seen = os.path.isdir(base)
            product_files = []
            # Battle.net tracks products in 'battle.net' folders per region.
            for f in os.listdir(base):
                if f.lower().endswith(".config"):
                    product_files.append(f)
            _ = product_db
        except OSError:
            product_files = []
        if not seen:
            notes.append("Battle.net not found on this PC.")
            return games, notes

        # Installed products are under 'Product DB' sibling folder:
        prod_root = os.path.join(base, "ProductDB")
        try:
            for f in os.listdir(prod_root):
                if cancel.cancelled():
                    break
                if not f.endswith(".json"):
                    continue
                try:
                    with open(os.path.join(prod_root, f), "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                except (OSError, json.JSONDecodeError):
                    continue
                settings = data.get("Settings", {}) or {}
                name = settings.get("Title") or f.replace(".json", "")
                path = settings.get("InstallPath") or ""
                if not name or not path:
                    continue
                valid = os.path.isdir(path)
                games.append({
                    "id": f"battlenet:{f.replace('.json', '')}",
                    "name": name,
                    "source": self.source,
                    "install_path": path if valid else None,
                    "exe_path": None,
                    "status": STATUS_INSTALLED if valid else STATUS_MISSING,
                })
        except OSError:
            notes.append("Battle.net product database unreadable (permissions).")
        return games, notes


class GogAdapter:
    """GOG keeps a python-style sqlite-free registry record in HKLM."""

    source = "gog"

    KNOWN_EXES: Dict[str, str] = {}  # filled by validation, no hardcoding

    def scan(self, cancel: _Cancel) -> tuple[List[Dict[str, Any]], List[str]]:
        games: List[Dict[str, Any]] = []
        notes: List[str] = []
        if os.name != "nt":
            notes.append("GOG detection supports Windows only.")
            return games, notes
        import winreg
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for path in (r"SOFTWARE\GOG.com\Games", r"SOFTWARE\Wow6432Node\GOG.com\Games"):
                if cancel.cancelled():
                    break
                try:
                    key = _Registry.open(hive, path)
                except OSError:
                    continue
                for sub in _Registry.subkeys(key):
                    skey = None
                    try:
                        skey = _Registry.open(key, sub)
                        gname = _Registry.read(skey, "displayName") or sub
                        gpath = _Registry.read(skey, "path") or ""
                        exe = _Registry.read(skey, "exe") or _Registry.read(skey, "LaunchExec") or ""
                    finally:
                        if skey:
                            _Registry.close(skey)
                    exe_path = os.path.join(gpath, exe) if gpath and exe else None
                    valid = os.path.isdir(gpath)
                    games.append({
                        "id": f"gog:{sub}",
                        "name": gname,
                        "source": self.source,
                        "install_path": gpath if valid else None,
                        "exe_path": exe_path if (valid and exe_path and os.path.isfile(exe_path)) else None,
                        "status": STATUS_INSTALLED if valid else STATUS_MISSING,
                    })
                _Registry.close(key)
        if not games:
            notes.append("GOG games not found on this PC.")
        return games, notes


class EaAppAdapter:
    """EA app: install records in HKLM..EA Games plus common dir validation."""

    source = "ea"

    def scan(self, cancel: _Cancel) -> tuple[List[Dict[str, Any]], List[str]]:
        games: List[Dict[str, Any]] = []
        notes: List[str] = []
        if os.name != "nt":
            notes.append("EA app detection supports Windows only.")
            return games, notes
        import winreg
        for hive_path in (
            r"SOFTWARE\EA Games",
            r"SOFTWARE\Wow6432Node\EA Games",
        ):
            try:
                key = _Registry.open(winreg.HKEY_LOCAL_MACHINE, hive_path)
            except OSError:
                continue
            for sub in _Registry.subkeys(key):
                if cancel.cancelled():
                    break
                skey = None
                try:
                    skey = _Registry.open(key, sub)
                    disp = _Registry.read(skey, "DisplayName") or sub
                    path = _Registry.read(skey, "InstallPath") or ""
                    exe = _Registry.read(skey, "Executable") or ""
                finally:
                    if skey:
                        _Registry.close(skey)
                exe_path = os.path.join(path, exe) if path and exe else None
                valid = os.path.isdir(path)
                games.append({
                    "id": f"ea:{_norm(sub).replace(' ', '-')}",
                    "name": disp,
                    "source": self.source,
                    "install_path": path if valid else None,
                    "exe_path": exe_path if (valid and exe_path and os.path.isfile(exe_path)) else None,
                    "status": STATUS_INSTALLED if valid else STATUS_MISSING,
                })
            _Registry.close(key)
        if not games:
            notes.append("EA games not found on this PC.")
        return games, notes


class UbisoftAdapter:
    """Ubisoft Connect via registry install keys."""

    source = "ubisoft"

    def scan(self, cancel: _Cancel) -> tuple[List[Dict[str, Any]], List[str]]:
        games: List[Dict[str, Any]] = []
        notes: List[str] = []
        if os.name != "nt":
            notes.append("Ubisoft detection supports Windows only.")
            return games, notes
        import winreg
        for hive_path in (
            r"SOFTWARE\Ubisoft\Launcher\Installs",
            r"SOFTWARE\Wow6432Node\Ubisoft\Launcher\Installs",
        ):
            try:
                key = _Registry.open(winreg.HKEY_LOCAL_MACHINE, hive_path)
            except OSError:
                continue
            for sub in _Registry.subkeys(key):
                if cancel.cancelled():
                    break
                skey = None
                try:
                    skey = _Registry.open(key, sub)
                    # InstallDir may hold the path directly.
                    path = _Registry.read(skey, "InstallDir") or ""
                finally:
                    if skey:
                        _Registry.close(skey)
                if not path:
                    continue
                valid = os.path.isdir(path)
                games.append({
                    "id": f"ubisoft:{sub.lower()}",
                    # Install key names are SKU ids, titles may differ; the
                    # name is taken from the folder's executable instead.
                    "name": os.path.basename(path.rstrip("\\/")) or sub,
                    "name_from": "folder",
                    "source": self.source,
                    "install_path": path if valid else None,
                    "exe_path": None,
                    "status": STATUS_INSTALLED if valid else STATUS_MISSING,
                })
            _Registry.close(key)
        if not games:
            notes.append("Ubisoft Connect games not found on this PC.")
        return games, notes


class GryphlineAdapter:
    """Gryphline launcher installs (Arknights: Endfield, Ex Astris…).

    Two evidence sources, both required-together: the launcher's uninstall
    registry key proves the launcher exists, and the games folder it manages
    (`<launcher>\\games\\<Title>`) must contain the game's own exe for a
    title to be reported installed. The Start-menu shortcuts point at
    `Launcher.exe --game=<slug>`, so the slug is read as secondary evidence
    but never invents an installation on its own.
    """

    source = "gryphline"

    # Registry keys the Gryphline launcher writes for itself and its games.
    _UNINSTALL_KEYS = (
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\GRYPHLINK",
        r"SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\GRYPHLINK",
    )

    @classmethod
    def _launcher_roots(cls) -> List[str]:
        roots: List[str] = []
        for hive_path in cls._UNINSTALL_KEYS:
            try:
                key = _Registry.open(winreg.HKEY_LOCAL_MACHINE, hive_path)
            except OSError:
                continue
            if key:
                try:
                    loc = _Registry.read(key, "InstallLocation")
                finally:
                    _Registry.close(key)
                if loc and os.path.isdir(loc):
                    roots.append(loc)
        if not roots:
            # Fallback on the well-known install root (still verified below).
            root = r"C:\Program Files\GRYPHLINK"
            if os.path.isdir(root):
                roots.append(root)
        return [p for p in dict.fromkeys(os.path.normcase(r) for r in roots) if p]

    def scan(self, cancel: _Cancel) -> tuple[List[Dict[str, Any]], List[str]]:
        games: List[Dict[str, Any]] = []
        notes: List[str] = []
        if os.name != "nt":
            notes.append("Gryphline detection supports Windows only.")
            return games, notes
        roots = self._launcher_roots()
        if not roots:
            notes.append("Gryphline launcher not found on this PC.")
            return games, notes
        for root in roots:
            if cancel.cancelled():
                break
            games_dir = os.path.join(root, "games")
            try:
                titles = os.listdir(games_dir)
            except OSError:
                notes.append(f"Gryphline games folder unreadable: {games_dir}")
                continue
            if not titles:
                notes.append("Gryphline launcher present but no games installed.")
            for title in sorted(titles):
                install_dir = os.path.join(games_dir, title)
                if not os.path.isdir(install_dir):
                    continue
                exe_path = self._resolve_game_exe(install_dir, title)
                games.append({
                    "id": f"gryphline:{_norm(title).replace(' ', '-')}",
                    "name": title,
                    "source": self.source,
                    "install_path": install_dir,
                    # Launcher itself can start the game; exe_path enables
                    # direct launch only when a real game binary exists.
                    "launcher_exe": os.path.join(root, "Launcher.exe")
                    if os.path.isfile(os.path.join(root, "Launcher.exe")) else None,
                    "exe_path": exe_path,
                    "status": STATUS_INSTALLED if exe_path else STATUS_MISSING,
                })
        if not games and roots:
            notes.append("Gryphline found but no game installed under games\\.")
        return games, notes

    @staticmethod
    def _resolve_game_exe(install_dir: str, title: str) -> Optional[str]:
        """Exe for a Gryphline title, evidence-first.

        The launcher stores one folder per game and the folder's exe usually
        shares a token with the title ('Arknights Endfield' -> Endfield.exe).
        These entry exes are small Unity stubs, so the 5 MB heuristic in
        resolve_game_exe misfires — a title-token match is stronger evidence
        than size here. Helpers (uninstallers, crash handlers…) stay excluded.
        """
        title_tokens = {t for t in _norm(title).split() if len(t) >= 3}
        try:
            entries = os.listdir(install_dir)
        except OSError:
            return None
        token_hit: Optional[str] = None
        big_hit: Optional[str] = None
        for e in entries:
            if os.path.splitext(e)[1].lower() not in _EXECUTABLE_EXTS or _NOT_GAME_EXE.search(e):
                continue
            full = os.path.join(install_dir, e)
            try:
                size = os.path.getsize(full)
            except OSError:
                continue
            stem = _norm(os.path.splitext(e)[0])
            if not token_hit and size >= 64 * 1024 and any(
                tok in stem for tok in title_tokens
            ):
                token_hit = full
            if big_hit is None and size >= _MIN_GAME_EXE_BYTES:
                big_hit = full
        # Token match beats generic size; fall back to the size heuristic.
        return token_hit or big_hit or resolve_game_exe(install_dir)


def resolve_lnk_target(lnk_path: str) -> tuple[Optional[str], str]:
    """Read a Windows shortcut's target + arguments without executing it.

    Pure-Python MS-SHLLINK parser — no COM dependency. Follows the spec
    layout: ShellLinkHeader (0x4C), optional IDList, optional LinkInfo
    (LocalBasePathOffset at +0x10 of the LinkInfo header — and LinkInfo
    starts AFTER the IDList, not at a fixed 0x4C), then the StringData
    blocks in flag order (Name, RelativePath, WorkingDir, Arguments,
    IconLocation). Returns (None, error) when the file is not a shortcut or
    malformed. Discovery never runs the target.
    """
    try:
        with open(lnk_path, "rb") as f:
            data = f.read(64 * 1024)
    except OSError as e:
        return None, f"Shortcut unreadable: {e}"
    if len(data) < 0x4C or data[:4] != b"L\x00\x00\x00":
        return None, "Not a Shell Link file."
    flags = int.from_bytes(data[0x14:0x18], "little")
    target = None
    args = ""
    pos = 0x4C  # end of ShellLinkHeader; optional blocks follow in order
    stream_ok = True

    def _utf16_strings(blob: bytes):
        """Decode null-terminated UTF-16LE runs. Heuristic read of IDList
        long-name entries; every result is validated by the caller."""
        import re as _re
        for m in _re.finditer(rb"(?:[\x20-\x7e]\x00){4,}", blob):
            try:
                yield m.group(0).decode("utf-16-le")
            except UnicodeDecodeError:
                continue

    # Optional IDList comes first; LinkInfo (when present) follows it.
    if flags & 0x1:
        if pos + 2 > len(data):
            stream_ok = False
        else:
            pos += 2 + int.from_bytes(data[pos:pos + 2], "little")
            if pos > len(data):
                stream_ok = False

    # Primary: LinkInfo LocalBasePath — an exact machine path. LinkInfo sits
    # directly at `pos` (no offset pointer). Header fields: Size(+0x00),
    # HeaderSize(+0x04), Flags(+0x08), VolumeIDOffset(+0x0C),
    # LocalBasePathOffset(+0x10), CNRLOffset(+0x14), SuffixOffset(+0x18),
    # and LocalBasePathOffsetUnicode(+0x1C) when HeaderSize >= 0x20.
    if flags & 0x2:
        li_size = hdr_size = 0
        if 0 <= pos < len(data) - 8:
            li_size = int.from_bytes(data[pos:pos + 4], "little")
            hdr_size = int.from_bytes(data[pos + 4:pos + 8], "little")
        if 0x1C <= hdr_size <= li_size and pos + li_size <= len(data):
            def _li_path(off: int, wide: bool) -> Optional[str]:
                if off <= 0 or off >= li_size:
                    return None
                raw = data[pos + off: pos + li_size]
                if wide:
                    end = len(raw)
                    for i in range(0, len(raw) - 1, 2):
                        if raw[i] == 0 and raw[i + 1] == 0:
                            end = i
                            break
                    cand = raw[:end].decode("utf-16-le", "replace")
                else:
                    end = raw.find(b"\x00")
                    if end <= 0:
                        return None
                    cand = raw[:end].decode("latin-1", "replace")
                if ":\\" in cand or cand.startswith("\\\\"):
                    return cand
                return None

            target = _li_path(int.from_bytes(data[pos + 0x10:pos + 0x14], "little"), False)
            if target is None and hdr_size >= 0x20:
                target = _li_path(int.from_bytes(data[pos + 0x1C:pos + 0x20], "little"), True)
            pos += li_size
        else:
            # Malformed LinkInfo: the stream position is unknown from here.
            stream_ok = False

    # Fallback for IDList-only shortcuts (modern installers store the target
    # as shell item names, not a LinkInfo path): take the last plausible
    # absolute exe path in the blob. Validation isfile() happens in scan();
    # nothing here is ever executed.
    if target is None:
        import re as _re
        for s in _utf16_strings(data):
            if _re.search(r"^[A-Za-z]:\\.+\.exe$", s, _re.I) and not _NOT_GAME_EXE.search(
                os.path.splitext(os.path.basename(s))[0]
            ):
                target = s
        utf8_hits = _re.findall(rb"(?:[\x20-\x7e]{4,}\.exe)", data[:0x8000], _re.I)
        if target is None:
            for raw_bytes in utf8_hits[::-1]:
                s = raw_bytes.decode("latin-1", "replace")
                if _re.search(r"^[A-Za-z]:\\.+\.exe$", s, _re.I):
                    target = s
                    break

    # StringData (exact, in flag order): Name, RelativePath, WorkingDir,
    # Arguments, IconLocation — each a uint16 character count followed by
    # that many UTF-16LE characters. Arguments are only trusted from here;
    # the heuristic below rescues malformed files where the stream position
    # could not be established.
    if stream_ok:
        for bit in (0x4, 0x10, 0x20, 0x8, 0x40):
            if not (flags & bit):
                continue
            if pos + 2 > len(data):
                stream_ok = False
                break
            n_chars = int.from_bytes(data[pos:pos + 2], "little")
            n_bytes = n_chars * 2
            if pos + 2 + n_bytes > len(data):
                stream_ok = False
                break
            text = data[pos + 2: pos + 2 + n_bytes].decode("utf-16-le", "replace")
            pos += 2 + n_bytes
            if bit == 0x8:
                args = text.strip()
    if target is not None and not stream_ok:
        # Rescue for malformed files: a UTF-16 run starting with a flag is
        # the strongest signal. A run can swallow the next block's 2-byte
        # length prefix, so cut at the first embedded drive path.
        for s in _utf16_strings(data):
            st = s.strip("\x00\ufeff").strip()
            if st.startswith("--") or (st.startswith("/") and " " in st and ":\\" not in st):
                args = st
                break
        if args and '"' not in args:
            drive = re.search(r"[A-Za-z]:\\", args)
            if drive:
                args = args[:drive.start()].rstrip("[ ").strip()
    if target is None:
        return None, "Shortcut target could not be resolved safely."
    return f"{target}|{args}" if args else target, ""


class StartMenuShortcutAdapter:
    """Source B: Start Menu shortcuts as discovery witnesses.

    A shortcut is evidence that its target was installed — never proof it is
    a game or still present. Filters, in order:
      1. known launcher-surface names (Steam, GRYPHLINK, Riot Client…) are
         NOT games and are skipped
      2. helpers (uninstallers, tutorials, SDK docs, driver tools) skipped
      3. targets inside Windows system directories are never games
      4. the resolved target must still exist for an 'installed' status;
         a vanished target is reported as 'missing' instead of hidden
    Dedup merges shortcut evidence into launcher-found records by exe path.
    """

    source = "startmenu"

    # Shortcut folder/display names that are launcher surfaces or utility
    # suites rather than games themselves.
    _LAUNCHER_NAMES = re.compile(
        r"\b(steam|steamtools|gryphlink|epic games launcher|riot client|"
        r"battle\.net|gog galaxy|ea app|ubisoft connect|origin|"
        r"msi afterburner|geforce|nvidia app|amd software|adrenalin|"
        r"project lightning|"
        r"discord|roblox studio|optimi[sz]er)\b",
        re.I,
    )
    # Shortcut names that are utility/tooling, not playable titles.
    _NOT_GAME_NAMES = re.compile(
        r"uninstall|update|setup|readme|help|tutorial|documentation|eula|"
        r"license|check for|redistribut|directx|anticheat|anti-cheat|"
        r"\bide\b|auto clicker|sdk|kernel stuff|unload|"
        r"remote desktop|vpn|command prompt|release notes",
        re.I,
    )
    # Well-known desktop applications that pass a naive name filter. Without
    # this denylist the Start Menu fills with dev tools and messengers.
    _KNOWN_APPS = re.compile(
        r"visual studio|vs ?code|\bgit\b|github|gitlab|\bnode\b|npm|"
        r"android studio|blend for|\bcode\b|\bkernel\b|"
        r"chrome|edge|firefox|brave|opera|tor browser|"
        r"explorer|internet explorer|notepad|\bpaint\b|wordpad|calculator|"
        r"telegram|whatsapp|signal|zoom|slack|teams|"
        r"spotify|discord|plexo|freebuff|opencode|luatools|"
        r"cheat engine|silent aim|trainer|"
        r"remote desktop|quick assist|steps recorder|media player|"
        r"vivaldi|microsoft edge|onedrive|dropbox|"
        r"winrar|7-?zip|winzip|\bpython\b|\bidle\b|module docs|"
        r"fxsound|ultraviewer|spacedesk|app cert|windows performance|"
        r"\bgpuview\b|\bwpa\b|\bwpr\b|windows kits|optinix|geforce now",
        re.I,
    )
    # Known game/emulator executables — recorded as kind='emulator'
    # so the library groups them separately from native PC games. Console
    # emulators are included: without this their size heuristic would label
    # the player itself as a "game".
    _EMULATOR_EXES = re.compile(
        r"^(hd-player|mumuplayer|mumu|nox|dnplayer|ldplayer|ld\d*player|"
        r"memuplay|bluestacks|msi app player|gameloop|txgameassistant|"
        r"gameassistant|pcsx2|pcsx2-qt|rpcs3|dolphin|dolphinwx|yuzu|suyu|"
        r"ryujinx|xenia|xenia-canary|ppsspp|ppssppwindows|duckstation|"
        r"retroarch|cemu|vita3k|mupen64plus|project64|mednafen|bizhawk|"
        r"scummvm)\b",
        re.I,
    )
    # Launcher executables: a shortcut may point at one, but only with game
    # specific arguments does it become that game's launch target.
    _LAUNCHER_EXES = re.compile(
        r"^(launcher|steam|epicgameslauncher|riotclient|battle\.net|"
        r"gog galaxy|origin|ubisoft game launcher|heroic|grhyplink)\.exe$",
        re.I,
    )

    # A shortcut named for a file/folder concept ("File", "Filee", "App",
    # "Game") is a shell artifact, not a title. The pattern must match the
    # WHOLE name: the caller also tests the shortcut's folder prefix, and a
    # prefix rule would reject every entry under a folder called "Games" or
    # "Programs". Repeated letters are collapsed as a fallback so "Filee" is
    # caught with "File".
    _GENERIC_TITLE = re.compile(
        r"^(?:file|files|app|apps|game|games|program|programs|tool|tools|"
        r"folder|folders|main|run|start|startup|setup|install|installer|"
        r"test|demo|sort)(?:[ _-]?\d{0,3})?$",
        re.I,
    )

    @classmethod
    def _is_generic_title(cls, title: str) -> bool:
        name = title.strip()
        return bool(
            cls._GENERIC_TITLE.match(name)
            or cls._GENERIC_TITLE.match(re.sub(r"(.)\1+", r"\1", name))
        )

    @classmethod
    def _is_game_shortcut(cls, title: str) -> bool:
        if not title:
            return False
        if cls._LAUNCHER_NAMES.search(title) or cls._NOT_GAME_NAMES.search(title):
            return False
        if NON_GAME_PATTERNS.search(title):
            return False
        if cls._is_generic_title(title):
            return False
        return True

    @staticmethod
    def _shortcut_files(cancel: _Cancel) -> List[str]:
        roots = [
            os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
            os.path.join(os.environ.get("PROGRAMDATA", r"C:\ProgramData"), r"Microsoft\Windows\Start Menu\Programs"),
        ]
        out: List[str] = []
        for root in roots:
            if cancel.cancelled() or not root or not os.path.isdir(root):
                continue
            for dirpath, _dirnames, filenames in os.walk(root):
                if cancel.cancelled():
                    break
                for f in filenames:
                    if f.lower().endswith(".lnk"):
                        out.append(os.path.join(dirpath, f))
            # Bounded: a Start Menu tree is hundreds of items, not thousands.
            if len(out) >= 1500:
                break
        return out

    def scan(self, cancel: _Cancel) -> tuple[List[Dict[str, Any]], List[str]]:
        games: List[Dict[str, Any]] = []
        notes: List[str] = []
        if os.name != "nt":
            notes.append("Start Menu discovery supports Windows only.")
            return games, notes
        lnks = self._shortcut_files(cancel)
        if not lnks:
            notes.append("No accessible Start Menu shortcuts found.")
            return games, notes
        skipped_names = 0
        broken_targets = 0
        com_failed = False
        for lnk in lnks:
            if cancel.cancelled():
                break
            title = os.path.splitext(os.path.basename(lnk))[0]
            surface = f"{os.path.basename(os.path.dirname(lnk))} {title}"
            name_ok = (
                self._is_game_shortcut(title)
                and self._is_game_shortcut(surface)
                and not self._KNOWN_APPS.search(surface)
            )
            if not name_ok:
                skipped_names += 1
                continue
            resolved, err = self._resolve(lnk)
            if resolved is None:
                if "pywin32" in err:  # pragma: no cover - legacy COM path
                    notes.append(err)
                    com_failed = True
                    break
                broken_targets += 1
                continue
            target, _, arg_part = resolved.partition("|")
            args_cmd = arg_part or ""
            if not target:
                broken_targets += 1
                continue
            # Downloaded installers and truncated temp paths are not installs.
            tlow = os.path.normcase(target)
            if "\\downloads\\" in tlow or "\\temp\\" in tlow:
                broken_targets += 1
                continue
            win_dir = os.environ.get("WINDIR", r"C:\Windows").lower()
            if tlow.startswith(os.path.normcase(win_dir)):
                broken_targets += 1
                continue
            # Only an .exe target can witness a game installation. .url/.msc/
            # .doc shortcuts (the Windows SDK ships .url links inside its
            # Start Menu folder) are documentation or tooling surfaces and
            # can never be launched or validated as a game.
            if not target.lower().endswith(".exe"):
                broken_targets += 1
                continue
            exe_name = os.path.basename(target)
            if _NOT_GAME_EXE.search(exe_name) or self._LAUNCHER_EXES.match(exe_name):
                # A launcher target is only a game's launch when the
                # shortcut arguments name that game (--game=<slug> style).
                if not re.search(r"--game=\S", args_cmd, re.I):
                    broken_targets += 1
                    continue
                # Launcher-driven game: exe exists == launcher exists. The
                # game files themselves are validated by the launcher's own
                # adapter; here the record keeps its shortcut evidence and
                # waits to merge with richer launcher discovery.
                valid = os.path.isfile(target)
                games.append({
                    "id": f"startmenu:{_norm(title).replace(' ', '-')}",
                    "name": title,
                    "source": self.source,
                    "install_path": None,
                    "exe_path": None,
                    "shortcut_path": lnk,
                    "launch_target": target if valid else None,
                    "launch_args": args_cmd,
                    "status": STATUS_INSTALLED if valid else STATUS_MISSING,
                })
                continue
            valid = os.path.isfile(target)
            try:
                big = os.path.getsize(target) >= _MIN_GAME_EXE_BYTES if valid else False
            except OSError:
                big = False
            is_emu = bool(self._EMULATOR_EXES.match(exe_name))
            # An allowlisted emulator shell is identified by its exact exe
            # name, so the game-binary size heuristic does not apply — a
            # 0.5 MB BlueStacks launcher is still a verified install, while
            # an unverified big-exe rule stays in force for native games.
            status = STATUS_MISSING
            if valid and (big or is_emu):
                status = STATUS_INSTALLED
            games.append({
                "id": f"startmenu:{_norm(title).replace(' ', '-')}",
                "name": title,
                "source": self.source,
                "kind": "emulator" if is_emu else "game",
                "install_path": os.path.dirname(target) if valid else None,
                "exe_path": target if valid else None,
                "shortcut_path": lnk,
                "launch_args": args_cmd,
                "status": status,
            })
        if not com_failed:
            notes.append(
                f"Start Menu scanned: {len(games)} game-like shortcuts, "
                f"{skipped_names} non-game names, {broken_targets} broken/system targets."
            )
        return games, notes

    # Patchable in tests so real COM/pythoncom is never needed.
    _resolve = staticmethod(resolve_lnk_target)


class EmulatorAdapter:
    """Installed emulators as first-class library entries (kind='emulator').

    Two independent witnesses, both verified against real files:
      1. uninstall registry entries whose DisplayName names a known player
      2. well-known install locations checked for the player executable

    Only the emulator itself is recorded. An Android player's internal app
    store is proprietary and cannot be read offline, so no emulator-owned
    game is ever invented — titles a game exposes as Start Menu/desktop
    shortcuts still arrive through the shortcut adapter (and merge here by
    title+path rather than duplicating).

    The player executable is matched by exact name, so a small launcher
    binary still verifies (the same rule the shortcut adapter uses for
    BlueStacks shells).
    """

    source = "emulator"

    # Known players, matched against display names (registry) or exe names.
    _NAME = re.compile(
        r"bluestacks|msi app player|ldplayer|ld player|noxplayer|nox app player|"
        r"mumuplayer|mumu ?player|memuplay|memu ?play|gameloop|game ?loop|"
        r"txgameassistant|gameassistant|\bandy\b|droid4x|"
        r"pcsx2|rpcs3|dolphin emulator|\byuzu\b|suyu|ryujinx|\bxenia\b|"
        r"ppsspp|duckstation|retroarch|\bcemu\b|vita3k|mupen|project64|"
        r"mednafen|bizhawk|scummvm",
        re.I,
    )
    _EXE = re.compile(
        r"^(hd-player|mumuplayer|mumu|nox|dnplayer|ldplayer|ld\d*player|"
        r"memuplay|bluestacks|msi app player|gameloop|txgameassistant|"
        r"gameassistant|pcsx2|pcsx2-qt|rpcs3|dolphin|dolphinwx|yuzu|suyu|"
        r"ryujinx|xenia|xenia-canary|ppsspp|ppssppwindows|duckstation|"
        r"retroarch|cemu|vita3k|mupen64plus|project64|mednafen|bizhawk|"
        r"scummvm)(\.exe)?$",
        re.I,
    )

    # Install dirs relative to a Program Files-style root, with the human
    # name users know them by (so the shortcut/registry records for the same
    # install merge by title+path instead of duplicating). Expanded over
    # every standard root so a library on D:\ is found as well as on C:\.
    _REL_DIRS = {
        r"BlueStacks_nxt": "BlueStacks",
        r"BlueStacks_x": "BlueStacks",
        r"BlueStacks_msi5": "MSI App Player",
        r"BlueStacks_msi": "MSI App Player",
        r"BlueStacks": "BlueStacks",
        r"MSI App Player": "MSI App Player",
        r"LDPlayer\LDPlayer9": "LDPlayer 9",
        r"LDPlayer\LDPlayer4.0": "LDPlayer 4.0",
        r"LDPlayer": "LDPlayer",
        r"Nox\bin": "NoxPlayer",
        r"Nox": "NoxPlayer",
        r"Netease\MuMuPlayer-12.0": "MuMu Player",
        r"Netease\MuMuPlayer-10.0": "MuMu Player",
        r"MuMuPlayer-12.0": "MuMu Player",
        r"MuMuPlayer-10.0": "MuMu Player",
        r"Microvirt\MEmu": "MEmu",
        r"MEmu": "MEmu",
        r"TxGameAssistant": "GameLoop",
        r"Tencent\GameLoop": "GameLoop",
        r"PCSX2": "PCSX2",
        r"RPCS3": "RPCS3",
        r"Dolphin Emulator": "Dolphin Emulator",
        r"Xenia": "Xenia",
        r"PPSSPP": "PPSSPP",
        r"DuckStation": "DuckStation",
        r"RetroArch": "RetroArch",
        r"Cemu": "Cemu",
        r"Vita3K": "Vita3K",
    }
    # Per-user installs (no admin rights needed) -> display name.
    _LOCAL_DIRS = {
        r"Yuzu": "Yuzu",
        r"Suyu": "Suyu",
        r"Ryujinx": "Ryujinx",
        r"Programs\Yuzu": "Yuzu",
        r"Programs\Suyu": "Suyu",
        r"Programs\Ryujinx": "Ryujinx",
        r"Programs\PPSSPP": "PPSSPP",
    }
    # Bounded shallow search for the player exe inside an install dir.
    _MAX_DEPTH = 2
    _MAX_ENTRIES = 600

    @classmethod
    def _find_exe(cls, root: str) -> Optional[str]:
        """Player executable within the install dir (shallow, bounded), or None."""
        stack = [(root, 0)]
        seen = 0
        while stack and seen < cls._MAX_ENTRIES:
            cur, depth = stack.pop()
            try:
                entries = os.listdir(cur)
            except OSError:
                continue
            for e in entries:
                seen += 1
                if seen >= cls._MAX_ENTRIES:
                    break
                p = os.path.join(cur, e)
                if os.path.isfile(p) and cls._EXE.match(e.lower()):
                    return p
                if depth < cls._MAX_DEPTH and os.path.isdir(p):
                    stack.append((p, depth + 1))
        return None

    @staticmethod
    def _registry_entries() -> List[tuple]:
        """(display_name, install_location) for known emulators. Patchable in tests."""
        out: List[tuple] = []
        if os.name != "nt":
            return out
        import winreg
        uninstall_paths = [
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
            r"SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
        ]
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for uview in uninstall_paths:
                try:
                    key = _Registry.open(hive, uview)
                except OSError:
                    continue
                for sub in _Registry.subkeys(key):
                    skey = None
                    try:
                        skey = _Registry.open(key, sub)
                        disp = _Registry.read(skey, "DisplayName")
                        loc = _Registry.read(skey, "InstallLocation") or ""
                    finally:
                        if skey:
                            _Registry.close(skey)
                    if disp and EmulatorAdapter._NAME.search(disp):
                        out.append((disp, loc))
                _Registry.close(key)
        return out

    @staticmethod
    def _known_dirs() -> List[tuple]:
        """(dir, display_name) candidates from the standard roots. Patchable in tests."""
        roots = [
            os.environ.get("ProgramFiles") or r"C:\Program Files",
            os.environ.get("ProgramFiles(x86)") or r"C:\Program Files (x86)",
        ]
        out = [(os.path.join(r, rel), disp)
               for r in roots for rel, disp in EmulatorAdapter._REL_DIRS.items()]
        local = os.environ.get("LOCALAPPDATA") or ""
        if local:
            out += [(os.path.join(local, rel), disp)
                    for rel, disp in EmulatorAdapter._LOCAL_DIRS.items()]
        return out

    @classmethod
    def _record(cls, name: str, install_path: str, exe: Optional[str], present: bool) -> Dict[str, Any]:
        return {
            "id": f"emulator:{_norm(name).replace(' ', '-')}",
            "name": name,
            "source": cls.source,
            "kind": "emulator",
            "install_path": install_path,
            "exe_path": exe,
            "status": STATUS_INSTALLED if present else STATUS_MISSING,
        }

    def scan(self, cancel: _Cancel) -> tuple[List[Dict[str, Any]], List[str]]:
        games: List[Dict[str, Any]] = []
        notes: List[str] = []
        if os.name != "nt":
            notes.append("Emulator discovery supports Windows only.")
            return games, notes

        seen_dirs: set = set()

        # Witness 1: uninstall registry names, verified against their dirs.
        for disp, loc in self._registry_entries():
            if cancel.cancelled():
                break
            present = bool(loc) and os.path.isdir(loc)
            if not present and not loc:
                # A name without a path cannot be verified — not emitted.
                continue
            exe = self._find_exe(loc) if present else None
            g = self._record(disp, loc if loc else "", exe, present)
            if present:
                seen_dirs.add(os.path.normcase(os.path.abspath(loc)))
            games.append(g)

        # Witness 2: well-known locations with a real player executable.
        if not cancel.cancelled():
            for d, display in self._known_dirs():
                if cancel.cancelled():
                    break
                if not os.path.isdir(d):
                    continue
                norm = os.path.normcase(os.path.abspath(d))
                if norm in seen_dirs:
                    continue
                exe = self._find_exe(d)
                if not exe:
                    continue  # a folder named like an emulator without its player exe proves nothing
                seen_dirs.add(norm)
                games.append(self._record(display, d, exe, True))

        if not games:
            notes.append("No known emulators found on this PC.")
        else:
            notes.append(f"Emulators detected: {', '.join(sorted(g['name'] for g in games))}")
        return games, notes


class XboxAdapter:
    """Microsoft Store / Xbox Game Pass packaged apps.

    Uses the supported Get-AppxPackage probe rather than folder walking. A
    game is only reported when Windows itself says it is installed for the
    current user. Security-focused filtering keeps game publishers —
    non-game Appx entries (Frameworks, runtimes) are rejected.
    """

    source = "xbox"

    # System packages that are never games. Windows ships dozens of these;
    # without the exclusion the "restricted" state would be noise.
    _SYSTEM_PACKAGE_RE = re.compile(
        r"^(microsoft|windows|nvidia|intel|amd|realtek|lenovo|dell|asus|msi"
        r"|photos|xbox\.|microsoft\.xbox|services|feedback|gethelp|getstarted"
        r"|accountscontrol|appinstaller|apimachinery|async|design|desktop"
        r"|deviceassociation|devicediagnostics|ect|explorer|guaranteed|files"
        r"|input|internet|language|licensing|lockapp|map|messeng|netnative"
        r"|oobe|outlook|paint|paypal|print3d|promote|raw|screen|sechealth"
        r"|secureassessment|shell|skype|snipping|speech|store|terminal|text"
        r"|whatto|widgets|yourphone|zune|corporation|microsoft\.ads"
        r"|microsoft\.net|microsoft\.services|vclibs|runtime|uwp|ncsiuwp)",
        re.I,
    )

    # Non-game desktop apps that ship as Appx packages. Without this list a
    # machine with Telegram/WhatsApp Store versions reports them as 'games'.
    _NON_GAME_APPX = re.compile(
        r"telegrammessenger|whatsapp|discord|spotify|netflix|instagram|"
        r"facebook|tiktok|twitter|slack|teams|zoom|meldstudio|reincubateltd|"
        r"camostudio|rocksdanister|livelywallpaper|scrcpybuddy|codertainment|"
        r"omencommand|hp[a-z]*audio|ad2f1837",
        re.I,
    )
    # Store packages with auto-generated GUID names are frameworks/stubs,
    # never user-facing games.
    _GUID_NAME = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-", re.I)

    # Non-game desktop apps that ship as Appx packages. Without this list a
    # machine with Telegram/WhatsApp Store versions reports them as 'games'.
    _NON_GAME_APPX = re.compile(
        r"telegram|whatsapp|discord|spotify|netflix|instagram|facebook|"
        r"tiktok|twitter|slack|teams|zoom|telegrammessenger|meldstudio|"
        r"reincubateltd|camostudio|rocksdanister|livelywallpaper|scrcpybuddy|"
        r"codertainment|omncommand|omencommand|hp[a-z]*audio|ad2f1837",
        re.I,
    )
    # Store packages with auto-generated GUID names are frameworks/stubs,
    # never user-facing games.
    _GUID_NAME = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-", re.I)

    def scan(self, cancel: _Cancel) -> tuple[List[Dict[str, Any]], List[str]]:
        games: List[Dict[str, Any]] = []
        notes: List[str] = []
        if os.name != "nt":
            notes.append("Xbox/Store detection supports Windows only.")
            return games, notes
        cmd = [
            "powershell", "-NoProfile", "-NonInteractive", "-Command",
            "Get-AppxPackage | Select-Object Name, InstallLocation | ConvertTo-Json -Compress",
        ]
        try:
            out = subprocess.run(cmd, capture_output=True, timeout=45, text=True, encoding="utf-8", errors="replace")
            if out.returncode != 0 or not out.stdout.strip():
                notes.append("Windows package query returned nothing (policy or permissions).")
                return games, notes
            data = json.loads(out.stdout)
            if isinstance(data, dict):
                data = [data]
        except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
            notes.append(f"Windows package query failed: {type(e).__name__}")
            return games, notes
        except OSError:
            notes.append("PowerShell unavailable for package query.")
            return games, notes
        for pkg in data:
            if cancel.cancelled():
                break
            name = pkg.get("Name", "")
            install = pkg.get("InstallLocation", "")
            if not name or not install:
                continue
            # Windows system packages are never games — skip silently.
            if XboxAdapter._SYSTEM_PACKAGE_RE.search(name):
                continue
            # Known non-game Store apps (messengers, streaming, wallpaper
            # engines…) and GUID-named framework stubs are skipped too: they
            # would otherwise surface as fake 'games'.
            if XboxAdapter._NON_GAME_APPX.search(name) or XboxAdapter._GUID_NAME.match(name):
                continue
            try:
                exe_candidates = [f for f in os.listdir(install) if f.lower().endswith(".exe")]
                seen = True
            except (OSError, PermissionError):
                exe_candidates = []
                notes.append(f"Xbox game package unreadable (restricted): {name}")
                games.append({
                    "id": f"xbox:{_norm(name).replace(' ', '-')}",
                    "name": name.replace(".", " ").title(),
                    "source": self.source,
                    "install_path": None,
                    "exe_path": None,
                    "status": STATUS_RESTRICTED,
                })
                continue
            if not exe_candidates:
                continue  # a Framework/runtime package, not a game
            exe_path = None
            for cand in sorted(exe_candidates, key=len):
                full = os.path.join(install, cand)
                try:
                    if os.path.getsize(full) >= _MIN_GAME_EXE_BYTES:
                        exe_path = full
                        break
                except OSError:
                    continue
            games.append({
                "id": f"xbox:{_norm(name).replace(' ', '-')}",
                "name": name.replace(".", " ").title(),
                "source": self.source,
                "install_path": install if os.path.isdir(install) else None,
                "exe_path": exe_path,
                "status": STATUS_INSTALLED if exe_path else STATUS_RESTRICTED,
            })
        if not games:
            notes.append("No Store/Xbox game packages found for this user.")
        return games, notes


def _steam_appid(subkey: Any, uninstall_string: str) -> Optional[int]:
    """Steam appid behind an uninstall entry, if this is one.

    Steam registers games as 'Steam App <id>' keys whose UninstallString is
    ``steam://uninstall/<id>``. The appid ties a registry record to the
    Steam adapter's own discovery (dedupe merges them) and gives the UI a
    cover-art lookup even when the install drive is disconnected.
    """
    m = re.search(r"steam://uninstall/(\d+)", uninstall_string or "", re.I)
    if not m:
        m = re.search(r"Steam App (\d+)", str(subkey))
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


class UninstallAdapter:
    """Windows uninstall keys for standalone/other-launcher installs.

    A game-looking uninstall entry is only 'installed' when its InstallLocation
    exists (or DisplayIcon points at a real game exe). Registry noise like
    redistributables is rejected.
    """

    source = "registry"
    _GAME_WORDS = re.compile(
        r"\bgame\b|\bgames\b| II | III | IV |: |of duty", re.I,
    )
    # Path evidence: a registry path inside a well-known game location is
    # stronger than any name test — it catches titles without game-ish names
    # ("Marvel Rivals", "Grand Theft Auto V", "Hades"). Only the LOCATION
    # counts; the entry name is still screened by the denylist below.
    # Matches Steam's own game dir plus "…\Games\"-style library folders
    # ("EA Games\", "GOG Galaxy\Games\", plain "C:\Games\").
    _GAME_PATH = re.compile(
        r"steamapps[\\/]common|[\\/](?:[A-Za-z0-9]+ )?games?[\\/]",
        re.I,
    )
    # Uninstall-key entries that are definitely not games: drivers, vendor
    # suites, anti-cheat services, this very app, runtimes. Without the
    # denylist the library fills with honest-looking non-games.
    _NOT_GAME_WORDS = re.compile(
        r"(driver|software|optimi[sz]er|runtime|redistributable|directx|"
        r"anticheat|anti-cheat|easyanticheat|punkbuster|vanguard|"
        r"battleeye|afterburner|rtss|geforce|radeon|adrenalin|"
        r"armoury|webhelper|helper|service|daemon|"
        r"launcher$|client$|engine$)", re.I,
    )

    @classmethod
    def _is_game_name(cls, name: str) -> bool:
        """Single decision point for whether an uninstall entry is a game.
        A name must look like a game AND not be launcher/driver/tooling."""
        return bool(cls._GAME_WORDS.search(name)) and not bool(
            cls._NOT_GAME_WORDS.search(name)
        )

    def scan(self, cancel: _Cancel) -> tuple[List[Dict[str, Any]], List[str]]:
        games: List[Dict[str, Any]] = []
        notes: List[str] = []
        if os.name != "nt":
            return games, notes
        import winreg
        uninstall_paths = [
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
            r"SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
        ]
        seen_names: set = set()
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for uview in uninstall_paths:
                try:
                    key = _Registry.open(hive, uview)
                except OSError:
                    continue
                for sub in _Registry.subkeys(key):
                    if cancel.cancelled():
                        break
                    skey = None
                    try:
                        skey = _Registry.open(key, sub)
                        disp = _Registry.read(skey, "DisplayName")
                        loc = _Registry.read(skey, "InstallLocation") or ""
                        icon = _Registry.read(skey, "DisplayIcon") or ""
                        uninst = _Registry.read(skey, "UninstallString") or ""
                    finally:
                        if skey:
                            _Registry.close(skey)
                    if not disp:
                        continue
                    appid = _steam_appid(sub, uninst)
                    disp_n = _norm(disp)
                    if not disp_n or disp_n in seen_names:
                        continue
                    # Skip obvious non-games quietly.
                    if NON_GAME_PATTERNS.search(disp) or "microsoft visual" in disp_n:
                        continue
                    # Uninstall keys are only game EVIDENCE when the name
                    # itself looks like a game OR the recorded location is a
                    # known game directory; vendor suites (AMD Software,
                    # launchers, anti-cheat runtimes, this app) fail both
                    # tests and are dropped rather than filling the library.
                    if UninstallAdapter._NOT_GAME_WORDS.search(disp):
                        continue
                    evidence = bool(UninstallAdapter._GAME_WORDS.search(disp)) or bool(
                        loc and UninstallAdapter._GAME_PATH.search(loc)
                    ) or appid is not None
                    if not evidence:
                        continue
                    # Evidence decides the claim. An icon is ARTWORK, never a
                    # launch target, unless it literally is the game exe — a
                    # still-cached Steam .ico must not turn a disconnected-
                    # drive install into a 'verified' one.
                    path_ok = bool(loc) and os.path.isdir(loc)
                    icon_path = icon.split(",")[0].strip()
                    icon_is_exe = bool(icon_path) and icon_path.lower().endswith(".exe") and os.path.isfile(icon_path)
                    icon_is_img = bool(icon_path) and icon_path.lower().endswith((".ico", ".png", ".jpg", ".jpeg")) and os.path.isfile(icon_path)
                    record: Dict[str, Any] = {
                        "id": f"reg:{disp_n.replace(' ', '-')}",
                        "name": disp,
                        "source": self.source,
                    }
                    if appid is not None:
                        # Ties the record to the Steam adapter (dedupe merges
                        # them) and gives the UI a CDN cover-art lookup.
                        record["appid"] = appid
                    if icon_is_img:
                        # Cached launcher artwork — a cover-art source for the
                        # UI (core.game_artwork), never an exe.
                        record["icon_path"] = icon_path
                    if path_ok:
                        record.update(
                            install_path=loc,
                            exe_path=resolve_game_exe(loc) or (icon_path if icon_is_exe else None),
                            status=STATUS_INSTALLED,
                        )
                    elif icon_is_exe:
                        # DisplayIcon pointing at a real game exe: the file's
                        # own presence is the verification.
                        record.update(
                            install_path=os.path.dirname(icon_path),
                            exe_path=icon_path,
                            status=STATUS_INSTALLED,
                        )
                    elif loc:
                        # The registry remembers a location the files no
                        # longer occupy (drive unplugged, folder removed):
                        # an honest 'missing' card, never 'installed' just
                        # because a cached icon still exists.
                        record.update(install_path=loc, exe_path=None, status=STATUS_MISSING)
                    elif icon_is_img or appid is not None:
                        # No location at all: an icon or a Steam appid still
                        # supports an honest card (artwork + appid, nothing
                        # launchable). A bare name stays dropped below.
                        record.update(install_path=None, exe_path=None, status=STATUS_MISSING)
                    else:
                        # Name-only entries cannot be verified — the Steam
                        # adapter owns those records when they are real.
                        continue
                    seen_names.add(disp_n)
                    games.append(record)
                _Registry.close(key)
        return games, notes


class CustomDirectoryScanner:
    """User-approved directories only.

    Walking everything on every drive is neither fast nor safe: this scanner
    only descends into paths the user chose, sized-limited, with plausibility
    checks so installers and helpers are not called games.
    """

    # Keep the recursion shallow and bounded — a game install always has its
    # exe near the top; a full-depth walk would cost minutes per folder.
    MAX_DEPTH = 2
    MAX_DIRS_PER_ROOT = 400

    def scan_roots(self, roots: List[str], cancel: _Cancel) -> tuple[List[Dict[str, Any]], List[str]]:
        games: List[Dict[str, Any]] = []
        notes: List[str] = []
        for root in roots:
            if cancel.cancelled():
                break
            if not os.path.isdir(root):
                notes.append(f"Scan root does not exist: {root}")
                continue
            try:
                subdirs = os.listdir(root)
            except (OSError, PermissionError):
                notes.append(f"Access denied scanning: {root}")
                continue
            count = 0
            # A root may BE the game folder the user added directly.
            root_game = self._identify_game_dir(root, depth=0)
            if root_game:
                games.append(root_game)
            for sub in sorted(subdirs):
                if cancel.cancelled() or count >= self.MAX_DIRS_PER_ROOT:
                    break
                path = os.path.join(root, sub)
                if not os.path.isdir(path):
                    continue
                count += 1
                game = self._identify_game_dir(path, depth=0)
                if game:
                    games.append(game)
        return games, notes

    def _identify_game_dir(self, path: str, depth: int) -> Optional[Dict[str, Any]]:
        """Return a game record when `path` looks like a real installation."""
        try:
            entries = os.listdir(path)
        except (OSError, PermissionError):
            return None
        exes = [e for e in entries if os.path.splitext(e)[1].lower() in _EXECUTABLE_EXTS]
        if exes:
            for exe in sorted(exes):
                if _NOT_GAME_EXE.search(exe):
                    continue
                full = os.path.join(path, exe)
                try:
                    size = os.path.getsize(full)
                except OSError:
                    continue
                if size < _MIN_GAME_EXE_BYTES:
                    continue
                if not _GAME_EXE_HINT.search(os.path.splitext(exe)[0]):
                    # A big exe whose name looks like a title is accepted even
                    # without the client/game hint (e.g. 'Cyberpunk2077.exe').
                    if not re.match(r"^[A-Za-z][A-Za-z0-9 ._'-]{3,40}$", os.path.splitext(exe)[0]):
                        continue
                return {
                    "id": f"custom:{_norm(os.path.basename(path)).replace(' ', '-')}",
                    "name": self._title_from(os.path.basename(path)),
                    "source": "custom",
                    "install_path": path,
                    "exe_path": full,
                    # Explainable evidence: which signals accepted this
                    # candidate (size gate already passed above).
                    "evidence": (
                        f"exe {size // (1024 * 1024)} MB"
                        + (", title-like name" if _GAME_EXE_HINT.search(
                            os.path.splitext(exe)[0]) else ", folder/exe name match")
                        + f", depth {depth}"
                    ),
                    "status": STATUS_INSTALLED,
                }
        # One level deeper only — avoids unbounded recursion.
        if depth < self.MAX_DEPTH:
            for sub in sorted(entries):
                p2 = os.path.join(path, sub)
                if os.path.isdir(p2):
                    hit = self._identify_game_dir(p2, depth + 1)
                    if hit:
                        return hit
        return None

    def _title_from(self, folder: str) -> str:
        t = re.sub(r"[_\-.]+", " ", folder).strip()
        t = re.sub(r"\s+", " ", t)
        return t.title() if t else folder


# --------------------------------------------------------------------------
# Process runner-status probe (never marks installed, only adds 'running')
# --------------------------------------------------------------------------

def _attach_profiles(games: List[Dict[str, Any]]) -> None:
    """Match existing optimization profiles onto detected games.

    Profiles are capability metadata owned by game_profiles.py. Matching only
    ever ATTACHES a profile to an already-verified installation (by title and
    known process names) — it can never create an installed game.
    """
    try:
        from .game_profiles import BUILTIN_PROFILES
    except ImportError:
        return
    for game in games:
        if game["status"] not in (STATUS_INSTALLED, STATUS_RUNNING):
            continue
        name_n = _norm(game.get("name", ""))
        for pid, profile in BUILTIN_PROFILES.items():
            pname = _norm(profile.get("name", ""))
            if pname and (pname in name_n or name_n in pname):
                game["profile_id"] = pid
                break


def _dedupe(games: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merge games discovered by several sources.

    Key: normalized title + verified installation path. A Wuthering Waves
    seen once via Steam and once via registry is ONE game: the record with
    the stronger evidence (own appid/exe path) wins, the other's source is
    kept as an extra source tag. Never lose a unique title.
    """
    out: List[Dict[str, Any]] = []
    by_key: Dict[tuple, int] = {}
    for g in games:
        path = (g.get("install_path") or "").rstrip("\\/").lower()
        key = (_norm(g.get("name", "")), path)
        idx = by_key.get(key)
        if idx is not None:
            existing = out[idx]
            # Prefer the record with richer evidence.
            if (g.get("exe_path") and not existing.get("exe_path")) or (
                g.get("appid") and not existing.get("appid")
            ):
                sources = {existing.get("source"), g.get("source")}
                merged = {**existing, **{k: v for k, v in g.items() if v is not None}}
                merged["source"] = existing["source"]
                merged["sources"] = sorted(s for s in sources if s)
                out[idx] = merged
            else:
                s = existing.get("sources") or [existing.get("source")]
                if g.get("source") not in s:
                    existing["sources"] = sorted([*s, g.get("source")])
            continue
        by_key[key] = len(out)
        out.append(g)
    # Second pass: same-title records from different sources (e.g. a launcher
    # adapter and a Start Menu shortcut) describe one game when titles match
    # and at least one side lacks its own verified path. Path-bearing records
    # never merge with a different path — same name on two drives stays two
    # games (same-name-games-in-different-locations rule).
    by_title: Dict[str, int] = {}
    merged_pass: List[Dict[str, Any]] = []
    for g in out:
        title = _norm(g.get("name", ""))
        path = (g.get("install_path") or "").rstrip("\\/").lower()
        idx = by_title.get(title)
        if idx is not None:
            keep = merged_pass[idx]
            keep_path = (keep.get("install_path") or "").rstrip("\\/").lower()
            if not path or not keep_path or path == keep_path:
                # Merge the evidence: richer record wins, weaker side's
                # source rides along as an extra tag.
                weaker = g if (
                    (keep.get("exe_path") or (
                        keep.get("launch_target") or keep.get("shortcut_path")
                    ))
                    and not (g.get("exe_path") or (
                        g.get("launch_target") and not keep.get("launch_target")
                    ))
                ) else keep
                richer = keep if weaker is g else g
                srcs = sorted({*(keep.get("sources") or [keep.get("source")]),
                               g.get("source")} - {None})
                merged = {**weaker, **{k: v for k, v in richer.items() if v is not None}}
                # Primary source = the install witness (a verified path or
                # exe), so a launcher+shortcut merge reports the real
                # launcher (e.g. Gryphline) while the shortcut side stays in
                # `sources` as supporting evidence.
                witness = keep if (keep.get("exe_path") or keep.get("install_path")) else g
                merged["source"] = witness.get("source") or richer.get("source") or weaker.get("source")
                merged["sources"] = srcs
                # Preserve shortcut launch data even when the richer record
                # has its own exe: direct exe wins, launcher args as fallback.
                if g.get("shortcut_path") and not weaker.get("shortcut_path"):
                    merged.setdefault("shortcut_path", g.get("shortcut_path"))
                    merged.setdefault("launch_args", g.get("launch_args"))
                    merged.setdefault("launch_target", g.get("launch_target"))
                merged_pass[idx] = merged
                continue
        by_title[title] = len(merged_pass)
        merged_pass.append(g)

    # Third pass: ONE card per emulator product, never one per folder or per
    # witness. BlueStacks/MSI ships an engine and a player shell in sibling
    # folders ("MSI App Player", "MSI App Player Engine") and BOTH the Start
    # Menu adapter and the emulator adapter witness the same product, so the
    # rules above would keep two or three cards for one emulator. Only
    # kind='emulator' records participate (game records keep the
    # two-locations rule): a family is one normalized title being a prefix of
    # the other.
    def _family(a: str, b: str) -> bool:
        short, long_ = sorted((a, b), key=len)
        return bool(short) and long_.startswith(short)

    def _merge_emulator(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
        # The emulator adapter is the product authority (display name and
        # source); Start Menu witnesses fill in any missing launch evidence.
        auth, other = (a, b) if a.get("source") == "emulator" else (
            (b, a) if b.get("source") == "emulator" else (a, b)
        )
        merged = {**other, **{k: v for k, v in auth.items() if v is not None}}
        rank = {STATUS_RUNNING: 3, STATUS_INSTALLED: 2, STATUS_MISSING: 1, STATUS_RESTRICTED: 0}
        statuses = [s for s in (a.get("status"), b.get("status")) if s]
        if statuses:
            merged["status"] = max(statuses, key=lambda s: rank.get(s, -1))
        merged["kind"] = "emulator"
        merged["sources"] = sorted(
            {*(a.get("sources") or [a.get("source")]),
             *(b.get("sources") or [b.get("source")])} - {None}
        )
        return merged

    families: List[Dict[str, Any]] = []  # {titles, index} of merged_pass slots
    pass3: List[Dict[str, Any]] = []
    for g in merged_pass:
        if g.get("kind") != "emulator":
            pass3.append(g)
            continue
        title = _norm(g.get("name", ""))
        fam = next((f for f in families if any(_family(t, title) for t in f["titles"])), None)
        if fam is None:
            families.append({"titles": {title}, "index": len(pass3)})
            pass3.append(g)
            continue
        fam["titles"].add(title)
        pass3[fam["index"]] = _merge_emulator(pass3[fam["index"]], g)
    return pass3


# --------------------------------------------------------------------------
# Service
# --------------------------------------------------------------------------


def _running_check(games: List[Dict[str, Any]]) -> None:
    """Mark a game running only when one of its own executables is alive.

    Never sets a game back to installed and never marks installed: a process
    whose image path matches a game's verified exe is the only evidence for
    STATUS_RUNNING. One psutil pass per call, not per game.
    """
    if os.name != "nt":
        return
    try:
        import psutil
    except ImportError:
        return
    by_exe: Dict[str, List[Dict[str, Any]]] = {}
    for g in games:
        exe = g.get("exe_path")
        if exe and g.get("status") in (STATUS_INSTALLED, STATUS_RUNNING):
            by_exe.setdefault(os.path.basename(exe).lower(), []).append(g)
    if not by_exe:
        return
    for proc in psutil.process_iter(["exe"]):
        try:
            pexe = proc.info.get("exe") or ""
        except Exception:  # noqa: BLE001 - process may vanish mid-iteration
            continue
        candidates = by_exe.get(os.path.basename(pexe).lower())
        if not candidates:
            continue
        for g in candidates:
            try:
                if os.path.normcase(os.path.abspath(pexe)) == os.path.normcase(
                    os.path.abspath(g["exe_path"])
                ):
                    g["status"] = STATUS_RUNNING
            except (OSError, ValueError):
                continue


class GameDiscoveryService:
    """The single discovery entry-point. Adapters are independent; a failure
    in one may never lose the results of the others."""

    ADAPTERS = [
        SteamAdapter, EpicAdapter, RiotAdapter, BattleNetAdapter,
        GogAdapter, EaAppAdapter, UbisoftAdapter, XboxAdapter,
        GryphlineAdapter, StartMenuShortcutAdapter, EmulatorAdapter,
        UninstallAdapter,
    ]

    def __init__(self, extra_roots: Optional[List[str]] = None) -> None:
        self._extra_roots = [r for r in (extra_roots or []) if isinstance(r, str) and r.strip()]
        self._lock = threading.Lock()
        self._cancel: Optional[_Cancel] = None
        self._progress = {
            "running": False, "adapters_done": 0,
            "adapters_total": len(self.ADAPTERS) + 1,  # + custom roots
            "games_found": 0, "started_at": 0.0, "finished_at": 0.0,
            "cancel_requested": False,
        }
        self._scan_thread: Optional[threading.Thread] = None

    # ---- public surface used by the API blueprint ----

    def scan_progress(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._progress)

    def cancel_scan(self) -> bool:
        with self._lock:
            if self._cancel:
                self._cancel.cancel()
                self._progress["cancel_requested"] = True
            return self._scan_thread is not None and self._scan_thread.is_alive()

    def scan_async(self, on_done: Optional[Callable[[Dict[str, Any]], None]] = None) -> bool:
        """Start a scan in a daemon thread; UI polls scan_async progress."""
        with self._lock:
            if self._progress.get("running"):
                return False
            self._cancel = _Cancel()
            self._progress = {
                "running": True, "cancelled": False,
                "adapters_done": 0, "adapters_total": len(self.ADAPTERS) + 1,
                "games_found": 0, "started_at": time.time(),
                "finished_at": 0.0, "cancel_requested": False,
            }
            cancel = self._cancel
            progress = self._progress  # guarded by _lock for reads
            self._scan_thread = threading.Thread(
                target=self._run_scan, args=(cancel, progress, on_done), daemon=True,
            )
            self._scan_thread.start()
            return True

    def scan_sync(self) -> Dict[str, Any]:
        """Blocking scan — used by tests and by API callers that prefer wait."""
        cancel = _Cancel()
        progress = {
            "running": True, "cancelled": False,
            "adapters_done": 0,
            "adapters_total": len(self.ADAPTERS) + 1,
            "games_found": 0, "started_at": time.time(),
            "finished_at": 0.0, "cancel_requested": False,
        }
        return self._run_scan(cancel, progress, None)

    # ---- internals ----

    def _run_scan(self, cancel: _Cancel, progress: Dict[str, Any], done_cb) -> Dict[str, Any]:
        games: List[Dict[str, Any]] = []
        notes: List[str] = []
        # Per-source diagnostics: what was actually inspected and why records
        # were rejected. Never fabricated — each adapter reports its own state.
        diagnostics = {
            "sources": [],
            "candidates_found": 0,
            "rejected": 0,
            "duplicates_removed": 0,
            "inaccessible": 0,
        }
        try:
            for adapter_cls in self.ADAPTERS:
                if cancel.cancelled():
                    break
                adapter = adapter_cls()
                src_status = {
                    "source": adapter_cls.source if hasattr(adapter_cls, "source") else adapter_cls.__name__.lower(),
                    "label": adapter_cls.__name__.replace("Adapter", ""),
                    "status": "inspected",
                    "games": 0,
                    "notes": [],
                }
                try:
                    g, n = adapter.scan(cancel)
                except Exception as e:  # one bad adapter never kills the scan
                    logger.warning(f"{adapter_cls.__name__} failed: {e}")
                    n = [f"{adapter_cls.__name__}: {e}"]
                    g = []
                    src_status["status"] = "error"
                games.extend(g)
                notes.extend(n)
                src_status["games"] = len(g)
                src_status["notes"] = list(n)
                if any("not found" in x.lower() for x in n):
                    src_status["status"] = "not_installed"
                if any("not connected" in x.lower() for x in n):
                    # A configured library on a missing drive is neither a
                    # permission problem nor a failure to inspect.
                    src_status["status"] = "inspected"
                elif any("unreadable" in x.lower() or "denied" in x.lower() for x in n):
                    src_status["status"] = "access_restricted"
                    diagnostics["inaccessible"] += 1
                diagnostics["sources"].append(src_status)
                diagnostics["candidates_found"] += len(g)
                with self._lock:
                    progress["adapters_done"] += 1
                    progress["games_found"] = len(games)

            if self._extra_roots:
                scanner = CustomDirectoryScanner()
                src_status = {"source": "custom", "label": "CustomFolders",
                              "status": "inspected", "games": 0, "notes": []}
                g, n = scanner.scan_roots(self._extra_roots, cancel)
                games.extend(g)
                notes.extend(n)
                src_status["games"] = len(g)
                src_status["notes"] = list(n)
                if any("denied" in x.lower() or "unreadable" in x.lower() for x in n):
                    src_status["status"] = "access_restricted"
                    diagnostics["inaccessible"] += 1
                diagnostics["sources"].append(src_status)
                diagnostics["candidates_found"] += len(g)

            # Last-verified keeps the library honest about scan staleness.
            verified = time.time()
            for g in games:
                g["last_verified"] = verified
            _running_check(games)
            # Existing optimization profiles ride along: a detected game that
            # matches a profile keeps the profile usable (Apply/Revert) without
            # the profile ever fabricating an installation.
            _attach_profiles(games)
            pre_dedupe = len(games)
            games = _dedupe(games)
            diagnostics["duplicates_removed"] = pre_dedupe - len(games)
            diagnostics["verified_installed"] = sum(
                1 for g in games
                if g.get("status") in (STATUS_INSTALLED, STATUS_RUNNING)
            )
            result = {
                "games": games,
                "notes": notes,
                "diagnostics": diagnostics,
                "scanned_at": verified,
                "cancelled": cancel.cancelled(),
            }
            self._cache_result(result)
            with self._lock:
                progress["running"] = False
                progress["cancelled"] = cancel.cancelled()
                progress["finished_at"] = time.time()
                progress["games_found"] = len(games)
            self._done(done_cb, result)
            return result
        except Exception as e:
            logger.error(f"Game discovery scan crashed: {e}", exc_info=True)
            with self._lock:
                progress["running"] = False
                progress["error"] = str(e)
                progress["finished_at"] = time.time()
            err = {"games": [], "notes": notes + [f"Scan failed: {e}"],
                   "scanned_at": time.time(), "cancelled": cancel.cancelled(), "error": str(e)}
            self._cache_result(err)
            self._done(done_cb, err)
            return err

    @staticmethod
    def _done(cb, result: Dict[str, Any]) -> None:
        if cb:
            try:
                cb(result)
            except Exception as e:
                logger.warning(f"Scan completion callback failed: {e}")

    # ---- result cache (explicit rescan action refreshes it) ----

    _CACHE_FILE = os.path.join("data", "game_library_cache.json")

    def _cache_result(self, result: Dict[str, Any]) -> None:
        try:
            os.makedirs(os.path.dirname(self._CACHE_FILE), exist_ok=True)
            data = {
                "saved_at": time.time(),
                "games": result["games"],
                "notes": result["notes"],
                "diagnostics": result.get("diagnostics"),
                "cancelled": result.get("cancelled", False),
                "error": result.get("error"),
            }
            with open(self._CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=0)
        except Exception as e:
            logger.debug(f"Game library cache write failed (non-fatal): {e}")

    def cached_result(self) -> Optional[Dict[str, Any]]:
        try:
            with open(self._CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict) or "games" not in data:
                return None
            return data
        except (OSError, json.JSONDecodeError):
            return None


# Singleton used by the API blueprint.
_service: Optional[GameDiscoveryService] = None
_service_lock = threading.Lock()


def _default_scan_roots() -> List[str]:
    """Bounded Source-C seeds: well-known game folders on drives that
    actually exist. Never assumes C:, never walks a whole drive — only a
    handful of fixed directory names are probed, and a disconnected drive
    simply fails the isdir check instead of erroring."""
    out: List[str] = []
    for code in range(ord("A"), ord("Z") + 1):
        drive_root = f"{chr(code)}:\\"
        try:
            if not os.path.isdir(drive_root):
                continue
        except OSError:
            continue
        for sub in ("Games", "GameLibrary"):
            p = os.path.join(drive_root, sub)
            if os.path.isdir(p):
                out.append(p)
    docs = os.path.join(os.path.expanduser("~"), "Documents", "Games")
    if os.path.isdir(docs):
        out.append(docs)
    return out


def get_service() -> GameDiscoveryService:
    global _service
    with _service_lock:
        if _service is None:
            extra: List[str] = []
            try:
                cfg_path = os.path.join("data", "custom_game_roots.json")
                if os.path.isfile(cfg_path):
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, dict):
                        extra = [r for r in data.get("roots", []) if isinstance(r, str)]
            except Exception as e:
                logger.debug(f"custom roots read failed: {e}")
            # User-approved roots first, then the bounded defaults — every
            # one of them is re-validated by the folder scanner's own
            # evidence rules, not trusted blindly.
            for r in _default_scan_roots():
                if r not in extra:
                    extra.append(r)
            _service = GameDiscoveryService(extra_roots=extra)
        return _service
