"""Wire-format contract tests: Flask routes vs the desktop's TypeScript types.

The React client (desktop/src/lib/api.ts and desktop/src/types/index.ts) reads
specific keys out of every JSON response. A route that silently changes shape
-- renaming a key, returning a bare list where an object is expected, dropping
a nested field -- crashes a page at first paint instead of failing the build.
The timeline events route did exactly this: it returned a bare list, HomePage
read `.events`, got undefined, and threw on `undefined.length`.

These tests hit the real Flask routes through the test client (no server, no
system mutation) and assert the exact shape the frontend types declare. They
run on CI via the `backend` job, so wire-format drift breaks the build instead
of the UI.
"""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app_module = importlib.import_module("app")
app = app_module.app

LOCAL = "http://127.0.0.1:5420"


def get(path):
    """GET a route through the test client, bound to the local host so the
    before_request guard accepts it. Returns parsed JSON."""
    c = app.test_client()
    r = c.get(path, base_url=LOCAL)
    assert r.status_code == 200, f"{path} returned {r.status_code}"
    return r.get_json()


def test_timeline_events_are_wrapped_in_an_object():
    """Regression pin for the shape bug that crashed HomePage.

    desktop/src/lib/api.ts declares timelineEvents as
    { events: TimelineEvent[] }. A bare list here makes HomePage read
    `.events` -> undefined and throw on `undefined.length`.
    """
    body = get("/api/timeline/events?limit=5")
    assert isinstance(body, dict), "timeline events must be an object, not a bare list"
    assert isinstance(body.get("events"), list), "object must carry an 'events' list"
    for ev in body["events"]:
        # TimelineEvent: {timestamp, type, name, details, benchmark_*}
        assert isinstance(ev.get("timestamp"), (int, float))
        assert isinstance(ev.get("type"), str)


def test_memory_free_post_action_constructs_memory_manager_with_os(monkeypatch):
    """Regression pin for the crash found in a live ACTIVATE run.

    _apply_post_action("memory_free") called MemoryManager() without the
    required os_type argument, so every Balanced preset run failed its
    Memory Free step with a TypeError. The fake here has a positional-only
    signature: reverting to the bare MemoryManager() call raises TypeError
    and fails this test.
    """
    import core.memory_manager as mm
    from core.api import overview as ov

    seen = {}

    class FakeMemoryManager:
        def __init__(self, os_type):
            seen["os_type"] = os_type

        def free_ram(self):
            return {"success": True, "results": []}

    monkeypatch.setattr(mm, "MemoryManager", FakeMemoryManager)
    result = ov._apply_post_action("memory_free")
    assert result.get("success") is True
    assert seen["os_type"] not in (None, ""), "memory_free must pass a real os_type"


def test_overview_matches_the_frontend_type():
    """Overview is the HomePage/OverviewPage payload (types: Overview)."""
    body = get("/api/overview")

    for key in ("generated_at", "is_admin", "health", "vitals",
                "detected_game", "actions", "reclaimable", "last_optimization"):
        assert key in body, f"Overview missing top-level key '{key}'"

    assert isinstance(body["is_admin"], bool)

    # OverviewHealth: {overall: number, scores: Record<string, ...>}
    health = body["health"]
    assert isinstance(health.get("overall"), (int, float))
    assert isinstance(health.get("scores"), dict)

    # OverviewVitals: every field HomePage dereferences.
    v = body["vitals"]
    for key in ("cpu_percent", "cpu_temp", "cpu_threads", "cpu_cores",
                "ram_percent", "ram_used_gb", "ram_total_gb",
                "swap_percent", "disk_percent", "disk_free_gb",
                "disk_total_gb", "process_count", "uptime_hours",
                "power_plan", "is_laptop", "battery"):
        assert key in v, f"OverviewVitals missing '{key}'"

    gpu = v["gpu"]
    for key in ("name", "usage", "temperature", "memory_used", "memory_total"):
        assert key in gpu, f"OverviewVitals.gpu missing '{key}'"

    # OverviewAction: {id, title, detail, severity, page, action, meta}
    for a in body["actions"]:
        for key in ("id", "title", "detail", "severity", "page"):
            assert key in a, f"OverviewAction missing '{key}'"
        assert a["severity"] in ("high", "medium", "low", "ok"), (
            f"unexpected severity '{a['severity']}'")


def test_overview_action_pages_point_at_real_routes():
    """Every action's `page` must be a route the desktop app actually
    renders. A typo'd or retired page id makes the action button navigate
    nowhere. Valid ids are read straight from nav.ts so this stays in sync."""
    import re
    nav_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "desktop", "src", "nav.ts")
    with open(nav_path, encoding="utf-8") as f:
        nav_src = f.read()
    valid_ids = set(re.findall(r"id:\s*'([a-z0-9-]+)'", nav_src))

    body = get("/api/overview")
    for a in body["actions"]:
        assert a["page"] in valid_ids, (
            f"action '{a['id']}' points at page '{a['page']}', which is not a "
            f"route id in desktop/src/nav.ts")


def test_presets_match_the_frontend_type():
    """PresetMode: {id, name, summary, detail, categories, post}."""
    body = get("/api/presets")
    presets = body.get("presets")
    assert isinstance(presets, list) and presets, "expected a non-empty presets list"
    for p in presets:
        for key in ("id", "name", "summary", "detail", "categories", "post"):
            assert key in p, f"PresetMode missing '{key}'"
        assert isinstance(p["detail"], list)
        assert isinstance(p["categories"], list)


def test_game_profiles_match_the_frontend_type():
    """GameProfileSummary: {id, name, description, builtin}."""
    body = get("/api/game-profiles")
    profiles = body.get("profiles")
    assert isinstance(profiles, list) and profiles, "expected built-in profiles"
    for p in profiles:
        for key in ("id", "name", "description", "builtin"):
            assert key in p, f"GameProfileSummary missing '{key}'"
        assert isinstance(p["builtin"], bool)


def test_system_info_matches_the_frontend_type():
    """SystemInfo is the shared poll behind every vitals card (systemStore)."""
    body = get("/api/system-info")

    for key in ("cpu", "memory", "disk", "network", "gpu", "system", "os"):
        assert key in body, f"SystemInfo missing top-level key '{key}'"

    cpu = body["cpu"]
    for key in ("percent", "logical", "physical"):
        assert key in cpu, f"SystemInfo.cpu missing '{key}'"

    mem = body["memory"]
    for key in ("percent", "total_gb", "used_gb", "available_gb"):
        assert key in mem, f"SystemInfo.memory missing '{key}'"

    assert isinstance(body["disk"], list), "disk must be a list of partitions"
    for d in body["disk"]:
        for key in ("device", "total", "used", "free", "percent"):
            assert key in d, f"SystemInfo.disk entry missing '{key}'"

    gpu = body["gpu"]
    for key in ("name", "usage", "memory_total", "memory_used", "temperature", "driver"):
        assert key in gpu, f"SystemInfo.gpu missing '{key}'"


def test_is_admin_matches_the_frontend_type():
    """useAdminCheck reads {is_admin: boolean} to drive the Limited mode UI."""
    body = get("/api/hardware/is-admin")
    assert "is_admin" in body, "missing 'is_admin' key"
    assert isinstance(body["is_admin"], bool)
