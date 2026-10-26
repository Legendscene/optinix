"""Installed games scanner — which optimization profiles map to games actually on this PC.

Installation is only reported when the installation itself can be verified:

- Steam: libraryfolders.vdf -> appmanifest_*.acf. The manifest must say the
  title is fully installed (StateFlags bit 4) and its `installdir` folder must
  exist and be non-empty. A stale manifest is a `missing` record, not a game.
- Windows "programs installed" registry keys: the uninstall record must point
  at an install path (InstallLocation / DisplayIcon / UninstallString) that
  still exists. A name-only record is a `candidate`; a record whose path has
  disappeared is `missing`. Neither is ever reported as installed.

A profile is reported installed only when its title matches a *verified*
record; an empty scan is a valid answer, never filled from the profile list.
"""
import os
import re
import stat
from typing import Any, Dict, List, Optional, Tuple

from .logger import get_logger

logger = get_logger("installed_games")

# Explicit states. Only VERIFIED may be shown to the user as "installed".
STATUS_VERIFIED = "verified_installed"
STATUS_CANDIDATE = "candidate"
STATUS_MISSING = "missing"
STATUS_UNKNOWN = "unknown"

VERIFIED_STATUSES = (STATUS_VERIFIED,)
# Dedupe preference: verified evidence must always win a duplicate title, and
# an unreadable path says more than no path at all. Lower rank is kept.
_EVIDENCE_RANK = {
    STATUS_VERIFIED: 0,
    STATUS_UNKNOWN: 1,
    STATUS_MISSING: 2,
    STATUS_CANDIDATE: 3,
}

# Cover art fallback for Steam-distributed titles matched outside a Steam
# library scan (registry hits). Public appids, used only when the game really
# is installed via its store's registry entry.
STEAM_APPID_FALLBACK: Dict[str, int] = {
    "counter-strike 2": 730,
    "call of duty: warzone": 1938090,
    "dota 2": 570,
    "pubg: battlegrounds": 578080,
    "rust": 252490,
    "apex legends": 1172470,
    "cyberpunk 2077": 1091500,
    "elden ring": 1245620,
    "grand theft auto v": 271590,
    "rainbow six siege": 359550,
}

DEFAULT_STEAM_ROOT = r"C:\Program Files (x86)\Steam"


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _tokens(text: str) -> set:
    """Comparable words; trademarks and punctuation carry no identity."""
    return set(re.findall(r"[a-z0-9]+", _norm(text)))


def _steam_library_paths(root: str) -> List[str]:
    """Read libraryfolders.vdf; the Steam default root is always included."""
    paths = [root]
    try:
        with open(os.path.join(root, "steamapps", "libraryfolders.vdf"), "r") as f:
            for m in re.finditer(r'"path"\s+"((?:\\\\.|[^"])*)"', f.read()):
                raw = m.group(1).replace("\\\\", "\\")
                paths.append(raw)
    except OSError:
        pass
    seen: set = set()
    out = []
    for p in paths:
        p = p.rstrip("\\/")
        if p and p not in seen:
            seen.add(p)
            out.append(p)
    return out


def _verify_path(path: Optional[str], want_dir: bool) -> Tuple[str, str]:
    """Classify an install path against the filesystem.

    Returns (status, human reason). Never raises: an inaccessible path is
    `unknown`, which is not treated as installed.
    """
    if not path:
        return STATUS_CANDIDATE, "The install record has no path to verify."
    try:
        st = os.stat(path)
    except FileNotFoundError:
        return STATUS_MISSING, f"The recorded install path no longer exists ({path})."
    except OSError as e:
        return STATUS_UNKNOWN, f"The recorded install path could not be read ({path}): {e}"

    if want_dir:
        if not stat.S_ISDIR(st.st_mode):
            return STATUS_MISSING, f"The recorded install path is not a folder ({path})."
        try:
            with os.scandir(path) as it:
                empty = next(it, None) is None
        except OSError as e:
            return STATUS_UNKNOWN, f"The install folder could not be listed ({path}): {e}"
        if empty:
            return STATUS_MISSING, f"The recorded install folder is empty ({path})."
        return STATUS_VERIFIED, f"Install folder present and populated ({path})."

    if not stat.S_ISREG(st.st_mode):
        return STATUS_MISSING, f"The recorded executable is not a file ({path})."
    return STATUS_VERIFIED, f"Executable present ({path})."


def _steam_games(steam_root: str) -> List[Dict[str, Any]]:
    """Every game Steam records, with its install folder verified."""
    games: List[Dict[str, Any]] = []
    for lib in _steam_library_paths(steam_root):
        steamapps = os.path.join(lib, "steamapps")
        try:
            entries = os.listdir(steamapps)
        except OSError:
            continue
        for f in entries:
            m = re.match(r"appmanifest_(\d+)\.acf$", f)
            if not m:
                continue
            try:
                with open(os.path.join(steamapps, f), "r", encoding="utf-8", errors="replace") as fp:
                    text = fp.read()
            except OSError:
                continue
            name_m = re.search(r'"name"\s+"([^"]*)"', text)
            if not name_m or not name_m.group(1):
                continue
            dir_m = re.search(r'"installdir"\s+"([^"]*)"', text)
            installdir = dir_m.group(1).strip() if dir_m else ""
            state_m = re.search(r'"StateFlags"\s+"(\d+)"', text)
            state = int(state_m.group(1)) if state_m else None

            install_path = os.path.join(steamapps, "common", installdir) if installdir else None
            if state is not None and not (state & 4):
                status, reason = STATUS_MISSING, "Steam reports this title is not fully installed."
            else:
                status, reason = _verify_path(install_path, want_dir=True)
            games.append({
                "name": name_m.group(1),
                "appid": int(m.group(1)),
                "source": "steam",
                "install_path": install_path,
                "status": status,
                "reason": reason,
            })
    return games


def _reg_value(skey, name: str) -> str:
    import winreg
    try:
        value, _ = winreg.QueryValueEx(skey, name)
        return str(value or "").strip()
    except OSError:
        return ""


def _clean_path(raw: str) -> str:
    """Strip quotes, a DisplayIcon ',0' suffix and stray arguments."""
    text = (raw or "").strip()
    if not text:
        return ""
    if text[0] in "\"'":
        quote = text[0]
        end = text.find(quote, 1)
        text = text[1:end] if end > 0 else text[1:]
    else:
        text = re.split(r"\s+", text, maxsplit=1)[0]
    text = re.sub(r",\s*-?\d+$", "", text).strip().strip('"')
    return os.path.expandvars(text)


def _registry_install_path(install: str, icon: str, uninstall: str) -> Tuple[str, bool]:
    """First usable path from the record: folder, icon target, uninstaller."""
    location = _clean_path(install)
    if location:
        return location, True
    icon_path = _clean_path(icon)
    if icon_path:
        return icon_path, False
    uninstaller = _clean_path(uninstall)
    if uninstaller:
        return uninstaller, False
    return "", True


def _registry_games() -> List[Dict[str, Any]]:
    """Install records from the Windows uninstall keys, each one verified."""
    if os.name != "nt":
        return []
    import winreg

    roots = [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]
    views = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    ]
    out: List[Dict[str, Any]] = []
    try:
        for hive in roots:
            for view in views:
                try:
                    key = winreg.OpenKey(hive, view)
                except OSError:
                    continue
                try:
                    i = 0
                    while True:
                        try:
                            sub = winreg.EnumKey(key, i)
                        except OSError:
                            break
                        i += 1
                        try:
                            skey = winreg.OpenKey(key, sub)
                        except OSError:
                            continue
                        try:
                            display = _reg_value(skey, "DisplayName")
                            if not display:
                                continue
                            install = _reg_value(skey, "InstallLocation")
                            icon = _reg_value(skey, "DisplayIcon")
                            uninstall = _reg_value(skey, "UninstallString")
                            path, want_dir = _registry_install_path(install, icon, uninstall)
                            status, reason = _verify_path(path, want_dir)
                            out.append({
                                "name": display,
                                "appid": None,
                                "source": "registry",
                                "install_path": path or None,
                                "status": status,
                                "reason": reason,
                            })
                        finally:
                            winreg.CloseKey(skey)
                finally:
                    winreg.CloseKey(key)
    except Exception as e:  # noqa: BLE001 - registry access is best effort
        logger.warning(f"Uninstall registry scan failed: {e}")
    return _dedupe_registry(out)


def _dedupe_registry(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """One record per title, keeping the best-verified copy."""
    by_name: Dict[str, Dict[str, Any]] = {}
    for entry in entries:
        key = _norm(entry["name"])
        previous = by_name.get(key)
        rank = _EVIDENCE_RANK.get(entry["status"], 9)
        if previous is None or rank < _EVIDENCE_RANK.get(previous["status"], 9):
            by_name[key] = entry
    return list(by_name.values())


# Steam-library noise that is not a game; used only to keep the
# "installed, no profile yet" list honest instead of noisy.
NON_GAME_PATTERNS = re.compile(
    r"redistributables|directx|visual c\+\+|runtime|dota 2 workshop|\bproton\b|steamworks",
    re.I,
)


def _matches(profile: Dict[str, Any], names: List[str]) -> bool:
    """Match on the title's own words, never on a loose substring.

    Every significant word of the profile title must be present in the
    installed title (so "Tom Clancy's Rainbow Six Siege" matches Rainbow Six
    Siege), while a record missing a distinguishing word does not ("Call of
    Duty" alone is not Warzone). Short titles must match exactly, and an id
    only counts as a whole word of at least four characters.
    """
    title_tokens = _tokens(profile.get("name", ""))
    ident = _norm(profile.get("id", ""))
    if not title_tokens and not ident:
        return False
    for n in names:
        tokens = _tokens(n)
        if title_tokens:
            if title_tokens == tokens:
                return True
            if len(title_tokens) >= 3 and title_tokens <= tokens:
                return True
        if ident and len(ident) >= 4 and re.search(rf"\b{re.escape(ident)}\b", n):
            return True
    return False


def scan_installed_games(profiles: List[Dict[str, Any]], steam_root: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
    """Match verified install evidence against optimization profiles.

    Returns three sets:
      matched:    { profile_id, status: verified_installed, evidence, ... }
                  — a profile exists and the game really is installed.
      others:     { name, source, appid? } — verified install, no profile yet.
      unverified: { profile_id, name, status, reason, ... } — a record matched
                  a profile but its installation could not be verified. These
                  are for diagnostics/browsing and must not be shown as games.
    """
    if not profiles:
        return {"matched": [], "others": [], "unverified": []}
    if not steam_root:
        # The Windows default; real Steam installs may live elsewhere but the
        # uninstall registry still catches those games.
        steam_root = DEFAULT_STEAM_ROOT

    matched: List[Dict[str, Any]] = []
    matched_ids: set = set()
    others: List[Dict[str, Any]] = []
    other_names: set = set()
    unverified: List[Dict[str, Any]] = []
    unverified_ids: set = set()

    # Verified evidence first, so a stale duplicate can never shadow it.
    evidence = _steam_games(steam_root) + _registry_games()
    evidence.sort(key=lambda g: 0 if g.get("status") == STATUS_VERIFIED else 1)

    for game in evidence:
        names = [_norm(game["name"])]
        status = game.get("status") or STATUS_UNKNOWN
        reason = game.get("reason") or "Installation could not be verified."
        profile_hits = [p for p in profiles if _matches(p, names)]

        if profile_hits:
            for p in profile_hits:
                pid = p.get("id")
                if not pid:
                    continue
                appid = game.get("appid") or STEAM_APPID_FALLBACK.get(_norm(p.get("name", "")))
                entry: Dict[str, Any] = {
                    "profile_id": pid,
                    "name": game["name"],
                    "source": game["source"],
                    "status": status,
                }
                if game.get("install_path"):
                    entry["install_path"] = game["install_path"]
                if appid:
                    entry["appid"] = appid

                if status in VERIFIED_STATUSES:
                    if pid in matched_ids:
                        continue
                    matched_ids.add(pid)
                    entry["evidence"] = reason
                    matched.append(entry)
                elif pid not in unverified_ids:
                    unverified_ids.add(pid)
                    entry["reason"] = reason
                    unverified.append(entry)
            continue

        # Anything else that is a verified Steam install is an installed game
        # the profile list does not cover — surface it rather than hiding it.
        if status in VERIFIED_STATUSES and game["source"] == "steam" and not NON_GAME_PATTERNS.search(game["name"]):
            label = game["name"]
            if label.lower() not in other_names:
                other_names.add(label.lower())
                o: Dict[str, Any] = {"name": label, "source": game["source"], "status": status}
                if game.get("appid"):
                    o["appid"] = game["appid"]
                others.append(o)

    logger.info(
        f"Installed-games scan: {len(matched)} verified profiles, "
        f"{len(unverified)} unverified records, {len(others)} profileless installs"
    )
    return {"matched": matched, "others": others, "unverified": unverified}
