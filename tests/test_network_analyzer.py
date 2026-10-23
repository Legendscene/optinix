"""Network analyzer tests: the measurement math, the ping parsing, and the
no-fabrication contract.

These tests never touch the network. `subprocess.run` is replaced with canned
`ping` / `tracert` output so jitter and packet-loss math are verified against
known inputs, and the route-validation rule (hostile host -> HTTP 400) is
pinned so a regression cannot quietly reopen a command-injection surface.

The load-bearing guarantee under test: a failed probe reports an error, never a
plausible-looking number. speed_test.py previously shipped a
`random.uniform(50, 950)` Mbps fallback, which would have shown a fabricated
speed whenever the network blipped.
"""
import importlib
import os
import sys
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

analyzer = importlib.import_module("core.network_analyzer")

app = importlib.import_module("app").app
LOCAL = "http://127.0.0.1:5420"

WINDOWS_PING = """\
Pinging 8.8.8.8 with 32 bytes of data:
Reply from 8.8.8.8: bytes=32 time=20ms TTL=115
Reply from 8.8.8.8: bytes=32 time=30ms TTL=115
Reply from 8.8.8.8: bytes=32 time<1ms TTL=115
Request timed out.

Ping statistics for 8.8.8.8:
    Packets: Sent = 4, Received = 3, Lost = 1 (25% loss),
Approximate round trip times in milli-seconds:
    Minimum = 1ms, Maximum = 30ms, Average = 25ms
"""

ALL_LOST_PING = """\
Pinging 10.255.255.1 with 32 bytes of data:
Request timed out.
Request timed out.

Ping statistics for 10.255.255.1:
    Packets: Sent = 2, Received = 0, Lost = 2 (100% loss),
"""

TRACERT = """\
Tracing route to 8.8.8.8 over a maximum of 3 hops

  1    <1 ms    <1 ms    <1 ms  192.168.1.1
  2     8 ms     9 ms     8 ms  10.42.0.1
  3     *        *        *     Request timed out.

Trace complete.
"""

# The header names an IP that never appears as a hop. A parser that matched an
# IP anywhere on the line (rather than requiring a leading hop number) would
# surface 8.8.8.8 as hop 1.
TRACERT_HEADER_IP_ONLY = """\
Tracing route to 8.8.8.8 over a maximum of 2 hops

  1     5 ms     5 ms     5 ms  192.168.1.1

Trace complete.
"""


def _run(stdout: str, returncode: int = 0, stderr: str = ""):
    return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)


# ------------------------------------------------------------ jitter / stats


def test_jitter_is_standard_deviation_not_mean_delta():
    """Jitter must be the population std-dev of RTTs.

    Samples [10, 20, 30, 40] have a mean absolute successive difference of 10
    but a population std-dev of ~11.18. Using the wrong definition would report
    10 here, so this pins the choice.
    """
    with mock.patch.object(analyzer.subprocess, "run",
                           return_value=_run(WINDOWS_PING)) as m:
        res = analyzer.measure_latency("8.8.8.8", count=4)
    assert res["ok"] is True
    # Parsed RTTs in order: 20, 30, 0.5 (the "<1ms" reply).
    assert res["samples_ms"] == [20.0, 30.0, 0.5]
    expected = (20 + 30 + 0.5) / 3
    assert abs(res["avg_ms"] - expected) < 0.01
    variance = sum((v - expected) ** 2 for v in [20, 30, 0.5]) / 3
    assert abs(res["jitter_ms"] - variance ** 0.5) < 0.01
    assert m.called


def test_sub_millisecond_replies_are_counted_at_half_a_ms():
    """Windows prints `time<1ms`; a value of 1 would skew the mean upward and
    reporting 0 would understate it. 0.5 is the conventional stand-in."""
    out = ("Reply from 1.1.1.1: bytes=32 time<1ms TTL=57\n"
           "Reply from 1.1.1.1: bytes=32 time<1ms TTL=57\n"
           "Packets: Sent = 2, Received = 2, Lost = 0 (0% loss)\n")
    with mock.patch.object(analyzer.subprocess, "run", return_value=_run(out)):
        res = analyzer.measure_latency("1.1.1.1", count=2)
    assert res["samples_ms"] == [0.5, 0.5]
    assert res["avg_ms"] == 0.5
    assert res["sub_ms"] is True


def test_packet_loss_is_a_percentage_of_sent_probes():
    with mock.patch.object(analyzer.subprocess, "run", return_value=_run(WINDOWS_PING)):
        res = analyzer.measure_latency("8.8.8.8", count=4)
    # 1 of 4 probes produced no reply.
    assert res["packet_loss_pct"] == 25.0
    assert res["sent"] == 4
    assert res["received"] == 3


def test_total_loss_reports_no_latency_rather_than_zero():
    """100% loss must not surface as 0ms latency — that reads as 'instant'."""
    with mock.patch.object(analyzer.subprocess, "run", return_value=_run(ALL_LOST_PING)):
        res = analyzer.measure_latency("10.255.255.1", count=2)
    assert res["ok"] is True
    assert res["packet_loss_pct"] == 100.0
    assert res["avg_ms"] is None
    assert res["jitter_ms"] is None
    assert res["received"] == 0


def test_unreachable_host_reports_error_not_a_number():
    """A probe that yields neither samples nor a loss summary is an error. The
    bug this guards: a swallowed exception returning a fabricated latency."""
    out = "Ping request could not find host bad.host. Check the name and try again."
    with mock.patch.object(analyzer.subprocess, "run",
                           return_value=_run(out, returncode=1)):
        res = analyzer.measure_latency("bad.host", count=4)
    assert res["ok"] is False
    assert "error" in res
    assert "avg_ms" not in res and "jitter_ms" not in res
    assert "packet_loss_pct" not in res


def test_probe_timeout_is_an_error():
    import subprocess as sp
    with mock.patch.object(analyzer.subprocess, "run",
                           side_effect=sp.TimeoutExpired(cmd="ping", timeout=20)):
        res = analyzer.measure_latency("8.8.8.8", count=4)
    assert res["ok"] is False
    assert "timed out" in res["error"].lower()


def test_probe_count_is_clamped():
    """A huge count would tie up the backend for minutes."""
    with mock.patch.object(analyzer.subprocess, "run",
                           return_value=_run(WINDOWS_PING)) as m:
        analyzer.measure_latency("8.8.8.8", count=10_000)
    sent = m.call_args[0][0][2]
    assert int(sent) <= 50


# ----------------------------------------------------------------- route trace


def test_route_trace_parses_hops_and_marks_unreachable_ones():
    with mock.patch.object(analyzer.subprocess, "run", return_value=_run(TRACERT)):
        res = analyzer.trace_route("8.8.8.8")
    assert res["ok"] is True
    # The "* * *" hop is kept so hop numbering matches tracert's own.
    assert [h["ip"] for h in res["hops"]] == ["192.168.1.1", "10.42.0.1", "*"]
    # `<1ms` replies resolve to the 0.5ms stand-in.
    assert res["hops"][0]["avg_ms"] == 0.5
    assert res["hops"][0]["times_ms"] == [0.5, 0.5, 0.5]
    assert res["hops"][1]["ok"] is True
    assert 8 <= res["hops"][1]["avg_ms"] <= 9
    # The unreachable hop carries no invented timings.
    assert res["hops"][2]["ok"] is False
    assert "avg_ms" not in res["hops"][2]


def test_route_trace_excludes_the_target_header_line():
    """The "Tracing route to 8.8.8.8" header must not become a fake hop."""
    with mock.patch.object(analyzer.subprocess, "run",
                           return_value=_run(TRACERT_HEADER_IP_ONLY)):
        res = analyzer.trace_route("8.8.8.8")
    assert [h["ip"] for h in res["hops"]] == ["192.168.1.1"]
    assert all(h["ip"] != "8.8.8.8" for h in res["hops"])


def test_route_trace_marks_star_only_hop_as_unreachable():
    """A hop of "* * *" means no reply: ok False, and no fabricated time."""
    out = ("Tracing route to 8.8.8.8 over a maximum of 3 hops\n\n"
           "  1     5 ms     5 ms     5 ms  192.168.1.1\n"
           "  3     *        *        *     Request timed out.\n\n"
           "Trace complete.\n")
    with mock.patch.object(analyzer.subprocess, "run", return_value=_run(out)):
        res = analyzer.trace_route("8.8.8.8")
    unreachable = [h for h in res["hops"] if not h["ok"]]
    assert len(unreachable) == 1
    # A no-reply hop still appears (so numbering matches tracert) but carries
    # the placeholder IP and no invented timings.
    assert unreachable[0]["ip"] == "*"
    assert "avg_ms" not in unreachable[0]
    assert "times_ms" not in unreachable[0]


# ------------------------------------------------------------------- DNS


def test_resolve_dns_servers_tolerates_command_failure():
    with mock.patch.object(analyzer.subprocess, "run",
                           side_effect=FileNotFoundError("ipconfig")):
        res = analyzer.resolve_dns_servers()
    assert res["ok"] is False
    assert res["servers"] == []
    assert "error" in res


# ------------------------------------------------- contract / fabrication


def test_analyze_declares_its_methodology():
    """The UI prints the jitter/loss definitions verbatim, so they must exist
    and must disclaim routing."""
    with mock.patch.object(analyzer.subprocess, "run", return_value=_run(WINDOWS_PING)):
        res = analyzer.analyze("8.8.8.8", count=4)
    meth = res["methodology"]
    assert "standard deviation" in meth["jitter"].lower()
    assert "no reply" in meth["packet_loss"].lower()
    assert "does not" in meth["routing_note"].lower()
    assert isinstance(res["timestamp"], float)


def test_speed_test_no_longer_fabricates_bandwidth():
    """Regression pin: test_download/test_upload used to return
    random.uniform(...) Mbps with a `simulated` flag when the request failed.
    They must now report an error and carry no speed field."""
    st_module = importlib.import_module("core.speed_test")
    st = st_module.SpeedTest()
    with mock.patch.object(st_module.urllib.request, "urlopen",
                           side_effect=OSError("network down")):
        dl = st.test_download(1)
        ul = st.test_upload(1)
    for res in (dl, ul):
        assert res.get("ok") is False
        assert "error" in res
        assert "download_mbps" not in res
        assert "upload_mbps" not in res
        assert "simulated" not in res


# ------------------------------------------------------------- HTTP surface


def _post(path, json):
    c = app.test_client()
    return c.post(path, base_url=LOCAL, json=json)


def test_analyze_rejects_hostile_hosts():
    """The host is interpolated into a subprocess argv. subprocess is called
    without shell=True, so these were never shell-injectable — but the route
    must also reject them outright rather than emitting a confusing ping error."""
    for bad in ("", None, "8.8.8.8; rm -rf /", "$(whoami)", "a" * 300,
                "8.8.8.8 host", "-e 8.8.8.8", "8.8.8.8\nexit"):
        r = _post("/api/network/analyze", {"host": bad})
        assert r.status_code == 400, f"host {bad!r} was not rejected"
        assert "error" in r.get_json()


def test_trace_rejects_hostile_hosts():
    for bad in ("", "8.8.8.8; dir", "$(reboot)", "a" * 300):
        r = _post("/api/network/trace", {"host": bad})
        assert r.status_code == 400, f"host {bad!r} was not rejected"


def test_analyze_rejects_missing_host():
    r = _post("/api/network/analyze", {})
    assert r.status_code == 400


def test_targets_route_matches_the_frontend_type():
    """NetworkTarget: {id, label, host, note}."""
    c = app.test_client()
    body = c.get("/api/network/targets", base_url=LOCAL).get_json()
    assert isinstance(body.get("targets"), list) and body["targets"]
    for t in body["targets"]:
        for key in ("id", "label", "host", "note"):
            assert key in t, f"NetworkTarget missing '{key}'"


def test_analyze_route_returns_the_frontend_shape_with_mocked_probe():
    """Assert the wire shape NetworkAnalyzeResult declares, with the probe
    mocked so the test is deterministic and makes no real network call."""
    c = app.test_client()
    with mock.patch.object(analyzer.subprocess, "run", return_value=_run(WINDOWS_PING)):
        r = c.post("/api/network/analyze", base_url=LOCAL,
                   json={"host": "8.8.8.8", "count": 4})
    assert r.status_code == 200
    body = r.get_json()
    for key in ("target", "latency", "dns", "timestamp", "methodology"):
        assert key in body, f"NetworkAnalyzeResult missing '{key}'"
    lat = body["latency"]
    for key in ("ok", "host", "avg_ms", "jitter_ms", "packet_loss_pct"):
        assert key in lat, f"NetworkLatency missing '{key}'"
    assert isinstance(body["timestamp"], (int, float))
