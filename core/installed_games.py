"""Installed games scanner — which optimization profiles map to games actually on this PC.

Two honest sources, nothing invented:
- Steam installs: libraryfolders.vdf -> appmanifest_*.acf (gives the real appid,
  which is also the key for cover art).
- Windows "programs installed" registry keys for everything else (Riot, Epic,
  Battle.net, GOG, standalone installers).

A profile is reported installed only when its name (or id token) matches a real
entry; an empty scan is a valid answer, never filled from the profile list.
"""
import os
import re
from typing import Any, Dict, List, Optional

from .logger import get_logger

logger = get_logger("installed_games")

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


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


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


def _steam_games(steam_root: str) -> List[Dict[str, Any]]:
    """Every installed game known to Steam: {name, appid, source}."""
    games: List[Dict[str, Any]] = []
    for lib in _steam_library_paths(steam_root):
        try:
            for f in os.listdir(os.path.join(lib, "steamapps")):
                m = re.match(r"appmanifest_(\d+)\.acf$", f)
                if not m:
                    continue
                try:
                    with open(os.path.join(lib, "steamapps", f), "r", encoding="utf-8", errors="replace") as fp:
                        text = fp.read()
                except OSError:
                    continue
                name_m = re.search(r'"name"\s+"([^"]*)"', text)
                if name_m and name_m.group(1):
                    games.append({"name": name_m.group(1), "appid": int(m.group(1)), "source": "steam"})
        except OSError:
            continue
    return games


def _registry_games() -> List[Dict[str, Any]]:
    """Display names from the Windows uninstall keys (all three views)."""
    if os.name != "nt":
        return []
    import winreg

    views = ["SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall"]
    out: List[Dict[str, Any]] = []
    seen: set = set()
    try:
        roots = [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]
        for hive in roots:
            for view in views:
                for wow in [view, "SOFTWARE\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall"]:
                    try:
                        key = winreg.OpenKey(hive, wow)
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
                                display, _ = winreg.QueryValueEx(skey, "DisplayName")
                                winreg.CloseKey(skey)
                                disp = _norm(display)
                                if disp and disp not in seen:
                                    seen.add(disp)
                                    out.append({"name": display, "appid": None, "source": "registry"})
                            except OSError:
                                continue
                    finally:
                        winreg.CloseKey(key)
    except Exception as e:
        logger.warning(f"Uninstall registry scan failed: {e}")
    return out


# Steam-library noise that is not a game; used only to keep the
# "installed, no profile yet" list honest instead of noisy.
NON_GAME_PATTERNS = re.compile(
    r"redistributables|directx|visual c\+\+|runtime|dota 2 workshop|\bproton\b|steamworks",
    re.I,
)


def _matches(profile: Dict[str, Any], names: List[str]) -> bool:
    """A profile matches when its display name appears inside an installed title,
    or its id shows up as a whole word long enough not to be a false positive."""
    title = _norm(profile.get("name", ""))
    ident = _norm(profile.get("id", ""))
    if not title and not ident:
        return False
    for n in names:
        if title and (title in n or n in title):
            return True
        if ident and len(ident) >= 4 and re.search(rf"\b{re.escape(ident)}\b", n):
            return True
    return False


def scan_installed_games(profiles: List[Dict[str, Any]], steam_root: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
    """Match install evidence against optimization profiles.

    Returns two honest sets:
      matched: { profile_id, source, appid? } — profile exists, apply available
      others:  { name, source, appid? }       — installed with no profile yet
    """
    if not profiles:
        return {"matched": [], "others": []}
    if not steam_root:
        # The Windows default; real Steam installs may live elsewhere but the
        # uninstall registry still catches those games.
        steam_root = r"C:\Program Files (x86)\Steam"

    matched: List[Dict[str, Any]] = []
    matched_ids: set = set()
    others: List[Dict[str, Any]] = []
    other_names: set = set()
    for game in _steam_games(steam_root) + _registry_games():
        names = [_norm(game["name"])]
        profile_hits = [p for p in profiles if _matches(p, names)]
        if profile_hits:
            for p in profile_hits:
                pid = p.get("id")
                if pid in matched_ids:
                    continue
                matched_ids.add(pid)
                appid = game.get("appid") or STEAM_APPID_FALLBACK.get(_norm(p.get("name", "")))
                entry: Dict[str, Any] = {"profile_id": pid, "source": game["source"]}
                if appid:
                    entry["appid"] = appid
                matched.append(entry)
            continue
        # Anything else that is a real Steam install is an installed game the
        # profile list does not cover — surface it rather than hiding it.
        if game["source"] == "steam" and not NON_GAME_PATTERNS.search(game["name"]):
            label = game["name"]
            if label.lower() not in other_names:
                other_names.add(label.lower())
                o: Dict[str, Any] = {"name": label, "source": game["source"]}
                if game.get("appid"):
                    o["appid"] = game["appid"]
                others.append(o)
    logger.info(f"Installed-games scan: {len(matched)} profiles matched, {len(others)} profileless installs")
    return {"matched": matched, "others": others}
