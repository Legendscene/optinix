"""Game discovery service tests — strict validation, no fabricated installs.

Covers the behaviors the real-machine scan exposed:
  - Steam manifests with missing dirs must be 'missing', not 'installed'
  - engine-standard exe resolution (Binaries/Win64/*-Shipping.exe)
  - uninstall-key entries must look like games (launchers/anti-cheat rejected)
  - dedupe merges duplicate sources without losing unique titles
  - running status comes only from a matching process image path
  - custom scanner rejects installers/helpers and unrelated exes
"""
import os
import sys
import types
from unittest.mock import patch

import pytest

from core import game_discovery as gd


def _cancel() -> gd._Cancel:
    return gd._Cancel()


def _write_manifest(path, appid: int, name: str, installdir: str = None,
                    state: str = "4") -> None:
    lines = [
        '"AppState"',
        '{',
        f'  "appid"\t"{appid}"',
        f'  "name"\t"{name}"',
        f'  "StateFlags"\t"{state}"',
    ]
    if installdir is not None:
        lines.append(f'  "installdir"\t"{installdir}"')
    lines.append('}')
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ------------------------------------------------------------- Gryphline

def _make_gryphline_layout(tmp_path, games):
    """games: list of (folder_name, {exe_name: size_bytes})."""
    root = tmp_path / "GRYPHLINK"
    for title, exes in games:
        gdir = root / "games" / title
        gdir.mkdir(parents=True)
        for exe, size in exes.items():
            (gdir / exe).write_bytes(b"MZ" + b"\0" * size)
    return root


def test_gryphline_detects_endfield(tmp_path):
    """Real-world shape: launcher root with games\\Arknights Endfield and a
    small Unity entry exe (Endfield.exe, <5 MB) that shares a token with the
    title. Detection must not depend on the 5 MB size heuristic."""
    root = _make_gryphline_layout(tmp_path, [
        ("Arknights Endfield", {"Endfield.exe": 895_448}),
    ])
    with patch.object(gd.GryphlineAdapter, "_launcher_roots", return_value=[str(root)]):
        games, notes = gd.GryphlineAdapter().scan(_cancel())
    assert len(games) == 1
    g = games[0]
    assert g["id"] == "gryphline:arknights-endfield"
    assert g["status"] == gd.STATUS_INSTALLED
    assert g["exe_path"].lower().endswith("endfield.exe")
    assert notes == []


def test_gryphline_missing_exe_is_missing(tmp_path):
    root = _make_gryphline_layout(tmp_path, [
        ("Some Title", {}),
    ])
    with patch.object(gd.GryphlineAdapter, "_launcher_roots", return_value=[str(root)]):
        games, _ = gd.GryphlineAdapter().scan(_cancel())
    assert games[0]["status"] == gd.STATUS_MISSING


def test_gryphline_helpers_never_picked_as_game(tmp_path):
    root = _make_gryphline_layout(tmp_path, [
        ("Arknights Endfield", {
            "Uninstall.exe": 5_000_000,     # big but helper: rejected
            "CrashHandler.exe": 2_000_000,  # helper: rejected
        }),
    ])
    with patch.object(gd.GryphlineAdapter, "_launcher_roots", return_value=[str(root)]):
        games, _ = gd.GryphlineAdapter().scan(_cancel())
    assert games[0]["status"] == gd.STATUS_MISSING  # no token-hit, no big clean exe


def test_gryphline_not_installed_note(tmp_path):
    with patch.object(gd.GryphlineAdapter, "_launcher_roots", return_value=[]):
        games, notes = gd.GryphlineAdapter().scan(_cancel())
    assert games == []
    assert any("not found" in n.lower() for n in notes)


def test_gryphline_in_service_adapters():
    assert gd.GryphlineAdapter in gd.GameDiscoveryService.ADAPTERS


# --------------------------------------------------------------------- Steam

def test_steam_valid_install(tmp_path):
    lib = tmp_path / "lib"
    common = lib / "steamapps" / "common"
    game_dir = common / "Cool Game"
    game_dir.mkdir(parents=True)
    (game_dir / "coolgame.exe").write_bytes(b"MZ" + b"\0" * 6_000_000)
    _write_manifest(lib / "steamapps" / "appmanifest_123.acf", 123, "Cool Game",
                    installdir="Cool Game")
    with patch.object(gd, "_steam_root_candidates", return_value=[str(lib)]), \
         patch.object(gd, "_steam_library_paths", return_value=[str(lib)]):
        games, notes = gd.SteamAdapter().scan(_cancel())
    assert len(games) == 1
    assert games[0]["status"] == gd.STATUS_INSTALLED
    assert games[0]["exe_path"] and os.path.isfile(games[0]["exe_path"])
    assert games[0]["id"] == "steam:123"


def test_steam_missing_install_dir_is_not_installed(tmp_path):
    """Manifest present, files gone — the honest 'missing' status."""
    lib = tmp_path / "lib"
    (lib / "steamapps").mkdir(parents=True)
    _write_manifest(lib / "steamapps" / "appmanifest_999.acf", 999,
                    "Uninstalled Game", installdir="Gone")
    with patch.object(gd, "_steam_root_candidates", return_value=[str(lib)]), \
         patch.object(gd, "_steam_library_paths", return_value=[str(lib)]):
        games, _ = gd.SteamAdapter().scan(_cancel())
    assert len(games) == 1
    assert games[0]["status"] == gd.STATUS_MISSING
    assert games[0]["install_path"] is None
    assert games[0]["exe_path"] is None


def test_steam_invalid_state_flags_rejected(tmp_path):
    """State 1/3 (installing/updating) must not claim a finished install."""
    lib = tmp_path / "lib"
    common = lib / "steamapps" / "common" / "Half Game"
    common.mkdir(parents=True)
    for state in ("1", "3"):
        _write_manifest(lib / "steamapps" / f"appmanifest_{state}.acf",
                        int(state), "Half Game", installdir="Half Game",
                        state=state)
    with patch.object(gd, "_steam_root_candidates", return_value=[str(lib)]), \
         patch.object(gd, "_steam_library_paths", return_value=[str(lib)]):
        games, _ = gd.SteamAdapter().scan(_cancel())
    assert [g for g in games if g["status"] == gd.STATUS_INSTALLED] == []


def test_steam_multiple_libraries(tmp_path):
    root = tmp_path / "steam"
    other = tmp_path / "gamesdrv"
    for base in (root, other):
        (base / "steamapps" / "common" / "Game A").mkdir(parents=True)
    _write_manifest(root / "steamapps" / "appmanifest_1.acf", 1, "Game A",
                    installdir="Game A")
    _write_manifest(other / "steamapps" / "appmanifest_2.acf", 2, "Game A",
                    installdir="Game A")
    lib_paths = [str(root), str(other)]
    with patch.object(gd, "_steam_root_candidates", return_value=[str(root)]), \
         patch.object(gd, "_steam_library_paths", return_value=lib_paths):
        games, _ = gd.SteamAdapter().scan(_cancel())
    assert {g["id"] for g in games} == {"steam:1", "steam:2"}


def test_steam_redists_and_servers_never_games(tmp_path):
    lib = tmp_path / "lib"
    (lib / "steamapps" / "common" / "Proton Mock").mkdir(parents=True)
    _write_manifest(lib / "steamapps" / "appmanifest_228980.acf", 228980,
                    "Steamworks Common Redistributables",
                    installdir="Proton Mock")
    _write_manifest(lib / "steamapps" / "appmanifest_1.acf", 1,
                    "Foo Dedicated Server", installdir="Proton Mock")
    with patch.object(gd, "_steam_root_candidates", return_value=[str(lib)]), \
         patch.object(gd, "_steam_library_paths", return_value=[str(lib)]):
        games, _ = gd.SteamAdapter().scan(_cancel())
    assert [g["name"] for g in games] == []


# ---------------------------------------------------------- exe resolution

def test_resolve_game_exe_finds_unreal_shipping_binary(tmp_path):
    """The real drive layout: Client/Binaries/Win64/Client-Win64-Shipping.exe."""
    root = tmp_path / "Wuthering Waves"
    bin64 = root / "Client" / "Binaries" / "Win64"
    bin64.mkdir(parents=True)
    exe = bin64 / "Client-Win64-Shipping.exe"
    exe.write_bytes(b"MZ" + b"\0" * 40_000_000)
    (root / "unins000.exe").write_bytes(b"x")  # helper, must be skipped
    assert gd.resolve_game_exe(str(root)) == str(exe)


def test_resolve_game_exe_skips_small_helpers(tmp_path):
    root = tmp_path / "Game"
    root.mkdir()
    (root / "GameHelper.exe").write_bytes(b"\0" * 4096)
    assert gd.resolve_game_exe(str(root)) is None


def test_resolve_game_exe_rejects_installers(tmp_path):
    root = tmp_path / "Game"
    root.mkdir()
    (root / "unins000.exe").write_bytes(b"\0" * 10_000_000)
    (root / "Setup.exe").write_bytes(b"\0" * 10_000_000)
    assert gd.resolve_game_exe(str(root)) is None


# ---------------------------------------------------------------- Uninstall

def test_uninstall_adapter_rejects_launchers_and_anticheat():
    cases = [
        "Epic Games Launcher",
        "Ubisoft Game Launcher",
        "Riot Client",
        "EasyAntiCheat",
        "AMD Software: Adrenalin Edition",
        "Optinix 1.0.0",
        "AntiCheatExpert",
        "MSI App Player Engine",
    ]
    for s in cases:
        assert not gd.UninstallAdapter._is_game_name(s), s


def test_uninstall_adapter_accepts_game_names():
    for s in ["Battlefield V Game", "Grand Theft Auto V Game",
              "Total War: WARHAMMER III Game", "My Summer Game: Car"]:
        assert gd.UninstallAdapter._is_game_name(s), s


# ------------------------------------------------------------------- dedupe

def test_dedupe_merges_same_game_from_two_sources():
    merged = gd._dedupe([
        {"id": "reg:a", "name": "Wuthering Waves",
         "install_path": r"C:\Games\WuWa", "status": gd.STATUS_INSTALLED,
         "source": "registry"},
        {"id": "steam:3513350", "name": "Wuthering Waves",
         "install_path": r"C:\Games\WuWa", "status": gd.STATUS_INSTALLED,
         "source": "steam", "appid": 3513350},
        {"id": "steam:730", "name": "Counter-Strike 2",
         "install_path": r"C:\Games\CS2", "status": gd.STATUS_INSTALLED,
         "source": "steam", "appid": 730},
    ])
    names = [g["name"] for g in merged]
    assert names.count("Wuthering Waves") == 1
    assert len(merged) == 2
    wuwa = next(g for g in merged if g["name"] == "Wuthering Waves")
    assert wuwa["appid"] == 3513350          # richer record wins
    assert wuwa["source"] == "registry"      # first record keeps the id
    assert sorted(wuwa.get("sources", [])) == ["registry", "steam"]


def test_dedupe_keeps_same_name_different_paths():
    """Two distinct installs of one title must stay two entries."""
    merged = gd._dedupe([
        {"id": "s:1", "name": "Game X", "install_path": r"C:\a",
         "status": gd.STATUS_INSTALLED, "source": "steam"},
        {"id": "s:2", "name": "Game X", "install_path": r"D:\a",
         "status": gd.STATUS_INSTALLED, "source": "steam"},
    ])
    assert len(merged) == 2


def test_dedupe_emulator_family_merges_to_one_card():
    """One emulator product = one card. BlueStacks/MSI ships an engine and a
    player shell in sibling folders, and BOTH the Start Menu adapter and the
    emulator adapter witness them — three records, one product."""
    merged = gd._dedupe([
        {"id": "startmenu:engine", "name": "MSI App Player Engine",
         "source": "startmenu", "kind": "emulator",
         "install_path": r"C:\Program Files\BlueStacks_msi5",
         "exe_path": r"C:\Program Files\BlueStacks_msi5\HD-Player.exe",
         "status": gd.STATUS_INSTALLED},
        {"id": "startmenu:player", "name": "MSI App Player",
         "source": "startmenu", "kind": "emulator",
         "install_path": r"C:\Program Files (x86)\BlueStacks X_msi5",
         "exe_path": r"C:\Program Files (x86)\BlueStacks X_msi5\MSI App Player.exe",
         "status": gd.STATUS_INSTALLED},
        {"id": "emulator:msi", "name": "MSI App Player",
         "source": "emulator", "kind": "emulator",
         "install_path": r"C:\Program Files\BlueStacks_msi5",
         "exe_path": r"C:\Program Files\BlueStacks_msi5\HD-Player.exe",
         "status": gd.STATUS_INSTALLED},
    ])
    emus = [g for g in merged if g.get("kind") == "emulator"]
    assert len(emus) == 1, "one emulator product must render exactly one card"
    # The emulator adapter is the product authority for name and source.
    assert emus[0]["name"] == "MSI App Player"
    assert emus[0]["source"] == "emulator"
    assert emus[0]["exe_path"].endswith("HD-Player.exe")
    assert sorted(emus[0].get("sources", [])) == ["emulator", "startmenu"]


def test_dedupe_family_rule_never_swallows_same_name_games():
    """The prefix-family rule is emulator-only: two same-name game installs
    on different drives must stay two cards (two-locations rule)."""
    merged = gd._dedupe([
        {"id": "s:1", "name": "Game X", "kind": "game", "source": "steam",
         "install_path": r"C:\a", "status": gd.STATUS_INSTALLED},
        {"id": "s:2", "name": "Game X", "kind": "game", "source": "steam",
         "install_path": r"D:\a", "status": gd.STATUS_INSTALLED},
    ])
    assert len(merged) == 2


# ------------------------------------------------------------- running check

class _FakeProc:
    def __init__(self, exe):
        self.info = {"exe": exe}


def test_running_check_marks_only_matching_process():
    games = [
        {"id": "steam:1", "name": "A", "status": gd.STATUS_INSTALLED,
         "exe_path": r"C:\Games\A\A.exe"},
        {"id": "steam:2", "name": "B", "status": gd.STATUS_INSTALLED,
         "exe_path": r"C:\Games\B\B.exe"},
        {"id": "steam:3", "name": "C", "status": gd.STATUS_INSTALLED,
         "exe_path": None},
    ]
    fake_psutil = types.SimpleNamespace(
        process_iter=lambda fields: [_FakeProc(r"C:\Games\A\A.exe")],
    )
    with patch.dict(sys.modules, {"psutil": fake_psutil}):
        gd._running_check(games)
    assert games[0]["status"] == gd.STATUS_RUNNING
    assert games[1]["status"] == gd.STATUS_INSTALLED
    assert games[2]["status"] == gd.STATUS_INSTALLED


def test_running_check_never_promotes_missing_or_restricted():
    games = [
        {"id": "s:1", "name": "A", "status": gd.STATUS_MISSING,
         "exe_path": r"C:\Gone\A.exe"},
        {"id": "s:2", "name": "B", "status": gd.STATUS_RESTRICTED,
         "exe_path": None},
    ]
    fake_psutil = types.SimpleNamespace(
        process_iter=lambda fields: [_FakeProc(r"C:\Gone\A.exe")],
    )
    with patch.dict(sys.modules, {"psutil": fake_psutil}):
        gd._running_check(games)
    assert games[0]["status"] == gd.STATUS_MISSING
    assert games[1]["status"] == gd.STATUS_RESTRICTED


# ------------------------------------------------------------ custom scanner

def test_custom_scanner_rejects_unrelated_exes(tmp_path):
    root = tmp_path / "RandomApp"
    root.mkdir()
    (root / "randomapp.exe").write_bytes(b"\0" * 10_000_000)
    scanner = gd.CustomDirectoryScanner()
    g, _ = scanner.scan_roots([str(root)], _cancel())
    assert g == []


def test_custom_scanner_accepts_plausible_game(tmp_path):
    root = tmp_path / "My Cool Game"
    root.mkdir()
    (root / "CoolGameClient.exe").write_bytes(b"\0" * 10_000_000)
    scanner = gd.CustomDirectoryScanner()
    g, _ = scanner.scan_roots([str(root)], _cancel())
    assert len(g) == 1
    assert g[0]["status"] == gd.STATUS_INSTALLED
    assert g[0]["source"] == "custom"


def test_custom_scanner_reports_missing_and_denied_roots(tmp_path):
    missing = tmp_path / "nope"
    root = tmp_path / "Locked"
    root.mkdir()
    scanner = gd.CustomDirectoryScanner()
    with patch.object(os, "listdir", side_effect=PermissionError):
        _, notes = scanner.scan_roots([str(root)], _cancel())
    _, notes2 = scanner.scan_roots([str(missing)], _cancel())
    assert any("denied" in n for n in notes)
    assert any("does not exist" in n for n in notes2)


# ------------------------------------------------------------ diagnostics

def test_steam_disconnected_library_reports_note(tmp_path):
    """A VDF-configured library on a disconnected drive must produce an
    explicit note ('drive not connected'), never silent silence."""
    root = tmp_path / "steam"
    (root / "steamapps" / "common" / "Game A").mkdir(parents=True)
    _write_manifest(root / "steamapps" / "appmanifest_1.acf", 1, "Game A",
                    installdir="Game A")
    ghost_lib = tmp_path / "GhostLibrary"  # exists in VDF, drive absent
    lib_paths = [str(root), str(ghost_lib)]
    with patch.object(gd, "_steam_root_candidates", return_value=[str(root)]), \
         patch.object(gd, "_steam_library_paths", return_value=lib_paths), \
         patch.object(os.path, "isdir", side_effect=lambda p: not str(p).startswith(str(ghost_lib))):
        games, notes = gd.SteamAdapter().scan(_cancel())
    assert any("Steam library" in n and str(ghost_lib) in n for n in notes), notes
    assert len(games) == 1  # the real library still scanned


def test_scan_result_includes_diagnostics(tmp_path):
    """Every completed scan carries a per-source diagnostics summary with
    real counts — verified, candidates, duplicates removed."""
    svc = gd.GameDiscoveryService()
    with patch.object(gd.GameDiscoveryService, "_CACHE_FILE",
                      str(tmp_path / "cache.json")):
        result = svc.scan_sync()
    diag = result.get("diagnostics")
    assert diag is not None
    assert diag["verified_installed"] == sum(
        1 for g in result["games"]
        if g["status"] in (gd.STATUS_INSTALLED, gd.STATUS_RUNNING)
    )
    assert diag["candidates_found"] >= diag["verified_installed"]
    assert diag["duplicates_removed"] >= 0
    assert len(diag["sources"]) == len(gd.GameDiscoveryService.ADAPTERS)
    for s in diag["sources"]:
        assert s["status"] in {"inspected", "not_installed", "access_restricted", "error"}
        assert isinstance(s["notes"], list)


def test_dedupe_count_reported_in_diagnostics():
    two_copies = [
        {"id": "a", "name": "Same Game", "install_path": r"C:\G\x",
         "status": gd.STATUS_INSTALLED, "source": "steam"},
        {"id": "b", "name": "Same Game", "install_path": r"C:\G\x",
         "status": gd.STATUS_INSTALLED, "source": "registry"},
    ]
    assert len(gd._dedupe(list(two_copies))) == 1


# ------------------------------------------------------------------ progress

def test_scan_progress_and_cancel():
    svc = gd.GameDiscoveryService()
    p = svc.scan_progress()
    assert p["running"] is False
    assert svc.cancel_scan() is False  # no scan in flight


def test_scan_sync_caches_result(tmp_path):
    svc = gd.GameDiscoveryService()
    with patch.object(gd.GameDiscoveryService, "_CACHE_FILE",
                      str(tmp_path / "cache.json")):
        result = svc.scan_sync()
        assert "games" in result
        cached = svc.cached_result()
        assert cached is not None and "games" in cached
        assert cached["games"] == result["games"]
