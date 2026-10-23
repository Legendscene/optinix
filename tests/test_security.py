"""Security boundary tests for the local-only API guard.

The backend mutates Windows settings, so the contract is: reachable only from
this machine, and not drivable by a web page via cross-origin requests to
localhost. These tests exercise app.py's before_request guard through the
Flask test client (no server is started, nothing on the system is changed).
"""
import importlib
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app_module = importlib.import_module("app")
app = app_module.app

LOCAL = "http://127.0.0.1:5420"
LOCAL_DEV = "http://localhost:5173"


def client(host="127.0.0.1:5420"):
    """Test client whose requests carry `host` in the Host header.

    base_url is the supported way to set the authority; environ_base's
    HTTP_HOST is silently ignored by modern Werkzeug.
    """
    c = app.test_client()
    c.base_host = host
    return c


def request(c, method, path, **kw):
    return getattr(c, method)(path, base_url=f"http://{c.base_host}", **kw)


def test_health_is_reachable_locally():
    r = request(client(), "get", "/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


def test_mutating_request_from_forged_origin_is_rejected():
    r = request(client(), "post", "/api/tweak-state/set", json={}, headers={"Origin": "https://evil.example"})
    assert r.status_code == 403


def test_mutating_request_from_local_origin_is_allowed():
    r = request(client(), "post", "/api/tweak-state/set", json={}, headers={"Origin": LOCAL})
    assert r.status_code == 200
    assert r.get_json()["success"] is True


def test_dev_server_origin_is_allowed():
    r = request(client(), "post", "/api/tweak-state/set", json={}, headers={"Origin": LOCAL_DEV})
    assert r.status_code == 200


def test_foreign_host_header_is_rejected():
    """DNS rebinding: attacker domain resolves to 127.0.0.1 but keeps its name."""
    r = request(client(host="attacker.example:5420"), "get", "/health")
    assert r.status_code == 403


def test_localhost_host_header_is_accepted():
    r = request(client(host="localhost:5420"), "get", "/health")
    assert r.status_code == 200


def test_foreign_referer_on_mutating_request_is_rejected():
    r = request(
        client(), "post", "/api/tweak-state/set",
        json={}, headers={"Referer": "https://attacker.example/page"},
    )
    assert r.status_code == 403


def test_get_without_origin_is_allowed():
    """Same-origin GETs and curl/test traffic often carry no Origin header."""
    r = request(client(), "get", "/health")
    assert r.status_code == 200


def test_api_404s_are_not_masked_by_the_spa_fallback():
    r = request(client(), "get", "/api/does-not-exist")
    assert r.status_code == 404


def test_local_origins_config_cover_both_ports():
    origins = app_module.LOCAL_ORIGINS
    assert LOCAL in origins
    assert LOCAL_DEV in origins
    # The wildcard must never come back.
    assert "*" not in origins


def test_socketio_cors_is_not_wildcard():
    """python-socketio does not retain cors_allowed_origins for introspection,
    so assert the exact value app.py hands to SocketIO via its source."""
    import inspect
    src = inspect.getsource(app_module)
    # The constructor call must pass the restricted set, never "*".
    assert "SocketIO(app, cors_allowed_origins=sorted(LOCAL_ORIGINS)," in src
    assert 'SocketIO(app, cors_allowed_origins="*")' not in src
    # Threading mode must be pinned for the frozen PyInstaller build to boot.
    assert 'async_mode="threading"' in src
