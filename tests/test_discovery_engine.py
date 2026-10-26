"""Universal discovery engine tests — Source B (Start Menu shortcuts),
cross-source dedupe merge, false-positive rejection and the automatic
refresh lifecycle.

Shortcut resolution and the filesystem are mocked, so no real COM/pythoncom
is needed and no real Start Menu is touched. The .lnk parser tests build
byte-accurate MS-SHLLINK fixtures (header, IDList, LinkInfo, StringData) —
the exact layout verified empirically against real shortcuts on a live
machine, where the Endfield acceptance case resolves to
C:\\Program Files\\GRYPHLINK\\Launcher.exe with args ``--game=endfield
--reason=4``.

These tests are mocked and do NOT prove Endfield was detected here; real
machine verification is a separate step.
"""
import os
import time
from unittest.mock import patch

import pytest

import core.game_discovery as gd
from core.game_discovery import (
    StartMenuShortcutAdapter, resolve_lnk_target, _Cancel,
    STATUS_INSTALLED, STATUS_MISSING,
)


def _cancel():
    return gd._Cancel()


# ---------------------------------------------------------------------------
# MS-SHLLINK fixture builders
# ---------------------------------------------------------------------------


def _build_lnk(dirpath, name, flags, body=b""):
    """A spec-layout .lnk: 0x4C-byte header (LinkFlags at 0x14) followed by
    the optional blocks in order (IDList, LinkInfo, StringData)."""
    header = bytearray(0x4C)
    header[0:4] = b"L\x00\x00\x00"
    header[0x14:0x18] = flags.to_bytes(4, "little")
    p = os.path.join(str(dirpath), name)
    with open(p, "wb") as f:
        f.write(bytes(header) + body)
    return p


def _linkinfo(path):
    """A minimal LinkInfo structure: VolumeID + null-terminated ASCII
    LocalBasePath. LocalBasePathOffset sits at +0x10 of this header."""
    vol = bytearray(16)
    vol[0:4] = (16).to_bytes(4, "little")       # VolumeIDSize
    vol[4:8] = (3).to_bytes(4, "little")        # DRIVE_FIXED
    vol[12:16] = (0x10).to_bytes(4, "little")   # VolumeLabelOffset
    pth = path.encode("latin-1") + b"\x00"
    lbp_off = 0x1C + len(vol)
    li = bytearray()
    li += (0).to_bytes(4, "little")             # size placeholder
    li += (0x1C).to_bytes(4, "little")          # LinkInfoHeaderSize
    li += (1).to_bytes(4, "little")             # VolumeIDAndLocalBasePath
    li += (0x1C).to_bytes(4, "little")          # VolumeIDOffset
    li += lbp_off.to_bytes(4, "little")         # LocalBasePathOffset (+0x10)
    li += (0).to_bytes(4, "little")             # CNRL offset (+0x14)
    li += (lbp_off + len(pth)).to_bytes(4, "little")  # suffix (+0x18)
    li += bytes(vol)
    li += pth
    li[0:4] = len(li).to_bytes(4, "little")
    return bytes(li)


def _string_data(text):
    """StringData block: uint16 character count + UTF-16LE characters."""
    return len(text).to_bytes(2, "little") + text.encode("utf-16-le")


# ---------------------------------------------------------------------------
# resolve_lnk_target — pure-python MS-SHLLINK reader
# ---------------------------------------------------------------------------


class TestLnkParser:
    def test_non_lnk_file_rejected(self, tmp_path):
        p = tmp_path / "not-a-link.lnk"
        p.write_bytes(b"NOPE" * 20)
        target, err = resolve_lnk_target(str(p))
        assert target is None and "Not a Shell Link" in err

    def test_missing_file_rejected(self, tmp_path):
        target, err = resolve_lnk_target(str(tmp_path / "ghost.lnk"))
        assert target is None and "unreadable" in err.lower()

    def test_linkinfo_local_base_path(self, tmp_path):
        """LinkInfo sits directly after the header (no IDList); the exact
        machine path comes from LocalBasePathOffset at +0x10."""
        path = r"C:\Games\Great\GreatGame.exe"
        lnk = _build_lnk(tmp_path, "g.lnk", flags=0x2, body=_linkinfo(path))
        target, err = resolve_lnk_target(lnk)
        assert err == ""
        assert target.partition("|")[0] == path

    def test_idlist_then_linkinfo_exact_args(self, tmp_path):
        """Real-world layout regression: IDList FIRST, LinkInfo after it
        (not fixed 0x4C), arguments read from exact StringData. This is the
        byte layout of the actual 'Arknights Endfield.lnk' shortcut."""
        path = r"C:\Program Files\GRYPHLINK\Launcher.exe"
        args = "--game=endfield --reason=4"
        idlist = b"\xaa\x00" + b"\xbb" * 20 + b"\x00\x00"  # opaque items
        body = bytearray()
        body += len(idlist).to_bytes(2, "little")          # IDListSize
        body += idlist
        body += _linkinfo(path)
        body += _string_data(args)
        lnk = _build_lnk(tmp_path, "endfield.lnk",
                         flags=0x1 | 0x2 | 0x8, body=bytes(body))
        out, err = resolve_lnk_target(lnk)
        assert err == "" and out
        target, _, got_args = out.partition("|")
        assert target == path
        assert got_args == args

    def test_idlist_only_shortcut_resolves_path(self, tmp_path):
        """No LinkInfo: the UTF-16 exe path inside the IDList is found and
        validated by the caller; nothing is executed, no args invented."""
        path = r"C:\Games\Great\\" + "Z" * 200 + r"\GreatGame.exe"
        payload = _string_data(path)
        body = len(payload).to_bytes(2, "little") + payload  # IDListSize
        lnk = _build_lnk(tmp_path, "idlist.lnk", flags=0x1, body=body)
        out, err = resolve_lnk_target(lnk)
        assert err == ""
        assert "|" not in out  # no HasArguments flag -> no fabricated args
        assert out == path

    def test_no_target_yields_error_not_invention(self, tmp_path):
        lnk = _build_lnk(tmp_path, "empty.lnk", flags=0x0, body=b"\x00" * 8)
        target, err = resolve_lnk_target(lnk)
        assert target is None
        assert "could not be resolved safely" in err


# ---------------------------------------------------------------------------
# StartMenuShortcutAdapter — filtering and evidence rules
#
# Targets are fake Windows paths (never under \Temp\ or \Downloads\, which
# the adapter rightly rejects — and pytest's tmp_path lives in \Temp\), with
# isfile/getsize patched so the fixtures stay deterministic on any machine.
# ---------------------------------------------------------------------------


def _write_lnk(dirpath, rel):
    p = os.path.join(str(dirpath), rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(b"L\x00\x00\x00" + b"\x00" * 64)
    return p


_FS_TRUE = patch("core.game_discovery.os.path.isfile", return_value=True)
_FS_FALSE = patch("core.game_discovery.os.path.isfile", return_value=False)


def _fs_size(mb):
    return patch("core.game_discovery.os.path.getsize",
                 return_value=mb * 1024 * 1024)


@pytest.mark.skipif(os.name != "nt", reason="Start Menu discovery is Windows-only")
class TestStartMenuAdapter:
    def test_game_shortcut_produces_installed_record(self, tmp_path):
        exe = r"C:\Games\Roblox\RobloxPlayerBeta.exe"
        lnk = _write_lnk(tmp_path, "Programs/Roblox/Roblox Player.lnk")
        with patch.object(StartMenuShortcutAdapter, "_shortcut_files", return_value=[lnk]), \
             patch.object(StartMenuShortcutAdapter, "_resolve", return_value=(exe + "|", "")), \
             _FS_TRUE, _fs_size(8):
            games, notes = StartMenuShortcutAdapter().scan(_cancel())
        assert len(games) == 1
        g = games[0]
        assert g["id"] == "startmenu:roblox-player"
        assert g["status"] == STATUS_INSTALLED
        assert g["exe_path"] == exe
        assert g["install_path"] == r"C:\Games\Roblox"
        assert g["shortcut_path"] == lnk

    def test_launcher_shortcut_without_game_args_rejected(self, tmp_path):
        """Steam surface with no --game= args is a launcher, not a game."""
        lnk = _write_lnk(tmp_path, "Programs/Steam/Steam.lnk")
        with patch.object(StartMenuShortcutAdapter, "_shortcut_files", return_value=[lnk]), \
             patch.object(StartMenuShortcutAdapter, "_resolve",
                          return_value=(r"C:\Program Files (x86)\Steam\steam.exe|", "")):
            games, notes = StartMenuShortcutAdapter().scan(_cancel())
        assert games == []

    def test_launcher_shortcut_with_game_args_kept(self, tmp_path):
        launcher = r"C:\Program Files\GRYPHLINK\Launcher.exe"
        lnk = _write_lnk(tmp_path, "Programs/Arknights Endfield.lnk")
        with patch.object(StartMenuShortcutAdapter, "_shortcut_files", return_value=[lnk]), \
             patch.object(StartMenuShortcutAdapter, "_resolve",
                          return_value=(launcher + "|--game=endfield --reason=4", "")), \
             _FS_TRUE:
            games, _ = StartMenuShortcutAdapter().scan(_cancel())
        assert len(games) == 1
        assert games[0]["launch_target"] == launcher
        assert games[0]["launch_args"].startswith("--game=")
        assert games[0]["exe_path"] is None  # launcher branch: no exe claim

    def test_known_apps_never_become_games(self, tmp_path):
        for i, surface in enumerate(("Visual Studio Code", "Discord", "Spotify",
                                     "Cheat Engine", "WinRAR", "Python 3.14",
                                     "NVIDIA App", "Project Lightning")):
            # The adapter derives the title from the shortcut filename, so
            # the denylist surface must BE the filename.
            lnk = _write_lnk(tmp_path, f"Programs/{i}-{surface}.lnk")
            with patch.object(StartMenuShortcutAdapter, "_shortcut_files", return_value=[lnk]), \
                 patch.object(StartMenuShortcutAdapter, "_resolve",
                              return_value=(r"C:\apps\x.exe|", "")):
                games, _ = StartMenuShortcutAdapter().scan(_cancel())
            assert games == [], f"{surface} must not be a game record"

    def test_uninstall_shortcut_rejected(self, tmp_path):
        lnk = _write_lnk(tmp_path, "Programs/Some Game Uninstall.lnk")
        with patch.object(StartMenuShortcutAdapter, "_shortcut_files", return_value=[lnk]), \
             patch.object(StartMenuShortcutAdapter, "_resolve",
                          return_value=(r"C:\Games\SomeGame\unins000.exe|", "")):
            games, _ = StartMenuShortcutAdapter().scan(_cancel())
        assert games == []

    def test_generic_file_shortcut_rejected(self, tmp_path):
        """A shortcut named for a file/folder concept is a shell artifact, not
        a title: the real machine has a stray 'Filee' shortcut pointing at a
        missing C:\\Program Files\\File\\File.exe, which used to become a game
        card called 'File'. Collapsing repeated letters catches 'Filee' as
        well as 'File'."""
        for name in ("File", "Filee", "App", "Gamee"):
            lnk = _write_lnk(tmp_path, f"Programs/{name}.lnk")
            with patch.object(StartMenuShortcutAdapter, "_shortcut_files", return_value=[lnk]), \
                 patch.object(StartMenuShortcutAdapter, "_resolve",
                              return_value=(r"C:\Program Files\File\File.exe|", "")), \
                 _FS_FALSE:
                games, _ = StartMenuShortcutAdapter().scan(_cancel())
            assert games == [], f"{name} must not become a game record"

    def test_system_directory_target_rejected(self, tmp_path):
        lnk = _write_lnk(tmp_path, "Programs/Awesome Quest.lnk")
        with patch.object(StartMenuShortcutAdapter, "_shortcut_files", return_value=[lnk]), \
             patch.object(StartMenuShortcutAdapter, "_resolve",
                          return_value=(r"C:\Windows\System32\quest.exe|", "")):
            games, _ = StartMenuShortcutAdapter().scan(_cancel())
        assert games == []

    def test_downloads_folder_target_rejected(self, tmp_path):
        lnk = _write_lnk(tmp_path, "Programs/Suspicious Game.lnk")
        with patch.object(StartMenuShortcutAdapter, "_shortcut_files", return_value=[lnk]), \
             patch.object(StartMenuShortcutAdapter, "_resolve",
                          return_value=(r"C:\Users\me\Downloads\SYNCLYX\game.exe|", "")):
            games, _ = StartMenuShortcutAdapter().scan(_cancel())
        assert games == []

    def test_vanished_target_is_missing_not_hidden(self, tmp_path):
        """Stale shortcut pointing at a deleted exe: honest 'missing' record."""
        lnk = _write_lnk(tmp_path, "Programs/Roblox/Roblox Player.lnk")
        with patch.object(StartMenuShortcutAdapter, "_shortcut_files", return_value=[lnk]), \
             patch.object(StartMenuShortcutAdapter, "_resolve",
                          return_value=(r"C:\Games\Roblox\GonePlayer.exe|", "")), \
             _FS_FALSE:
            games, _ = StartMenuShortcutAdapter().scan(_cancel())
        assert len(games) == 1
        assert games[0]["status"] == STATUS_MISSING
        assert games[0]["exe_path"] is None
        assert games[0]["install_path"] is None

    def test_emulator_exe_recorded_with_kind(self, tmp_path):
        exe = r"C:\Emulators\HD-Player.exe"
        lnk = _write_lnk(tmp_path, "Programs/MSI App Player.lnk")
        with patch.object(StartMenuShortcutAdapter, "_shortcut_files", return_value=[lnk]), \
             patch.object(StartMenuShortcutAdapter, "_resolve", return_value=(exe + "|", "")), \
             _FS_TRUE, _fs_size(6):
            games, _ = StartMenuShortcutAdapter().scan(_cancel())
        assert len(games) == 1
        assert games[0]["kind"] == "emulator"
        assert games[0]["status"] == STATUS_INSTALLED

    def test_non_exe_target_rejected(self, tmp_path):
        """A .url documentation shortcut (Windows SDK ships these) is never
        a game installation witness, even when the file exists."""
        url_file = r"C:\Program Files (x86)\Windows Kits\10\Shortcuts\DesktopAppsSamples.url"
        lnk = _write_lnk(tmp_path, "Programs/Sample Desktop Apps.lnk")
        with patch.object(StartMenuShortcutAdapter, "_shortcut_files", return_value=[lnk]), \
             patch.object(StartMenuShortcutAdapter, "_resolve",
                          return_value=(url_file + "|", "")), \
             _FS_TRUE:
            games, _ = StartMenuShortcutAdapter().scan(_cancel())
        assert games == []

    def test_small_emulator_shell_still_installed(self, tmp_path):
        """A live 0.5 MB BlueStacks launcher must not be reported 'missing'
        just because it is smaller than the 5 MB game-binary heuristic."""
        exe = r"C:\Program Files (x86)\BlueStacks X_msi5\MSI App Player.exe"
        lnk = _write_lnk(tmp_path, "Programs/MSI App Player/MSI App Player.lnk")
        with patch.object(StartMenuShortcutAdapter, "_shortcut_files", return_value=[lnk]), \
             patch.object(StartMenuShortcutAdapter, "_resolve", return_value=(exe + "|", "")), \
             _FS_TRUE, _fs_size(0.5):
            games, _ = StartMenuShortcutAdapter().scan(_cancel())
        assert len(games) == 1
        assert games[0]["kind"] == "emulator"
        assert games[0]["status"] == STATUS_INSTALLED

    def test_small_native_helper_still_missing(self, tmp_path):
        """The size gate still protects native games: a small existing exe
        is 'missing verification', never a verified install."""
        exe = r"C:\Games\SomeGame\SomeGame.exe"
        lnk = _write_lnk(tmp_path, "Programs/Some Game.lnk")
        with patch.object(StartMenuShortcutAdapter, "_shortcut_files", return_value=[lnk]), \
             patch.object(StartMenuShortcutAdapter, "_resolve", return_value=(exe + "|", "")), \
             _FS_TRUE, _fs_size(0.5):
            games, _ = StartMenuShortcutAdapter().scan(_cancel())
        assert len(games) == 1
        assert games[0]["status"] == STATUS_MISSING

    def test_scan_cancellation_stops_early(self, tmp_path):
        _write_lnk(tmp_path, "Programs/A/Roblox Player.lnk")
        _write_lnk(tmp_path, "Programs/B/Some Game.lnk")
        cancel = _Cancel()
        with patch.object(StartMenuShortcutAdapter, "_shortcut_files", return_value=["x", "y"]), \
             patch.object(StartMenuShortcutAdapter, "_resolve", return_value=(None, "broken")):
            games, _ = StartMenuShortcutAdapter().scan(cancel)
            assert games == []
            cancel.cancel()
            # Once cancelled, a scan returns without touching any source.
            games2, _ = StartMenuShortcutAdapter().scan(cancel)
            assert games2 == []

    def test_diagnostics_notes_are_specific(self, tmp_path):
        lnks = [_write_lnk(tmp_path, f"Programs/X{i}.lnk") for i in range(3)]
        with patch.object(StartMenuShortcutAdapter, "_shortcut_files", return_value=lnks), \
             patch.object(StartMenuShortcutAdapter, "_resolve", return_value=(None, "broken")):
            games, notes = StartMenuShortcutAdapter().scan(_cancel())
        assert any("game-like shortcuts" in n for n in notes)
        assert any("broken" in n for n in notes)


# ---------------------------------------------------------------------------
# Cross-source dedupe merge
# ---------------------------------------------------------------------------


class TestDedupeMerge:
    def test_same_title_different_sources_merge(self):
        launcher_record = {
            "id": "gryphline:arknights-endfield", "name": "Arknights Endfield",
            "source": "gryphline",
            "install_path": r"C:\Program Files\GRYPHLINK\games\Arknights Endfield",
            "exe_path": r"C:\Program Files\GRYPHLINK\games\Arknights Endfield\Endfield.exe",
            "status": STATUS_INSTALLED,
        }
        shortcut_record = {
            "id": "startmenu:arknights-endfield", "name": "Arknights Endfield",
            "source": "startmenu",
            "install_path": None, "exe_path": None,
            "shortcut_path": r"C:\StartMenu\Arknights Endfield.lnk",
            "launch_args": "--game=endfield --reason=4",
            "status": STATUS_INSTALLED,
        }
        merged = gd._dedupe([launcher_record, shortcut_record])
        assert len(merged) == 1
        m = merged[0]
        assert sorted(m["sources"]) == ["gryphline", "startmenu"]
        # Primary source is the install witness — the launcher, not the
        # shortcut — so the launcher filter shows the real launcher.
        assert m["source"] == "gryphline"
        # Richer evidence wins; weaker side's shortcut data is preserved.
        assert m["exe_path"] and m["exe_path"].endswith("Endfield.exe")
        assert m.get("shortcut_path") == shortcut_record["shortcut_path"]
        assert m.get("launch_args") == "--game=endfield --reason=4"

    def test_differing_paths_same_title_not_merged(self):
        """Same game title on two drives = two games, never one."""
        a = {"id": "steam:1", "name": "Same Name", "source": "steam",
             "install_path": r"C:\Games\A", "exe_path": r"C:\Games\A\a.exe",
             "status": STATUS_INSTALLED}
        b = {"id": "custom:2", "name": "Same Name", "source": "custom",
             "install_path": r"D:\B", "exe_path": r"D:\B\b.exe",
             "status": STATUS_INSTALLED}
        assert len(gd._dedupe([a, b])) == 2

    def test_truly_identical_path_merges(self):
        a = {"id": "steam:1", "name": "Duo", "source": "steam",
             "install_path": r"C:\Games\Duo", "exe_path": r"C:\Games\Duo\d.exe",
             "status": STATUS_INSTALLED}
        b = {"id": "reg:duo", "name": "Duo", "source": "registry",
             "install_path": r"C:\Games\Duo", "exe_path": None,
             "status": STATUS_INSTALLED}
        merged = gd._dedupe([a, b])
        assert len(merged) == 1
        assert merged[0]["exe_path"].endswith("d.exe")
        assert sorted(merged[0]["sources"]) == ["registry", "steam"]

    def test_distinct_games_survive(self):
        a = {"id": "steam:1", "name": "Alpha", "source": "steam",
             "install_path": r"C:\A", "exe_path": None, "status": STATUS_INSTALLED}
        b = {"id": "steam:2", "name": "Beta", "source": "steam",
             "install_path": r"C:\B", "exe_path": None, "status": STATUS_INSTALLED}
        assert len(gd._dedupe([a, b])) == 2


# ---------------------------------------------------------------------------
# Launch endpoint: launcher-args path
# ---------------------------------------------------------------------------


class TestLauncherArgsLaunch:
    def _app(self):
        from core.api.game_library_api import game_library_bp
        from flask import Flask
        app = Flask(__name__)
        app.register_blueprint(game_library_bp)
        return app.test_client()

    def test_launcher_target_launch_with_args(self, tmp_path):
        """No exe_path but launch_target+args: Popen via launcher, no shell."""
        launcher = tmp_path / "Launcher.exe"
        launcher.write_bytes(b"MZ")
        game = {
            "id": "startmenu:x", "name": "X", "source": "startmenu",
            "install_path": None, "exe_path": None,
            "launch_target": str(launcher), "launch_args": "--game=endfield --reason=4",
            "status": STATUS_INSTALLED,
        }
        with patch("core.api.game_library_api._find_game", return_value=game), \
             patch("subprocess.Popen") as popen:
            r = self._app().post("/api/game-library/launch", json={"id": "startmenu:x"})
            assert r.status_code == 200
            assert r.get_json()["launched"] is True
            args_, kwargs = popen.call_args
            cmd = args_[0]
            assert cmd[0] == str(launcher)
            assert "--game=endfield" in cmd
            assert not kwargs.get("shell")

    def test_missing_exe_and_no_launcher_fails(self):
        game = {
            "id": "startmenu:y", "name": "Y", "source": "startmenu",
            "install_path": None, "exe_path": None,
            "status": STATUS_MISSING,
        }
        with patch("core.api.game_library_api._find_game", return_value=game):
            r = self._app().post("/api/game-library/launch", json={"id": "startmenu:y"})
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Automatic refresh lifecycle
# ---------------------------------------------------------------------------


class TestAutoRefresh:
    def _client(self):
        from core.api.game_library_api import game_library_bp
        from flask import Flask
        app = Flask(__name__)
        app.register_blueprint(game_library_bp)
        return app.test_client()

    def test_stale_cache_triggers_background_rescan(self):
        """A cache older than 24h quietly schedules one background scan;
        the response itself is never blocked on it."""
        from core.api.game_library_api import _AUTO_SCAN_MAX_AGE_S
        stale = {"saved_at": time.time() - _AUTO_SCAN_MAX_AGE_S - 10,
                 "games": [], "notes": [], "diagnostics": None}
        started = {"n": 0}
        with patch("core.api.game_library_api.get_service") as gs:
            svc = gs.return_value
            svc.cached_result.return_value = stale
            svc.scan_progress.return_value = {"running": False}
            svc.scan_async.side_effect = lambda *a, **k: (
                started.__setitem__("n", started["n"] + 1) or True)
            r = self._client().get("/api/game-library")
        assert r.status_code == 200
        assert started["n"] == 1

    def test_fresh_cache_no_rescan(self):
        fresh = {"saved_at": time.time() - 60, "games": [], "notes": [],
                 "diagnostics": None}
        with patch("core.api.game_library_api.get_service") as gs:
            svc = gs.return_value
            svc.cached_result.return_value = fresh
            svc.scan_progress.return_value = {"running": False}
            r = self._client().get("/api/game-library")
        assert r.status_code == 200
        svc.scan_async.assert_not_called()

    def test_running_scan_not_double_started(self):
        from core.api.game_library_api import _AUTO_SCAN_MAX_AGE_S
        stale = {"saved_at": time.time() - _AUTO_SCAN_MAX_AGE_S - 10,
                 "games": [], "notes": []}
        with patch("core.api.game_library_api.get_service") as gs:
            svc = gs.return_value
            svc.cached_result.return_value = stale
            svc.scan_progress.return_value = {"running": True}
            r = self._client().get("/api/game-library")
        assert r.status_code == 200
        svc.scan_async.assert_not_called()
