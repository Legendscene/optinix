"""Discovery-coverage rules: emulators, registry path evidence, honest
missing records and diagnostics wording.

Registry and filesystem are stubbed at the adapter seams
(EmulatorAdapter._registry_entries / _known_dirs, core.game_discovery._Registry,
os.path.isfile/getsize), so no real machine state is read or mutated. These
tests pin the RULES; a live rescan on a real machine is a separate check.
"""
import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core.game_discovery as gd  # noqa: E402
from core.game_discovery import (  # noqa: E402
    EmulatorAdapter, EpicAdapter, StartMenuShortcutAdapter, UninstallAdapter,
    STATUS_INSTALLED, STATUS_MISSING,
)


def _cancel():
    return gd._Cancel()


# ---------------------------------------------------------------------------
# EmulatorAdapter — two witnesses, both file-verified
# ---------------------------------------------------------------------------
@pytest.mark.skipif(os.name != "nt", reason="emulator discovery is Windows-only")
class TestEmulatorAdapter:
    def test_known_dir_with_player_exe_is_an_emulator(self, tmp_path):
        root = tmp_path / "BlueStacks_msi5"
        root.mkdir()
        exe = root / "HD-Player.exe"
        exe.write_bytes(b"MZ" * 32)
        with patch.object(EmulatorAdapter, "_known_dirs",
                          return_value=[(str(root), "MSI App Player")]), \
             patch.object(EmulatorAdapter, "_registry_entries", return_value=[]):
            games, _notes = EmulatorAdapter().scan(_cancel())
        assert len(games) == 1
        g = games[0]
        assert g["kind"] == "emulator"
        assert g["source"] == "emulator"
        assert g["name"] == "MSI App Player"
        assert g["status"] == STATUS_INSTALLED
        assert g["install_path"] == str(root)
        assert g["exe_path"] and os.path.basename(g["exe_path"]) == "HD-Player.exe"

    def test_known_dir_without_player_exe_proves_nothing(self, tmp_path):
        """A folder merely NAMED like an emulator (leftover uninstall) is
        not an emulator install — no record without its player executable."""
        root = tmp_path / "PCSX2"
        root.mkdir()
        (root / "unins000.exe").write_bytes(b"MZ" * 8)
        with patch.object(EmulatorAdapter, "_known_dirs",
                          return_value=[(str(root), "PCSX2")]), \
             patch.object(EmulatorAdapter, "_registry_entries", return_value=[]):
            games, notes = EmulatorAdapter().scan(_cancel())
        assert games == []
        assert any("No known emulators" in n for n in notes)

    def test_registry_entry_with_existing_dir_is_installed(self, tmp_path):
        root = tmp_path / "Nox"
        root.mkdir()
        (root / "nox.exe").write_bytes(b"MZ" * 32)
        with patch.object(EmulatorAdapter, "_known_dirs", return_value=[]), \
             patch.object(EmulatorAdapter, "_registry_entries",
                          return_value=[("NoxPlayer 7", str(root))]):
            games, _notes = EmulatorAdapter().scan(_cancel())
        assert len(games) == 1
        assert games[0]["name"] == "NoxPlayer 7"  # registry's own display name
        assert games[0]["kind"] == "emulator"
        assert games[0]["status"] == STATUS_INSTALLED
        assert games[0]["exe_path"] and games[0]["exe_path"].endswith("nox.exe")

    def test_registry_entry_without_any_path_is_dropped(self, tmp_path):
        """A name alone (no install location) cannot be verified — the
        record is never emitted, installed or missing."""
        with patch.object(EmulatorAdapter, "_known_dirs", return_value=[]), \
             patch.object(EmulatorAdapter, "_registry_entries",
                          return_value=[("MuMu Player 12", "")]):
            games, _notes = EmulatorAdapter().scan(_cancel())
        assert games == []

    def test_registry_entry_with_vanished_dir_is_a_missing_record(self, tmp_path):
        gone = tmp_path / "LDPlayer9"  # never created
        with patch.object(EmulatorAdapter, "_known_dirs", return_value=[]), \
             patch.object(EmulatorAdapter, "_registry_entries",
                          return_value=[("LDPlayer 9", str(gone))]):
            games, _notes = EmulatorAdapter().scan(_cancel())
        assert len(games) == 1
        assert games[0]["status"] == STATUS_MISSING
        assert games[0]["install_path"] == str(gone)
        assert games[0]["exe_path"] is None


# ---------------------------------------------------------------------------
# Start Menu: console emulators must not be labeled as games
# ---------------------------------------------------------------------------
@pytest.mark.skipif(os.name != "nt", reason="Start Menu discovery is Windows-only")
class TestConsoleEmulatorLabeling:
    def _write_lnk(self, dirpath, rel):
        p = os.path.join(str(dirpath), rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(b"L\x00\x00\x00" + b"\x00" * 64)
        return p

    def test_dolphin_shortcut_is_emulator_not_game(self, tmp_path):
        """The player binary is small; before the emulator-exe list covered
        console players, the size heuristic labeled PCSX2/Dolphin/etc. as
        native 'games' — a false game card."""
        lnk = self._write_lnk(tmp_path, "Programs/Dolphin Emulator.lnk")
        with patch.object(StartMenuShortcutAdapter, "_shortcut_files", return_value=[lnk]), \
             patch.object(StartMenuShortcutAdapter, "_resolve",
                          return_value=(r"C:\Emulators\Dolphin\Dolphin.exe|", "")), \
             patch("core.game_discovery.os.path.isfile", return_value=True), \
             patch("core.game_discovery.os.path.getsize", return_value=512 * 1024):
            games, _ = StartMenuShortcutAdapter().scan(_cancel())
        assert len(games) == 1
        assert games[0]["kind"] == "emulator"
        assert games[0]["status"] == STATUS_INSTALLED

    def test_pcsx2_shortcut_is_emulator_not_game(self, tmp_path):
        lnk = self._write_lnk(tmp_path, "Programs/PCSX2.lnk")
        with patch.object(StartMenuShortcutAdapter, "_shortcut_files", return_value=[lnk]), \
             patch.object(StartMenuShortcutAdapter, "_resolve",
                          return_value=(r"C:\Emulators\PCSX2\pcsx2-qt.exe|", "")), \
             patch("core.game_discovery.os.path.isfile", return_value=True), \
             patch("core.game_discovery.os.path.getsize", return_value=512 * 1024):
            games, _ = StartMenuShortcutAdapter().scan(_cancel())
        assert len(games) == 1
        assert games[0]["kind"] == "emulator"
        assert games[0]["status"] == STATUS_INSTALLED


# ---------------------------------------------------------------------------
# Uninstall registry: path evidence + honest missing records
# ---------------------------------------------------------------------------
class _FakeRegistry:
    """Enough of _Registry's surface: one uninstall entry per subkey index."""

    def __init__(self, entries):
        self.entries = entries

    def open(self, hive, path):
        return ("sub", path) if isinstance(path, int) else ("root", path)

    def subkeys(self, key):
        return list(range(len(self.entries)))

    def read(self, key, name):
        if key[0] != "sub":
            return None
        return self.entries[key[1]].get(name)

    def close(self, key):
        pass


@pytest.mark.skipif(os.name != "nt", reason="registry discovery is Windows-only")
class TestUninstallPathEvidence:
    def _scan(self, entries, monkeypatch):
        monkeypatch.setattr(gd, "_Registry", _FakeRegistry(entries))
        return UninstallAdapter().scan(_cancel())[0]

    def test_game_without_gameish_name_found_via_steam_path(self, tmp_path, monkeypatch):
        """'Marvel Rivals' has no colon/game-word in its name — the path
        inside steamapps\\common is the evidence that catches it."""
        loc = tmp_path / "steamapps" / "common" / "MarvelRivals"
        loc.mkdir(parents=True)
        games = self._scan([{
            "DisplayName": "Marvel Rivals",
            "InstallLocation": str(loc),
            "DisplayIcon": "",
        }], monkeypatch)
        assert len(games) == 1
        assert games[0]["name"] == "Marvel Rivals"
        assert games[0]["status"] == STATUS_INSTALLED

    def test_disconnected_drive_game_is_missing_not_dropped(self, tmp_path, monkeypatch):
        """A real registered location whose files are absent right now
        (drive unplugged) surfaces as an honest missing record instead of
        silently vanishing from the library."""
        loc = tmp_path / "steamapps" / "common" / "CarMechanicSimulator2018"  # never created
        games = self._scan([{
            "DisplayName": "Car Mechanic Simulator 2018",
            "InstallLocation": str(loc),
            "DisplayIcon": "",
        }], monkeypatch)
        assert len(games) == 1
        assert games[0]["status"] == STATUS_MISSING
        assert games[0]["install_path"] == str(loc)

    def test_launcher_name_rejected_even_from_a_games_folder(self, tmp_path, monkeypatch):
        """'…\\Rockstar Games\\Launcher' is a launcher, not a game — the
        denylist outranks path evidence."""
        loc = tmp_path / "Games" / "LauncherDir"
        loc.mkdir(parents=True)
        games = self._scan([{
            "DisplayName": "Rockstar Games Launcher",
            "InstallLocation": str(loc),
            "DisplayIcon": "",
        }], monkeypatch)
        assert games == []

    def test_tool_name_without_evidence_rejected(self, tmp_path, monkeypatch):
        loc = tmp_path / "AMDCIM"
        loc.mkdir()
        games = self._scan([{
            "DisplayName": "AMD Software",
            "InstallLocation": str(loc),
            "DisplayIcon": "",
        }], monkeypatch)
        assert games == []

    def test_game_name_without_any_path_is_still_dropped(self, tmp_path, monkeypatch):
        """Name evidence alone with NO location and NO icon cannot be
        verified (e.g. a Steam entry — the Steam adapter owns those)."""
        games = self._scan([{
            "DisplayName": "Wuthering Waves",
            "InstallLocation": "",
            "DisplayIcon": "",
        }], monkeypatch)
        assert games == []

    def test_steam_app_on_absent_drive_is_missing_with_appid_and_artwork(self, tmp_path, monkeypatch):
        """Steam's uninstall keys point at a library whose drive is not
        connected right now: the card survives as an honest 'missing' with
        the appid (CDN cover art) and the cached .ico (offline cover art) —
        but never an exe, so nothing pretends to be launchable."""
        icon = tmp_path / "marvel.ico"
        icon.write_bytes(b"\x00\x00\x01\x00" + b"\x00" * 200)
        loc = str(tmp_path / "GhostLibrary" / "steamapps" / "common" / "MarvelRivals")  # never created
        games = self._scan([{
            "DisplayName": "Marvel Rivals",
            "InstallLocation": loc,
            "DisplayIcon": str(icon),
            "UninstallString": '"C:\\Program Files (x86)\\Steam\\steam.exe" steam://uninstall/2767030',
        }], monkeypatch)
        assert len(games) == 1
        g = games[0]
        assert g["status"] == STATUS_MISSING
        assert g["install_path"] == loc
        assert g["exe_path"] is None, "a cached .ico must never be a launch target"
        assert g["icon_path"] == str(icon), "the icon rides along as cover-art source"
        assert g["appid"] == 2767030, "the Steam appid ties it to CDN artwork"

    def test_icon_only_entry_keeps_an_honest_card(self, tmp_path, monkeypatch):
        """No InstallLocation, just a launcher icon: the card must not vanish
        (the user asked for every detected game) — it is honestly 'missing'
        with the icon as artwork and nothing launchable."""
        icon = tmp_path / "cool.ico"
        icon.write_bytes(b"\x00\x00\x01\x00" + b"\x00" * 200)
        games = self._scan([{
            "DisplayName": "Cool Game",
            "InstallLocation": "",
            "DisplayIcon": str(icon),
        }], monkeypatch)
        assert len(games) == 1
        g = games[0]
        assert g["status"] == STATUS_MISSING
        assert g["install_path"] is None and g["exe_path"] is None
        assert g["icon_path"] == str(icon)

    def test_installed_game_with_icon_does_not_use_ico_as_exe(self, tmp_path, monkeypatch):
        """A verified location resolves its own exe; the .ico rides along as
        icon_path for cover art, never as exe_path."""
        loc = tmp_path / "Games" / "CoolGame"
        loc.mkdir(parents=True)
        icon = tmp_path / "cool.ico"
        icon.write_bytes(b"\x00\x00\x01\x00" + b"\x00" * 200)
        games = self._scan([{
            "DisplayName": "Cool Game",
            "InstallLocation": str(loc),
            "DisplayIcon": str(icon),
        }], monkeypatch)
        assert len(games) == 1
        g = games[0]
        assert g["status"] == STATUS_INSTALLED
        assert g["install_path"] == str(loc)
        assert not (g["exe_path"] or "").lower().endswith(".ico")
        assert g["icon_path"] == str(icon)


# ---------------------------------------------------------------------------
# Epic diagnostics: launcher-present differs from absent
# ---------------------------------------------------------------------------
@pytest.mark.skipif(os.name != "nt", reason="Epic discovery is Windows-only")
class TestEpicDiagnosticsNote:
    def test_launcher_without_manifests_says_installed_not_missing(self, tmp_path, monkeypatch):
        pdata = tmp_path / "ProgramData"
        (pdata / "Epic" / "EpicGamesLauncher").mkdir(parents=True)  # launcher, no Data/Manifests
        empty_pf = tmp_path / "pf"
        monkeypatch.setenv("PROGRAMDATA", str(pdata))
        monkeypatch.setenv("ProgramFiles(x86)", str(empty_pf / "x86"))
        monkeypatch.setenv("ProgramFiles", str(empty_pf))
        _games, notes = EpicAdapter().scan(_cancel())
        assert any("Launcher installed but no games registered" in n for n in notes), notes
        assert not any("not found" in n for n in notes)

    def test_epic_absent_reports_not_found(self, tmp_path, monkeypatch):
        empty = tmp_path / "empty"
        monkeypatch.setenv("PROGRAMDATA", str(empty))
        monkeypatch.setenv("ProgramFiles(x86)", str(empty))
        monkeypatch.setenv("ProgramFiles", str(empty))
        _games, notes = EpicAdapter().scan(_cancel())
        assert any("not found" in n for n in notes), notes
