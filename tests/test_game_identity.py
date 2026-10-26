"""Game identity tests — a game is only 'running' when its own exe is.

Regression: the old detector substring-matched profile keywords against a
process' name, path and full command line. Warzone's keyword was "cod", which
matches code.exe, vscode and any shell running something under a path with
"code" in it — so machines with no Call of Duty install reported Warzone.
"""
import os

import pytest

from core.game_profiles import GameProfiles


class _Proc:
    def __init__(self, pid: int, name: str, exe: str):
        self.info = {"pid": pid, "name": name, "exe": exe}


def _patch_processes(monkeypatch, procs):
    import psutil
    monkeypatch.setattr(psutil, "process_iter", lambda attrs=None: procs)


@pytest.fixture
def engine():
    return GameProfiles()


def test_cod_keyword_processes_are_not_warzone(monkeypatch, engine, tmp_path):
    """Editors/shells containing 'cod' are not Call of Duty."""
    txt = tmp_path / "Code.exe"
    txt.write_text("")
    bash = tmp_path / "bash.exe"
    bash.write_text("")
    cod = tmp_path / "cod.exe"
    cod.write_text("")
    _patch_processes(monkeypatch, [
        _Proc(1, "Code.exe", str(txt)),
        _Proc(2, "bash.exe", str(bash)),
        _Proc(3, "cmd.exe", ""),
        _Proc(4, "cod.exe", str(cod)),
    ])

    hits = engine.detect_running_games()
    assert [h["id"] for h in hits] == ["warzone"]
    assert hits[0]["exe"] == str(cod)
    assert engine.detect_running_game() == "warzone"


def test_process_without_an_existing_exe_is_not_evidence(monkeypatch, engine, tmp_path):
    """A name alone (access denied / spoofed process) proves nothing."""
    _patch_processes(monkeypatch, [
        _Proc(1, "cod.exe", ""),
        _Proc(2, "warzone.exe", str(tmp_path / "missing" / "warzone.exe")),
    ])
    assert engine.detect_running_games() == []
    assert engine.detect_running_game() is None


def test_unmapped_process_never_reports_a_game(monkeypatch, engine):
    """A generic runtime (javaw) must not be guessed as Minecraft."""
    _patch_processes(monkeypatch, [_Proc(1, "javaw.exe", "")])
    assert engine.detect_running_games() == []


def test_installation_evidence_is_false_when_nothing_is_installed(monkeypatch, engine):
    monkeypatch.setattr(engine, "detect_running_games", lambda: [])
    monkeypatch.setattr(
        "core.installed_games.scan_installed_games",
        lambda profiles: {"matched": [], "others": [], "unverified": []},
    )
    evidence = engine.installation_evidence("warzone")
    assert evidence["verified"] is False
    assert evidence["status"] == "missing"


def test_installation_evidence_accepts_verified_scan(monkeypatch, engine):
    monkeypatch.setattr(engine, "detect_running_games", lambda: [])
    monkeypatch.setattr(
        "core.installed_games.scan_installed_games",
        lambda profiles: {
            "matched": [{"profile_id": "warzone", "status": "verified_installed", "evidence": "ok"}],
            "others": [],
            "unverified": [],
        },
    )
    assert engine.installation_evidence("warzone")["verified"] is True


def test_apply_is_blocked_without_verified_installation(monkeypatch, engine):
    """An uninstalled game must never have system tweaks applied for it."""
    monkeypatch.setattr(
        engine,
        "installation_evidence",
        lambda pid: {"verified": False, "status": "missing", "reason": "No installation found."},
    )

    def _must_not_run(*args, **kwargs):
        raise AssertionError("apply_profile ran system commands for an uninstalled game")

    monkeypatch.setattr("subprocess.run", _must_not_run)

    results = engine.apply_profile("warzone")
    assert len(results) == 1
    assert results[0]["success"] is False
    assert "No system changes were made" in results[0]["message"]


def test_custom_profile_is_exempt_from_game_installation(monkeypatch, engine):
    """Custom profiles are user data, not claims about a specific game."""
    monkeypatch.setattr(
        engine,
        "get_profile",
        lambda pid: {"name": "My profile", "description": "custom"},
    )
    monkeypatch.setattr(engine, "installation_evidence", lambda pid: {
        "verified": True, "status": "custom", "reason": "Custom profile",
    })
    monkeypatch.setattr("platform.system", lambda: "Linux")
    results = engine.apply_profile("my_custom")
    assert results and results[0]["success"] is False
    assert "only support Windows" in results[0]["message"]


def test_overview_detected_game_only_from_verified_process(monkeypatch):
    from core.api import overview
    from core.game_profiles import GameProfiles

    monkeypatch.setattr(GameProfiles, "detect_running_games", lambda self: [])
    assert overview._detected_game() is None

    exe = os.path.join("C:\\", "Games", "cod.exe")
    monkeypatch.setattr(GameProfiles, "detect_running_games", lambda self: [{
        "id": "warzone", "name": "Call of Duty: Warzone", "pid": 42, "exe": exe,
    }])
    detected = overview._detected_game()
    assert detected is not None
    assert detected["id"] == "warzone"
    assert detected["state"] == "running"
    assert detected["verified"] is True
    assert detected["evidence"] == {"pid": 42, "exe": exe}
