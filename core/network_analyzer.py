"""Real network measurements for the Network Intelligence page.

Every number here comes from an actual measurement. There is deliberately no
"simulated" fallback: if a probe cannot reach its target, the result reports an
error and the UI shows an unavailable state rather than a plausible-looking
fabricated value.

Metric definitions
------------------
latency   : the mean of the per-reply round-trip times reported by the OS ping
            utility, in milliseconds. When every reply is faster than ping's
            reporting resolution (``time<1ms`` on Windows) the reply is counted
            at 0.5ms, which is the conventional stand-in and is flagged.
jitter    : the population standard deviation (not the mean of absolute
            differences) of the same round-trip samples. Standard deviation is
            the more common definition in network engineering and reacts to
            outliers, which is what gamers actually feel as "stutter".
packet_loss: the percentage of sent probes that produced no reply, derived from
            the OS-reported lost/total counts rather than from parsing each
            line, so an unparsable line can never silently read as 0% loss.
"""

import platform
import re
import socket
import statistics
import subprocess
import time
from typing import Any, Dict, List, Optional

OS = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(
    platform.system(), "unknown"
)

# Windows prints "time<1ms" for sub-millisecond replies; count them at the
# conventional 0.5ms so the mean is not skewed to exactly zero.
_SUB_MS_ASSUMED = 0.5

_LOST_RE = re.compile(r"\((\d+)% loss\)|(\d+)% packet loss", re.IGNORECASE)


def _parse_reply_times(stdout: str) -> List[float]:
    """Extract per-reply round-trip times, in milliseconds, in order.

    Handles both ``time=12ms`` and Windows' ``time<1ms`` (sub-millisecond),
    counting the latter at 0.5ms so the mean is not skewed toward zero.
    """
    times: List[float] = []
    for line in (stdout or "").splitlines():
        m = re.search(r"time[=<](\d+(?:\.\d+)?)\s*ms", line, re.IGNORECASE)
        if not m:
            continue
        value = float(m.group(1))
        is_sub_ms = "<" in line[m.start():m.end()] and value == 1
        times.append(_SUB_MS_ASSUMED if is_sub_ms else value)
    return times


def _parse_loss_percent(stdout: str) -> Optional[float]:
    """Packet loss as a percentage, from the OS summary line. None if unknown."""
    for match in _LOST_RE.finditer(stdout or ""):
        for group in match.groups():
            if group is not None:
                return float(group)
    return None


def measure_latency(
    host: str = "8.8.8.8", count: int = 10, timeout_seconds: int = 20
) -> Dict[str, Any]:
    """Ping a host and return latency, jitter and packet loss.

    Returns a dict with ``ok`` True on success. On any failure ``ok`` is False
    and ``error`` explains why; no metric is filled with a placeholder.
    """
    count = max(1, min(int(count), 50))
    param = "-n" if OS == "windows" else "-c"
    # Windows bounds the wait per reply with -w (ms); POSIX uses -W (seconds).
    if OS == "windows":
        cmd = ["ping", param, str(count), "-w", "1000", host]
    else:
        cmd = ["ping", "-c", str(count), "-W", "1", host]

    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout_seconds
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "host": host, "error": f"Ping to {host} timed out"}
    except Exception as e:  # pragma: no cover - defensive
        return {"ok": False, "host": host, "error": f"Ping failed: {e}"}

    stdout = r.stdout or ""
    times = _parse_reply_times(stdout)
    loss = _parse_loss_percent(stdout)

    if not times and loss is None:
        detail = (r.stderr or stdout).strip().splitlines()
        reason = detail[0] if detail else "no reply"
        return {
            "ok": False,
            "host": host,
            "error": f"No replies from {host}: {reason}",
        }

    result: Dict[str, Any] = {
        "ok": True,
        "host": host,
        "sent": count,
        "received": len(times),
        "samples_ms": [round(t, 2) for t in times],
    }

    if times:
        result["avg_ms"] = round(statistics.fmean(times), 2)
        result["min_ms"] = round(min(times), 2)
        result["max_ms"] = round(max(times), 2)
        # Population standard deviation of the round-trip times.
        result["jitter_ms"] = round(statistics.pstdev(times), 2) if len(times) > 1 else 0.0
        result["sub_ms"] = any(t == _SUB_MS_ASSUMED for t in times)
    else:
        # Every probe was lost: report loss, keep latency fields absent rather
        # than inventing 0ms.
        result["avg_ms"] = None
        result["jitter_ms"] = None

    if loss is not None:
        result["packet_loss_pct"] = loss
    elif count:
        result["packet_loss_pct"] = round((count - len(times)) / count * 100, 1)
    else:
        result["packet_loss_pct"] = None

    return result


def resolve_host(host: str) -> Dict[str, Any]:
    """DNS resolution diagnostics: resolve a hostname and time the lookup."""
    started = time.perf_counter()
    try:
        infos = socket.getaddrinfo(host, None)
        elapsed_ms = (time.perf_counter() - started) * 1000
        addresses = sorted({info[4][0] for info in infos})
        return {
            "ok": True,
            "host": host,
            "addresses": addresses,
            "resolve_ms": round(elapsed_ms, 1),
        }
    except Exception as e:
        elapsed_ms = (time.perf_counter() - started) * 1000
        return {
            "ok": False,
            "host": host,
            "resolve_ms": round(elapsed_ms, 1),
            "error": f"Could not resolve {host}: {e}",
        }


def resolve_dns_servers() -> Dict[str, Any]:
    """Best-effort read of the system's configured DNS servers."""
    try:
        if OS == "windows":
            r = subprocess.run(
                ["ipconfig", "/all"], capture_output=True, text=True, timeout=10
            )
            servers = sorted(set(
                m.group(1) for m in re.finditer(
                    r"DNS Servers[^\d\n]*([\d.]+)", r.stdout or ""
                )
            ))
        elif OS == "macos":
            r = subprocess.run(
                ["scutil", "--dns"], capture_output=True, text=True, timeout=10
            )
            servers = sorted(set(
                m.group(1) for m in re.finditer(
                    r"nameserver\[0\]\s*:\s*([\d.]+)", r.stdout or ""
                )
            ))
        else:
            with open("/etc/resolv.conf") as f:
                servers = sorted(set(
                    line.split()[1] for line in f
                    if line.startswith("nameserver")
                ))
        return {"ok": True, "servers": servers}
    except Exception as e:
        return {"ok": False, "servers": [], "error": str(e)}


def trace_route(host: str = "8.8.8.8", max_hops: int = 30,
                timeout_seconds: int = 40) -> Dict[str, Any]:
    """Hop-by-hop route using the OS traceroute/tracert utility.

    Returns a list of hops; a hop with ``ok`` False means no reply within the
    per-hop timeout (shown as an unreachable hop, never as a fabricated time).
    """
    if OS == "windows":
        cmd = ["tracert", "-d", "-h", str(max_hops), "-w", "1000", host]
    else:
        cmd = ["traceroute", "-n", "-m", str(max_hops), "-w", "1", host]

    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout_seconds
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "host": host, "hops": [],
                "error": f"Trace to {host} timed out"}
    except Exception as e:
        return {"ok": False, "host": host, "hops": [], "error": str(e)}

    # Match "<1 ms" (Windows sub-millisecond), "<1ms", and "12.34 ms".
    # A "<" reading is an upper bound, so it resolves to the same 0.5ms
    # stand-in measure_latency uses -- the two parsers must agree, or a hop
    # would look faster/slower than a ping sample of the same path.
    time_re = re.compile(r"<\s*(\d+(?:\.\d+)?)\s*ms|\b(\d+(?:\.\d+)?)\s*ms",
                         re.IGNORECASE)
    # A hop line is "<indent><hop-number><times...><ip>". Anchoring on the
    # leading hop number excludes the "Tracing route to <target>" header,
    # whose IP would otherwise be parsed as hop 1.
    hop_line_re = re.compile(
        r"^\s*(\d+)\s+(.*)$"
    )

    hops: List[Dict[str, Any]] = []
    for line in (r.stdout or "").splitlines():
        lm = hop_line_re.match(line)
        if not lm:
            continue
        rest = lm.group(2)
        ip = re.search(r"(\d{1,3}(?:\.\d{1,3}){3})", rest)
        # No guard here on purpose: a "* * *" hop has neither an IP nor
        # times, and must still be kept (as ip="*", ok=False) so the hop
        # numbering the user sees matches tracert's own.
        vals = []
        for g1, g2 in time_re.findall(rest):
            bound, plain = g1, g2
            if bound:
                # "<1ms" is an upper bound; 0.5ms is the conventional stand-in.
                vals.append(_SUB_MS_ASSUMED if float(bound) <= 1 else float(bound))
            else:
                vals.append(float(plain))
        hop: Dict[str, Any] = {"ip": ip.group(1) if ip else "*"}
        if vals:
            hop["ok"] = True
            hop["avg_ms"] = round(statistics.fmean(vals), 2)
            hop["times_ms"] = [round(v, 2) for v in vals]
        else:
            hop["ok"] = False
        hops.append(hop)

    return {"ok": True, "host": host, "hops": hops}


GAMING_TARGETS = [
    {"id": "cloudflare", "label": "Cloudflare", "host": "1.1.1.1",
     "note": "General internet / DNS"},
    {"id": "google", "label": "Google", "host": "8.8.8.8",
     "note": "General internet / DNS"},
    {"id": "steam", "label": "Steam", "host": "store.steampowered.com",
     "note": "Steam store and content network"},
]


def analyze(host: str, count: int = 10) -> Dict[str, Any]:
    """One full analysis: resolve + latency. Route trace is a separate call
    because it is slow and optional."""
    latency = measure_latency(host, count=count)
    dns = resolve_host(host)
    return {
        "target": host,
        "latency": latency,
        "dns": dns,
        "timestamp": time.time(),
        "methodology": {
            "jitter": "population standard deviation of round-trip times",
            "packet_loss": "percentage of sent probes with no reply",
            "routing_note": (
                "These are diagnostics only. Optinix does not run relay "
                "infrastructure and cannot change how your traffic is routed."
            ),
        },
    }
