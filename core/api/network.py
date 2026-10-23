import os
import platform
import re

from flask import Blueprint, jsonify, request

OS = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(platform.system(), "unknown")
network_bp = Blueprint("network", __name__)

# Hostnames and IPv4 literals only. subprocess is always invoked with a list
# (never shell=True), so this is defense in depth against a crafted target
# string plus a clear 400 instead of an opaque ping failure.
_HOST_RE = re.compile(r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$|^(?:\d{1,3}\.){3}\d{1,3}$", re.IGNORECASE)


def _validated_host(raw):
    """Return a safe host string, or None when the input is not a plausible
    hostname/IPv4 address (empty, too long, or containing shell metachars)."""
    host = (raw or "").strip()
    if not host or len(host) > 253:
        return None
    return host if _HOST_RE.match(host) else None


@network_bp.route("/api/network/adapters")
def net_adapters():
    try:
        from core.network_tuner import NetworkTuner
        return jsonify({"adapters": NetworkTuner(OS).get_adapters()})
    except Exception as e:
        return jsonify({"adapters": [], "error": str(e)})


@network_bp.route("/api/network/tune-adapter", methods=["POST"])
def net_tune_adapter():
    try:
        d = request.get_json() or {}
        from core.network_tuner import NetworkTuner
        return jsonify({"results": NetworkTuner(OS).tune_adapter(d.get("adapter"), d.get("preset", "gaming"))})
    except Exception as e:
        return jsonify({"error": str(e)})


@network_bp.route("/api/network/bufferbloat", methods=["POST"])
def net_bufferbloat():
    try:
        d = request.get_json() or {}
        from core.network_tuner import NetworkTuner
        return jsonify({"results": NetworkTuner(OS).set_bufferbloat_preset(d.get("preset", "low_latency"))})
    except Exception as e:
        return jsonify({"error": str(e)})


@network_bp.route("/api/network/qos", methods=["POST"])
def net_qos():
    try:
        d = request.get_json() or {}
        from core.network_tuner import NetworkTuner
        return jsonify({"results": NetworkTuner(OS).set_qos_priority(d.get("enable", True))})
    except Exception as e:
        return jsonify({"error": str(e)})


@network_bp.route("/api/network/advanced-tweaks", methods=["POST"])
def net_advanced():
    try:
        from core.network_tuner import NetworkTuner
        return jsonify({"results": NetworkTuner(OS).advanced_network_tweaks()})
    except Exception as e:
        return jsonify({"error": str(e)})


@network_bp.route("/api/network/optimize-mtu", methods=["POST"])
def net_optimize_mtu():
    try:
        from core.network_tuner import NetworkTuner
        return jsonify({"results": NetworkTuner(OS).optimize_mtu()})
    except Exception as e:
        return jsonify({"error": str(e)})


@network_bp.route("/api/network-priority/qos/enable", methods=["POST"])
def np_qos_enable():
    try:
        from core.network_priority import NetworkPriority
        return jsonify(NetworkPriority(OS).enable_qos())
    except Exception as e:
        return jsonify({"error": str(e)})


@network_bp.route("/api/network-priority/qos/disable", methods=["POST"])
def np_qos_disable():
    try:
        from core.network_priority import NetworkPriority
        return jsonify(NetworkPriority(OS).disable_qos())
    except Exception as e:
        return jsonify({"error": str(e)})


@network_bp.route("/api/network-priority/qos/game-traffic", methods=["POST"])
def np_qos_game():
    try:
        d = request.get_json() or {}
        from core.network_priority import NetworkPriority
        return jsonify(NetworkPriority(OS).prioritize_game_traffic(d.get("game_exe", "")))
    except Exception as e:
        return jsonify({"error": str(e)})


@network_bp.route("/api/network-priority/bufferbloat/presets")
def np_bufferbloat_presets():
    try:
        from core.network_priority import BufferBloatControl
        return jsonify({"presets": BufferBloatControl(OS).get_presets()})
    except Exception as e:
        return jsonify({"error": str(e)})


@network_bp.route("/api/network-priority/bufferbloat/apply", methods=["POST"])
def np_bufferbloat_apply():
    try:
        d = request.get_json() or {}
        from core.network_priority import BufferBloatControl
        return jsonify(BufferBloatControl(OS).apply_preset(d.get("preset", "balanced")))
    except Exception as e:
        return jsonify({"error": str(e)})


@network_bp.route("/api/network-priority/adapter/optimize", methods=["POST"])
def np_adapter_optimize():
    try:
        d = request.get_json() or {}
        from core.network_priority import AdapterTuner
        return jsonify(AdapterTuner(OS).optimize_adapter(d.get("adapter", ""), d.get("preset", "gaming")))
    except Exception as e:
        return jsonify({"error": str(e)})


@network_bp.route("/api/network-priority/adapter/reset", methods=["POST"])
def np_adapter_reset():
    try:
        d = request.get_json() or {}
        from core.network_priority import AdapterTuner
        return jsonify(AdapterTuner(OS).reset_adapter(d.get("adapter", "")))
    except Exception as e:
        return jsonify({"error": str(e)})


# ---------------------------------------------------------------------------
# Network Intelligence: real measurements only.
#
# These routes never fabricate a value. A failed probe returns ok=False with an
# explanation, which the UI renders as an unavailable state. There is no
# simulated fallback and no claim of multipath/route optimization: Optinix has
# no relay infrastructure, so these are diagnostics, not traffic control.
# ---------------------------------------------------------------------------

@network_bp.route("/api/network/targets")
def net_targets():
    """Preset measurement targets (general internet + game-service CDNs)."""
    from core.network_analyzer import GAMING_TARGETS
    return jsonify({"targets": GAMING_TARGETS})


@network_bp.route("/api/network/dns-servers")
def net_dns_servers():
    """The system's currently configured DNS servers (read-only)."""
    from core.network_analyzer import resolve_dns_servers
    return jsonify(resolve_dns_servers())


@network_bp.route("/api/network/analyze", methods=["POST"])
def net_analyze():
    """Resolve a target and measure latency, jitter and packet loss.

    Body: {"host": str, "count"?: int}. The count is clamped 1..50 by the
    analyzer. Returns {target, latency, dns, timestamp, methodology}.
    """
    d = request.get_json() or {}
    host = _validated_host(d.get("host"))
    if not host:
        return jsonify({"error": "Invalid or missing host"}), 400
    try:
        count = int(d.get("count", 10))
    except (TypeError, ValueError):
        count = 10
    from core.network_analyzer import analyze
    return jsonify(analyze(host, count=count))


@network_bp.route("/api/network/trace", methods=["POST"])
def net_trace():
    """Hop-by-hop route trace. Slow and optional, so it is a separate call.

    Body: {"host": str, "max_hops"?: int}.
    """
    d = request.get_json() or {}
    host = _validated_host(d.get("host"))
    if not host:
        return jsonify({"error": "Invalid or missing host"}), 400
    try:
        max_hops = max(1, min(int(d.get("max_hops", 30)), 64))
    except (TypeError, ValueError):
        max_hops = 30
    from core.network_analyzer import trace_route
    return jsonify(trace_route(host, max_hops=max_hops))
