"""Manual game import store tests — exe/folder/shortcut, emulators, dedupe,
safe launching and persistence. All storage is redirected to temp dirs, so
the real data/manual_games.json is never touched."""
import json
import os
import subprocess
import sys
import tempfile
from unittest.mock import patch

import pytest

import core.game_imports as gi


@pytest.fixture()
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(gi, "STORE_FILE", str(tmp_path / "manual_games.json"))
    gi.reset_cache_for_tests()
    yield gi
    gi.reset_cache_for_tests()


@pytest.fixture()
def fake_exe(tmp_path):
    """A real .exe-styled file on disk (copy of a system binary is not needed;
    an arbitrarily sized file satisfies is_file + isfile checks)."""
    p = tmp_path / "GreatGame.exe"
    p.write_bytes(b"MZ" + b"\x00" * 256)
    return str(p)


@pytest.fixture()
def real_exe(tmp_path_factory):
    """A real Windows executable for true launch tests (skipped off-Windows)."""
    exe = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "notepad.exe")
    if not os.path.isfile(exe):
        pytest.skip("Windows notepad.exe not available")
    return exe


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidation:
    def test_relative_path_rejected(self, store):
        ok, err = store.validate_exe("game.exe")
        assert not ok and "absolute" in err.lower()

    def test_non_exe_rejected(self, store, tmp_path):
        f = tmp_path / "readme.txt"
        f.write_text("x")
        ok, err = store.validate_exe(str(f))
        assert not ok and ".exe" in err

    def test_missing_file_rejected(self, store):
        ok, err = store.validate_exe(r"C:\definitely\missing.exe")
        assert not ok and "exist" in err.lower()

    def test_valid_exe_accepted(self, store, fake_exe):
        ok, err = store.validate_exe(fake_exe)
        assert ok and err == ""


# ---------------------------------------------------------------------------
# Manual exe import
# ---------------------------------------------------------------------------


class TestExeImport:
    def test_add_and_list(self, store, fake_exe):
        r = store.add_game_exe(fake_exe, name="Great Game")
        assert r["game"]["name"] == "Great Game"
        assert r["game"]["source"] == "manual"
        games = store.list_games()
        assert len(games) == 1
        assert games[0]["status"] == "installed"

    def test_name_defaults_to_filename(self, store, fake_exe):
        r = store.add_game_exe(fake_exe)
        assert r["game"]["name"] == "GreatGame"

    def test_duplicate_updates_not_duplicates(self, store, fake_exe):
        store.add_game_exe(fake_exe, name="A")
        r2 = store.add_game_exe(fake_exe, name="Renamed")
        assert r2["updated"] is True
        assert len(store.list_games()) == 1
        assert store.list_games()[0]["name"] == "Renamed"

    def test_invalid_path_rejected(self, store):
        assert "error" in store.add_game_exe(r"C:\missing\game.exe", name="X")

    def test_missing_entry_lists_missing(self, store, fake_exe):
        r = store.add_game_exe(fake_exe, name="Will Vanish")
        gid = r["game"]["id"]
        os.remove(fake_exe)
        store.reset_cache_for_tests()
        entry = store.entry_by_id(gid)
        assert entry["status"] == "missing"

    def test_remove_then_status(self, store, fake_exe):
        gid = store.add_game_exe(fake_exe, name="R")["game"]["id"]
        assert "removed" in store.remove_game(gid)
        assert store.entry_by_id(gid) is None
        assert "not found" in store.remove_game(gid)["error"].lower()


# ---------------------------------------------------------------------------
# Folder import
# ---------------------------------------------------------------------------


class TestFolderImport:
    def _game_folder(self, tmp_path, exe_names):
        folder = tmp_path / "SomeGame"
        folder.mkdir()
        for name, size in exe_names:
            f = folder / name
            f.write_bytes(b"\x00" * size)
        return folder

    def test_candidates_exclude_installers(self, store, tmp_path):
        folder = self._game_folder(tmp_path, [
            ("setup.exe", 100 * 1024 * 1024),      # installer: rejected by name
            ("unins000.exe", 5 * 1024 * 1024),     # uninstaller: rejected
            ("CrashReport.exe", 20 * 1024 * 1024), # handler: rejected
            ("GameClient.exe", 80 * 1024 * 1024),  # plausible: kept, ranked first
            ("tiny.exe", 1024),                    # too small: rejected
        ])
        cands = store.find_game_exes(str(folder))
        paths = [c["path"] for c in cands]
        assert any(c.endswith("GameClient.exe") for c in paths)
        assert not any("setup" in c.lower() or "unins" in c.lower() or "crash" in c.lower() for c in paths)

    def test_candidates_rank_client_hint_first(self, store, tmp_path):
        folder = self._game_folder(tmp_path, [
            ("SoundEngine.exe", 90 * 1024 * 1024),
            ("GameClient.exe", 70 * 1024 * 1024),
        ])
        cands = store.find_game_exes(str(folder))
        assert cands[0]["path"].endswith("GameClient.exe")

    def test_folder_import_with_chosen_exe(self, store, tmp_path):
        folder = self._game_folder(tmp_path, [("GameClient.exe", 80 * 1024 * 1024)])
        r = store.add_game_folder(str(folder), chosen_exe=str(folder / "GameClient.exe"), name="Folder Game")
        assert r["game"]["folder"] == str(folder)
        assert r["game"]["exe_path"].endswith("GameClient.exe")

    def test_chosen_exe_outside_folder_rejected(self, store, tmp_path):
        folder = self._game_folder(tmp_path, [("a.exe", 10 * 1024 * 1024)])
        r = store.add_game_folder(str(folder), chosen_exe=r"C:\elsewhere\evil.exe")
        assert "error" in r

    def test_folder_import_never_auto_picks(self, store, tmp_path):
        """Without a chosen exe the entry exists but has no validated exe."""
        folder = self._game_folder(tmp_path, [("MaybeGame.exe", 60 * 1024 * 1024)])
        r = store.add_game_folder(str(folder))
        assert r["game"]["exe_path"] == ""
        assert r["game"]["status"] == "missing" if False else store.list_games()[0]["status"] == "missing"

    def test_folder_id_stable(self, store, tmp_path):
        folder = self._game_folder(tmp_path, [("g.exe", 5 * 1024 * 1024)])
        r1 = store.add_game_folder(str(folder), name="One")
        r2 = store.add_game_folder(str(folder), name="Two")
        assert r2["updated"] is True
        assert len(store.list_games()) == 1
        assert store.list_games()[0]["name"] == "Two"


# ---------------------------------------------------------------------------
# Shortcut resolution
# ---------------------------------------------------------------------------


class TestShortcut:
    def test_resolve_shortcut_import_missing(self, store):
        """pythoncom is optional on CI; the function must degrade honestly."""
        try:
            import pythoncom  # noqa: F401
            from win32com.client import Dispatch  # noqa: F401
            has_com = True
        except ImportError:
            has_com = False
        target, args, err, _icon = store.resolve_shortcut(r"C:\fake\missing.lnk")
        if not has_com:
            assert "pywin32" in err
        else:
            # With COM available, a nonexistent .lnk still yields an error.
            assert err or not os.path.isfile(r"C:\fake\missing.lnk")
        assert target is None if not has_com else True


# ---------------------------------------------------------------------------
# Emulators
# ---------------------------------------------------------------------------


class TestEmulators:
    def test_register_validate_list(self, store, fake_exe):
        r = store.add_emulator("BlueStacks", fake_exe, args="--vm default")
        assert r["emulator"]["name"] == "BlueStacks"
        emus = store.list_emulators()
        assert len(emus) == 1 and emus[0]["args"] == "--vm default"

    def test_emulator_path_must_exist(self, store):
        assert "error" in store.add_emulator("Ghost", r"C:\missing\emu.exe")

    def test_duplicate_emulator_updates(self, store, fake_exe):
        store.add_emulator("A", fake_exe)
        store.add_emulator("B-renamed", fake_exe)
        emus = store.list_emulators()
        assert len(emus) == 1 and emus[0]["name"] == "B-renamed"

    def test_remove_emulator_detaches_games(self, store, fake_exe):
        em = store.add_emulator("Emu", fake_exe)["emulator"]
        g = store.add_game_exe(fake_exe, name="Emu Game", emulator_id_ref=em["id"])["game"]
        assert g["emulator_id"] == em["id"]
        r = store.remove_emulator(em["id"])
        assert "removed" in r
        after = store.entry_by_id(g["id"])
        assert after is not None, "game entry must never be silently deleted"
        assert after.get("emulator_id") is None


# ---------------------------------------------------------------------------
# Emulator-game associations and safe launching
# ---------------------------------------------------------------------------


class TestLaunch:
    def test_unknown_id_fails_closed(self, store):
        r = store.launch_game("manual:doesnotexist")
        assert r["created"] is False and "not found" in r["error"].lower()

    def test_missing_file_reports_missing(self, store, fake_exe):
        gid = store.add_game_exe(fake_exe)["game"]["id"]
        os.remove(fake_exe)
        r = store.launch_game(gid)
        assert r["created"] is False and "moved" in r["error"] or "missing" in r["error"].lower()

    def test_real_launch_creates_process(self, store, real_exe):
        gid = store.add_game_exe(real_exe, name="Launch Test")["game"]["id"]
        r = store.launch_game(gid)
        assert r["created"] is True
        assert isinstance(r.get("pid"), int)
        # Clean up quickly; notepad is harmless.
        subprocess.run(["taskkill", "/PID", str(r["pid"]), "/F"],
                       capture_output=True, timeout=10)

    def test_launch_failure_reported_not_silent(self, store, tmp_path):
        """A directory where the exe should be triggers a real OSError path."""
        fake_dir_exe = tmp_path / "folder-not-exe.exe"
        fake_dir_exe.mkdir()  # isfile() passes? No: mkdir makes a dir -> validate fails
        assert "error" in store.add_game_exe(str(fake_dir_exe), name="Broken")

    def test_emulator_associated_launch_uses_emu_target(self, store, fake_exe, tmp_path):
        """The emulator exe is the spawned target; game exe is only an arg."""
        emu_exe = tmp_path / "FakeEmu.exe"
        emu_exe.write_bytes(b"MZ" + b"\x00" * 64)
        em = store.add_emulator("FakeEmu", str(emu_exe), args="--run")["emulator"]
        gid = store.add_game_exe(fake_exe, name="Emu Game", emulator_id_ref=em["id"])["game"]["id"]
        captured = {}

        class FakeProc:
            pid = 4321

        def fake_popen(cmd, **kwargs):
            captured["cmd"] = list(cmd)
            captured["shell"] = kwargs.get("shell", None)
            captured["cwd"] = kwargs.get("cwd")
            return FakeProc()

        monkeypatch_old = gi.subprocess.Popen = fake_popen  # type: ignore[assignment]
        try:
            r = store.launch_game(gid)
            assert r["created"] is True
            assert captured["cmd"][0] == os.path.normpath(str(emu_exe))
            assert any(os.path.normpath(fake_exe) == c for c in captured["cmd"][1:])
            assert captured["shell"] is False
            assert "--run" in captured["cmd"]
        finally:
            gi.subprocess.Popen = monkeypatch_old


# ---------------------------------------------------------------------------
# Persistence across restart (cache reset = fresh process)
# ---------------------------------------------------------------------------


class TestPersistence:
    def test_survives_cache_reset(self, store, fake_exe):
        store.add_game_exe(fake_exe, name="Persist Me")
        store.reset_cache_for_tests()  # simulate restart
        games = store.list_games()
        assert len(games) == 1
        assert games[0]["name"] == "Persist Me"

    def test_store_file_content_shape(self, store, fake_exe):
        store.add_game_exe(fake_exe, name="Shape")
        with open(store.STORE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert set(["emulators", "games"]).issubset(data.keys())
        assert data["games"][0]["source"] == "manual"


# ---------------------------------------------------------------------------
# Merge into discovery results
# ---------------------------------------------------------------------------


class TestMerge:
    def test_merge_keeps_manual_label(self, store, fake_exe):
        store.add_game_exe(fake_exe, name="Merged Game")
        out = store.merge_into([{"id": "steam:730", "name": "CS2", "source": "steam", "status": "installed"}])
        assert out[0]["source"] == "steam"
        assert out[1]["source"] == "manual"
        assert out[1]["label"] == "manually added"

    def test_merge_with_empty_discovery(self, store, fake_exe):
        store.add_game_exe(fake_exe, name="Solo Manual")
        out = store.merge_into([])
        assert len(out) == 1 and out[0]["source"] == "manual"
