"""Installed-games scanner tests — only verified installs may be reported."""
import errno
import os
from unittest.mock import patch

from core.installed_games import (
    STATUS_MISSING,
    STATUS_VERIFIED,
    _verify_path,
    scan_installed_games,
    STEAM_APPID_FALLBACK,
)

PROFILES = [
    {"id": "cs2", "name": "Counter-Strike 2"},
    {"id": "valorant", "name": "Valorant"},
    {"id": "gta5", "name": "Grand Theft Auto V"},
    {"id": "rust", "name": "Rust"},
    {"id": "rainbow6", "name": "Rainbow Six Siege"},
    {"id": "warzone", "name": "Call of Duty: Warzone"},
]


def _steam_root(tmp_path, name: str, appid: int, *, install: bool = True) -> str:
    """A Steam library whose manifest points at a real (or removed) folder."""
    apps = tmp_path / "steamapps"
    apps.mkdir(parents=True, exist_ok=True)
    installdir = name.replace(":", "").replace(" ", "")
    if install:
        game_dir = apps / "common" / installdir
        game_dir.mkdir(parents=True)
        (game_dir / "game.exe").write_text("")
    (apps / f"appmanifest_{appid}.acf").write_text(
        '"AppState"\n{\n'
        f'  "appid"\t"{appid}"\n'
        f'  "name"\t"{name}"\n'
        f'  "installdir"\t"{installdir}"\n'
        '  "StateFlags"\t"4"\n'
        "}"
    )
    return str(tmp_path)


def _registry_entry(name: str, status: str, path: str | None = None):
    return {
        "name": name,
        "appid": None,
        "source": "registry",
        "status": status,
        "reason": "test evidence",
        "install_path": path,
    }


def test_steam_manifest_match(tmp_path):
    root = _steam_root(tmp_path, "Counter-Strike 2", 730)
    scan = scan_installed_games(PROFILES, steam_root=root)
    assert scan["matched"] == [{
        "profile_id": "cs2",
        "name": "Counter-Strike 2",
        "source": "steam",
        "status": STATUS_VERIFIED,
        "appid": 730,
        "install_path": str(tmp_path / "steamapps" / "common" / "Counter-Strike2"),
        "evidence": scan["matched"][0]["evidence"],
    }]
    assert scan["others"] == []
    assert scan["unverified"] == []


def test_steam_manifest_with_removed_folder_is_not_installed(tmp_path):
    """A stale manifest (path gone) is `missing`, never an installed game."""
    root = _steam_root(tmp_path, "Counter-Strike 2", 730, install=False)
    scan = scan_installed_games(PROFILES, steam_root=root)
    assert scan["matched"] == []
    assert [u["profile_id"] for u in scan["unverified"]] == ["cs2"]
    assert scan["unverified"][0]["status"] == STATUS_MISSING


def test_registry_match_and_appid_fallback():
    def fake_registry():
        return [_registry_entry("Counter-Strike 2", STATUS_VERIFIED, r"C:\Games\CS2")]

    with patch("core.installed_games._steam_games", return_value=[]), \
         patch("core.installed_games._registry_games", side_effect=fake_registry):
        scan = scan_installed_games(PROFILES)
    ids = {(g["profile_id"], g["appid"]) for g in scan["matched"]}
    assert ("cs2", 730) in ids
    assert all(g.get("appid") for g in scan["matched"] if g["profile_id"] == "cs2")


def test_name_only_registry_record_is_a_candidate_not_installed():
    """DisplayName without a verifiable path is not installation evidence."""
    def fake_registry():
        return [_registry_entry("Call of Duty: Warzone", "candidate")]

    with patch("core.installed_games._steam_games", return_value=[]), \
         patch("core.installed_games._registry_games", side_effect=fake_registry):
        scan = scan_installed_games(PROFILES)
    assert scan["matched"] == []
    assert [u["profile_id"] for u in scan["unverified"]] == ["warzone"]
    assert scan["unverified"][0]["status"] == "candidate"


def test_stale_registry_record_is_missing_not_installed():
    def fake_registry():
        return [_registry_entry("Call of Duty: Warzone", STATUS_MISSING, r"Z:\gone")]

    with patch("core.installed_games._steam_games", return_value=[]), \
         patch("core.installed_games._registry_games", side_effect=fake_registry):
        scan = scan_installed_games(PROFILES)
    assert scan["matched"] == []
    assert scan["unverified"][0]["status"] == STATUS_MISSING


def test_call_of_duty_alone_does_not_match_warzone():
    """A base Call of Duty install is not evidence that Warzone is installed."""
    def fake_registry():
        return [_registry_entry("Call of Duty", STATUS_VERIFIED, r"C:\Games\COD")]

    with patch("core.installed_games._steam_games", return_value=[]), \
         patch("core.installed_games._registry_games", side_effect=fake_registry):
        scan = scan_installed_games(PROFILES)
    assert all(m["profile_id"] != "warzone" for m in scan["matched"])


def test_verified_title_with_extra_words_matches():
    def fake_registry():
        return [_registry_entry("Tom Clancy's Rainbow Six Siege", STATUS_VERIFIED, r"C:\Games\R6")]

    with patch("core.installed_games._steam_games", return_value=[]), \
         patch("core.installed_games._registry_games", side_effect=fake_registry):
        scan = scan_installed_games(PROFILES)
    assert [m["profile_id"] for m in scan["matched"]] == ["rainbow6"]


def test_verify_path_states(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    assert _verify_path(str(empty), want_dir=True)[0] == STATUS_MISSING
    populated = tmp_path / "populated"
    populated.mkdir()
    (populated / "file.bin").write_text("x")
    (populated / "game.exe").write_text("")
    assert _verify_path(str(populated), want_dir=True)[0] == STATUS_VERIFIED
    assert _verify_path(str(tmp_path / "gone"), want_dir=True)[0] == STATUS_MISSING
    exe = populated / "game.exe"
    assert _verify_path(str(exe), want_dir=False)[0] == STATUS_VERIFIED
    assert _verify_path("", want_dir=True)[0] == "candidate"


def test_inaccessible_install_path_is_unknown_not_installed(tmp_path):
    """A path the process cannot read is `unknown`, never an installed game."""
    denied = str(tmp_path / "denied")
    real_stat = os.stat

    def fake_stat(path, *args, **kwargs):
        if str(path) == denied:
            raise PermissionError(errno.EACCES, "access denied", denied)
        return real_stat(path, *args, **kwargs)

    with patch("core.installed_games.os.stat", side_effect=fake_stat):
        status, reason = _verify_path(denied, want_dir=True)
    assert status == "unknown"
    assert "could not be read" in reason

    def fake_registry():
        return [_registry_entry("Call of Duty: Warzone", "unknown", denied)]

    with patch("core.installed_games._steam_games", return_value=[]), \
         patch("core.installed_games._registry_games", side_effect=fake_registry):
        scan = scan_installed_games(PROFILES)
    assert scan["matched"] == []
    assert scan["unverified"][0]["status"] == "unknown"


def test_profile_with_no_installed_game_is_absent():
    """Profiles are a catalog, not evidence: no scan hit means no installed game."""
    with patch("core.installed_games._steam_games", return_value=[]), \
         patch("core.installed_games._registry_games", return_value=[]):
        scan = scan_installed_games(PROFILES)
    assert scan["matched"] == []
    assert scan["others"] == []
    assert scan["unverified"] == []


def test_duplicate_registry_records_keep_the_verified_copy():
    """A stale duplicate must never shadow the verified install record."""
    from core.installed_games import _dedupe_registry

    entries = [
        _registry_entry("Counter-Strike 2", "candidate", None),
        _registry_entry("Counter-Strike 2", STATUS_VERIFIED, r"C:\Games\CS2"),
    ]
    kept = _dedupe_registry(entries)
    assert len(kept) == 1
    assert kept[0]["status"] == STATUS_VERIFIED
    assert kept[0]["install_path"] == r"C:\Games\CS2"


def test_unknown_titles_ignored():
    def fake_registry():
        return [_registry_entry("Some Random Utility", STATUS_VERIFIED, r"C:\Apps\Util")]

    with patch("core.installed_games._steam_games", return_value=[]), \
         patch("core.installed_games._registry_games", side_effect=fake_registry):
        scan = scan_installed_games(PROFILES)
    assert scan["matched"] == []
    assert scan["unverified"] == []
    assert scan["others"] == []


def test_profileless_steam_install_reported_and_noise_skipped(tmp_path):
    """A verified Steam game with no profile appears in others; redists do not."""
    root = _steam_root(tmp_path, "Wuthering Waves", 3513350)
    apps = tmp_path / "steamapps"
    (apps / "common" / "Steamworks").mkdir()
    (apps / "appmanifest_228980.acf").write_text(
        '"AppState"\n{\n  "appid"\t"228980"\n'
        '  "name"\t"Steamworks Common Redistributables"\n'
        '  "installdir"\t"Steamworks"\n  "StateFlags"\t"4"\n}'
    )
    scan = scan_installed_games(PROFILES, steam_root=root)
    assert scan["matched"] == []
    assert scan["others"] == [{
        "name": "Wuthering Waves",
        "source": "steam",
        "status": STATUS_VERIFIED,
        "appid": 3513350,
    }]


def test_short_ids_never_match_alone():
    """'cs2' is 3 chars; the id must not fuzzy-match unrelated titles."""
    def fake_registry():
        return [_registry_entry("CS Umbrella Ltd stuff", STATUS_VERIFIED, r"C:\Apps\CS")]

    with patch("core.installed_games._steam_games", return_value=[]), \
         patch("core.installed_games._registry_games", side_effect=fake_registry):
        scan = scan_installed_games(PROFILES)
    assert not any(g["profile_id"] != "cs2" and g.get("source") == "registry" for g in scan["matched"])


def test_appid_fallback_table_is_scoped_to_real_titles():
    """The artwork table must never be used to invent a detection."""
    assert STEAM_APPID_FALLBACK["call of duty: warzone"] == 1938090
    assert "call of duty" not in STEAM_APPID_FALLBACK
