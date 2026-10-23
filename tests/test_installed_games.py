"""Installed-games scanner tests — matcher must be strict and appid-backed."""
import os
from unittest.mock import patch

from core.installed_games import scan_installed_games, STEAM_APPID_FALLBACK

PROFILES = [
    {"id": "cs2", "name": "Counter-Strike 2"},
    {"id": "valorant", "name": "Valorant"},
    {"id": "gta5", "name": "Grand Theft Auto V"},
    {"id": "rust", "name": "Rust"},
]


def _steam_root(tmp_path, name: str, appid: int) -> str:
    apps = tmp_path / "steamapps"
    apps.mkdir(parents=True)
    (apps / f"appmanifest_{appid}.acf").write_text(
        f'"AppState"\n{{\n  "appid"\t"{appid}"\n  "name"\t"{name}"\n}}'
    )
    return str(tmp_path)


def test_steam_manifest_match(tmp_path):
    root = _steam_root(tmp_path, "Counter-Strike 2", 730)
    scan = scan_installed_games(PROFILES, steam_root=root)
    assert {"profile_id": "cs2", "source": "steam", "appid": 730} in scan["matched"]
    assert len(scan["matched"]) == 1
    assert scan["others"] == []


def test_registry_match_and_appid_fallback():
    registry_names = ["Riot Client", "Counter-Strike 2"]  # cs2 also via reg
    def fake_registry():
        return [{"name": n, "appid": None, "source": "registry"} for n in registry_names]

    with patch("core.installed_games._steam_games", return_value=[]), \
         patch("core.installed_games._registry_games", side_effect=fake_registry):
        scan = scan_installed_games(PROFILES)
    ids = {(g["profile_id"], g["appid"]) for g in scan["matched"]}
    assert ("cs2", 730) in ids
    assert not any(pid == "valorant" for pid, _ in ids), "Riot Client must not match Valorant"
    assert all(g.get("appid") for g in scan["matched"] if g["profile_id"] == "cs2")


def test_unknown_titles_ignored():
    def fake_registry():
        return [{"name": "Some Random Utility", "appid": None, "source": "registry"}]

    with patch("core.installed_games._steam_games", return_value=[]), \
         patch("core.installed_games._registry_games", side_effect=fake_registry):
        assert scan_installed_games(PROFILES) == {"matched": [], "others": []}


def test_profileless_steam_install_reported_and_noise_skipped(tmp_path):
    """A real Steam game with no profile appears in others; redists do not."""
    root = _steam_root(tmp_path, "Wuthering Waves", 3513350)
    apps = tmp_path / "steamapps"
    (apps / "appmanifest_228980.acf").write_text(
        '"AppState"\n{\n  "appid"\t"228980"\n  "name"\t"Steamworks Common Redistributables"\n}'
    )
    scan = scan_installed_games(PROFILES, steam_root=root)
    assert scan["matched"] == []
    assert scan["others"] == [{"name": "Wuthering Waves", "source": "steam", "appid": 3513350}]


def test_short_ids_never_match_alone():
    """'cs2' is 3 chars; the id must not fuzzy-match unrelated titles."""
    def fake_registry():
        return [{"name": "CS Umbrella Ltd stuff", "appid": None, "source": "registry"}]

    with patch("core.installed_games._steam_games", return_value=[]), \
         patch("core.installed_games._registry_games", side_effect=fake_registry):
        scan = scan_installed_games(PROFILES)
    assert not any(g["profile_id"] != "cs2" and g.get("source") == "registry" for g in scan["matched"])
