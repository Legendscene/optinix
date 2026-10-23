"""Artwork pipeline tests — real resolution logic, network stubbed at one seam.

The rules these tests pin down:
  - a legacy CDN hit is used as-is (older titles never touch the store APIs)
  - newer titles whose legacy path 404s resolve through appdetails
  - a game with no appid resolves by name, but ONLY on a near-exact store
    match (a wrong-title cover is worse than no cover)
  - HTML/invalid bodies are never cached as artwork
  - failures are negatively cached, so a repeat request makes no network calls
  - the HTTP endpoint serves bytes as image/* and 404s honestly

No test here reaches the network: every call goes through
core.game_artwork._fetch, which these tests replace.
"""
import importlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core.game_artwork as ga  # noqa: E402
from core.game_artwork import ArtworkStore, _name_matches  # noqa: E402

LOCAL = "http://127.0.0.1:5420"

# Valid JPEG magic + enough bytes to clear the size floor.
JPEG = b"\xff\xd8\xff\xe0" + b"A" * 2048


class FakeNet:
    """Route table of URL-fragment -> response; default 404. Records calls."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def __call__(self, url, timeout=ga._HTTP_TIMEOUT_S):
        self.calls.append(url)
        for fragment, (status, headers, body) in self.routes.items():
            if fragment in url:
                return status, headers, body
        return 404, {}, b"not found"


def _store(tmp_path):
    return ArtworkStore(str(tmp_path / "artwork"))


def _meta(store, game):
    return store._read_meta(store._key(game))


def test_legacy_cdn_hit_is_used_directly(tmp_path, monkeypatch):
    """An appid whose legacy URL works resolves without any store API call."""
    store = _store(tmp_path)
    net = FakeNet({
        "cdn.cloudflare.steamstatic.com/steam/apps/730/header.jpg":
            (200, {"content-type": "image/jpeg"}, JPEG),
    })
    monkeypatch.setattr(ga, "_fetch", net)

    game = {"id": "steam:730", "name": "Counter-Strike 2", "appid": 730}
    result = store.resolve(game)
    assert result is not None, "legacy CDN image must resolve"
    body, mime = result
    assert mime == "image/jpeg" and body == JPEG
    assert not any("appdetails" in u or "storesearch" in u for u in net.calls), \
        "older titles must not hit the store APIs when the CDN works"
    assert _meta(store, game)["source"] == "steam-legacy"

    # Second resolve: served from disk, zero network calls.
    before = len(net.calls)
    assert store.resolve(game) is not None
    assert len(net.calls) == before, "positive cache must avoid refetching"


def test_new_title_falls_back_to_appdetails_header_image(tmp_path, monkeypatch):
    """Newer titles 404 on the legacy path; appdetails reveals the real
    hashed asset URL (the exact failure that left cards lettered)."""
    store = _store(tmp_path)
    hashed = "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/3513350/fb969539/header.jpg?t=1"
    net = FakeNet({
        "store.steampowered.com/api/appdetails":
            (200, {"content-type": "application/json"},
             json.dumps({"3513350": {"success": True, "data": {"header_image": hashed}}}).encode()),
        "store_item_assets/steam/apps/3513350/fb969539/header.jpg":
            (200, {"content-type": "image/jpeg"}, JPEG),
        # legacy CDN falls through to the default 404
    })
    monkeypatch.setattr(ga, "_fetch", net)

    game = {"id": "steam:3513350", "name": "Wuthering Waves", "appid": 3513350}
    result = store.resolve(game)
    assert result is not None, "appdetails path must resolve the new title"
    assert result[0] == JPEG
    assert any("appdetails" in u for u in net.calls)
    assert any("store_item_assets" in u for u in net.calls)
    assert _meta(store, game)["source"] == "steam-appdetails"


def test_no_appid_resolves_by_exact_name(tmp_path, monkeypatch):
    """A Gryphline/launcher install has no appid; a near-exact store match
    (Arknights: Endfield) is allowed to resolve its real cover."""
    store = _store(tmp_path)
    hashed = "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/4732690/0eca74/header.jpg"
    net = FakeNet({
        "storesearch":
            (200, {"content-type": "application/json"},
             json.dumps({"total": 1, "items": [{"type": "app", "name": "Arknights: Endfield", "id": 4732690}]}).encode()),
        "api/appdetails":
            (200, {"content-type": "application/json"},
             json.dumps({"4732690": {"success": True, "data": {"header_image": hashed}}}).encode()),
        "0eca74/header.jpg": (200, {"content-type": "image/jpeg"}, JPEG),
    })
    monkeypatch.setattr(ga, "_fetch", net)

    game = {"id": "gryphline:endfield", "name": "Arknights: Endfield"}  # no appid
    result = store.resolve(game)
    assert result is not None, "exact store-name match must resolve artwork"
    meta = _meta(store, game)
    assert meta.get("appid") == 4732690
    assert meta["source"] == "steam-name-lookup"


def test_name_mismatch_is_refused_and_negatively_cached(tmp_path, monkeypatch):
    """A similar-but-different store hit must never become this game's
    cover, and the miss must be remembered so the network is not re-hit."""
    store = _store(tmp_path)
    net = FakeNet({
        "storesearch":
            (200, {"content-type": "application/json"},
             json.dumps({"total": 2, "items": [
                 {"type": "app", "name": "Roblox Studio", "id": 1},
                 {"type": "dlc", "name": "Roblox Player", "id": 2},
             ]}).encode()),
    })
    monkeypatch.setattr(ga, "_fetch", net)

    game = {"id": "startmenu:roblox", "name": "Roblox Player"}
    assert store.resolve(game) is None, "a wrong-title cover must not be attached"
    assert not any("appdetails" in u for u in net.calls), \
        "an unmatched name must not proceed to image fetching"
    assert _meta(store, game)["found"] is False

    # Negative cache: no further network traffic on the next request.
    before = len(net.calls)
    assert store.resolve(game) is None
    assert len(net.calls) == before, "negative cache must short-circuit"


def test_html_body_never_cached_as_artwork(tmp_path, monkeypatch):
    """A 200 that is not actually an image (error page, proxy block) must
    not be stored or served."""
    store = _store(tmp_path)
    net = FakeNet({
        "cdn.cloudflare.steamstatic.com/steam/apps/730/header.jpg":
            (200, {"content-type": "text/html"}, b"<html>blocked by proxy</html>" * 100),
    })
    monkeypatch.setattr(ga, "_fetch", net)

    game = {"id": "steam:730", "name": "Counter-Strike 2", "appid": 730}
    assert store.resolve(game) is None, "HTML must not pass as an image"
    assert _meta(store, game)["found"] is False
    assert not os.path.exists(store._img_path(store._key(game))), \
        "no image file may be written for an invalid body"


def test_network_failure_is_negative_cached(tmp_path, monkeypatch):
    """DNS/timeout failures resolve to None and stop retrying for a day."""
    store = _store(tmp_path)

    def boom(url, timeout=ga._HTTP_TIMEOUT_S):
        raise OSError("network down")

    monkeypatch.setattr(ga, "_fetch", boom)
    game = {"id": "steam:730", "name": "Counter-Strike 2", "appid": 730}
    assert store.resolve(game) is None
    assert _meta(store, game)["found"] is False


def test_name_matching_requires_a_clear_match():
    assert _name_matches("Arknights: Endfield", "Arknights: Endfield")
    assert _name_matches("Wuthering Waves", "Wuthering Waves ")
    assert not _name_matches("Roblox Player", "Roblox Studio")
    assert not _name_matches("MSI App Player", "App Player 2")
    assert not _name_matches("", "anything")


# ---------------------------------------------------------------------------
# Local launcher icons (icon_path): the guaranteed floor, offline.
# ---------------------------------------------------------------------------
# Windows .ico magic + padding to clear the (small, local) size floor.
ICO = b"\x00\x00\x01\x00" + b"\x00" * 508


def test_local_icon_fills_in_when_the_network_is_down(tmp_path, monkeypatch):
    """A launcher-shipped icon (icon_path) is the guaranteed floor: with the
    store APIs unreachable the card still gets a real image — this is what
    keeps every game's card populated on an offline PC."""
    store = _store(tmp_path)
    icon = tmp_path / "game.ico"
    icon.write_bytes(ICO)

    def boom(url, timeout=ga._HTTP_TIMEOUT_S):
        raise OSError("network down")

    monkeypatch.setattr(ga, "_fetch", boom)
    game = {"id": "reg:marvel-rivals", "name": "Marvel Rivals",
            "appid": 2767030, "icon_path": str(icon)}
    result = store.resolve(game)
    assert result is not None, "local icon must answer when the store is unreachable"
    body, mime = result
    assert body == ICO and mime == "image/x-icon"
    assert _meta(store, game)["source"] == "local-icon"


def test_steam_cover_wins_over_the_local_icon_when_online(tmp_path, monkeypatch):
    """With an appid AND a local icon, an online store cover still wins —
    the icon is the floor, not the ceiling (a wide cover beats an icon)."""
    store = _store(tmp_path)
    icon = tmp_path / "game.ico"
    icon.write_bytes(ICO)
    net = FakeNet({
        "cdn.cloudflare.steamstatic.com/steam/apps/730/header.jpg":
            (200, {"content-type": "image/jpeg"}, JPEG),
    })
    monkeypatch.setattr(ga, "_fetch", net)

    game = {"id": "steam:730", "name": "Counter-Strike 2", "appid": 730,
            "icon_path": str(icon)}
    body, mime = store.resolve(game)
    assert body == JPEG, "the CDN cover must be preferred over the local icon"
    assert _meta(store, game)["source"] == "steam-legacy"


def test_no_appid_game_resolves_from_local_icon_without_any_network(tmp_path, monkeypatch):
    """A standalone registry game (no appid) with a local icon: zero network
    traffic, instant artwork."""
    store = _store(tmp_path)
    icon = tmp_path / "standalone.ico"
    icon.write_bytes(ICO)
    net = FakeNet({})  # every URL would 404 — nothing may be asked
    monkeypatch.setattr(ga, "_fetch", net)

    game = {"id": "reg:cool-game", "name": "Cool Game", "icon_path": str(icon)}
    result = store.resolve(game)
    assert result is not None and result[0] == ICO
    assert net.calls == [], "the local icon must resolve before any store lookup"
    assert _meta(store, game)["source"] == "local-icon"


def test_missing_icon_file_falls_through_to_the_network_chain(tmp_path, monkeypatch):
    """icon_path pointing at a deleted file: silently ignored, the normal
    appid chain still decides (and negative-caches on failure)."""
    store = _store(tmp_path)
    net = FakeNet({})  # all 404
    monkeypatch.setattr(ga, "_fetch", net)

    game = {"id": "steam:730", "name": "Counter-Strike 2", "appid": 730,
            "icon_path": str(tmp_path / "gone.ico")}
    assert store.resolve(game) is None
    assert _meta(store, game)["found"] is False
    assert net.calls, "a dead icon_path must not short-circuit the chain"


def test_exe_icon_is_the_last_resort_photo(tmp_path, monkeypatch):
    """No appid, no local icon, no store match (Roblox, an emulator shell):
    the executable's own embedded icon still gives the card a real image."""
    PNG_ICON = b"\x89PNG\r\n\x1a\n" + b"\x00" * 300
    store = _store(tmp_path)
    net = FakeNet({})  # storesearch finds nothing for these names
    monkeypatch.setattr(ga, "_fetch", net)
    monkeypatch.setattr(ga, "_exe_icon_png", lambda exe: PNG_ICON)

    game = {"id": "startmenu:roblox", "name": "Roblox Player",
            "exe_path": r"C:\\Roblox\\RobloxPlayerBeta.exe"}
    result = store.resolve(game)
    assert result is not None, "the embedded exe icon must fill the card"
    body, mime = result
    assert body == PNG_ICON and mime == "image/png"
    assert _meta(store, game)["source"] == "exe-icon"


def test_exe_icon_never_overrides_a_resolved_cover(tmp_path, monkeypatch):
    """A game that resolves via the store must not pay for icon extraction."""
    store = _store(tmp_path)
    net = FakeNet({
        "cdn.cloudflare.steamstatic.com/steam/apps/730/header.jpg":
            (200, {"content-type": "image/jpeg"}, JPEG),
    })
    monkeypatch.setattr(ga, "_fetch", net)
    extracted = []
    monkeypatch.setattr(ga, "_exe_icon_png", lambda exe: extracted.append(exe) or b"")

    game = {"id": "steam:730", "name": "Counter-Strike 2", "appid": 730,
            "exe_path": r"C:\\Steam\\hl2.exe"}
    body, _mime = store.resolve(game)
    assert body == JPEG
    assert extracted == [], "a resolved cover must skip the slow extraction path"


def test_exe_icon_failure_is_negatively_cached(tmp_path, monkeypatch):
    """Nothing works (no network, file carries no icon): one honest 404
    answer, remembered — no repeated PowerShell extractions per request."""
    store = _store(tmp_path)
    net = FakeNet({})
    monkeypatch.setattr(ga, "_fetch", net)
    monkeypatch.setattr(ga, "_exe_icon_png", lambda exe: b"")

    game = {"id": "startmenu:x", "name": "Some Tool", "exe_path": r"C:\\x\\x.exe"}
    assert store.resolve(game) is None
    assert _meta(store, game)["found"] is False
    before = len(net.calls)
    assert store.resolve(game) is None
    assert len(net.calls) == before, "negative cache must short-circuit the whole chain"


# ---------------------------------------------------------------------------
# Endpoint contract (real Flask routes, no server).
# ---------------------------------------------------------------------------
app = importlib.import_module("app").app


def _seeded_store(tmp_path, game):
    """A store whose cache already holds this game's cover (or a negative)."""
    store = ArtworkStore(str(tmp_path / "artwork"))
    return store


def test_artwork_endpoint_serves_image_for_cached_game(tmp_path, monkeypatch):
    import core.api.game_library_api as gla
    import core.game_artwork as gamod

    game = {"id": "steam:730", "name": "Counter-Strike 2", "appid": 730}
    store = ArtworkStore(str(tmp_path / "artwork"))
    os.makedirs(store.cache_dir, exist_ok=True)
    with open(store._img_path(store._key(game)), "wb") as f:
        f.write(JPEG)
    store._write_meta(store._key(game), {
        "found": True, "file": os.path.basename(store._img_path(store._key(game))),
        "mime": "image/jpeg", "ts": time.time(), "source": "steam-legacy", "appid": 730,
    })

    monkeypatch.setattr(gla, "_find_game", lambda gid: game if gid == game["id"] else None)
    monkeypatch.setattr(gamod, "STORE", store)

    c = app.test_client()
    r = c.get(f"/api/game-library/artwork?id={game['id']}", base_url=LOCAL)
    assert r.status_code == 200, r.status_code
    assert r.headers["Content-Type"].startswith("image/"), r.headers["Content-Type"]
    assert r.data[:3] == b"\xff\xd8\xff", "must serve the real image bytes"
    assert "max-age" in r.headers.get("Cache-Control", "").lower() or r.headers.get("Expires"), \
        "cached artwork must carry browser caching headers"


def test_artwork_endpoint_404s_for_unknown_and_unresolved(tmp_path, monkeypatch):
    import core.api.game_library_api as gla
    import core.game_artwork as gamod

    game = {"id": "startmenu:roblox", "name": "Roblox Player"}
    store = ArtworkStore(str(tmp_path / "artwork"))
    store._store_negative(store._key(game), "no verified artwork")  # fresh negative

    monkeypatch.setattr(gla, "_find_game", lambda gid: game if gid == game["id"] else None)
    monkeypatch.setattr(gamod, "STORE", store)

    c = app.test_client()
    # Unresolved game: honest 404 -> frontend renders the designed tile.
    r = c.get(f"/api/game-library/artwork?id={game['id']}", base_url=LOCAL)
    assert r.status_code == 404
    assert r.get_json().get("artwork") is None

    # Unknown id: rejected before any resolution work.
    r2 = c.get("/api/game-library/artwork?id=not-a-game", base_url=LOCAL)
    assert r2.status_code == 404
