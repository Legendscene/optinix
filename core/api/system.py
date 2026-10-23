import os
import time
import platform
import subprocess
import psutil
from flask import Blueprint, jsonify

system_bp = Blueprint("system", __name__)
_boot = time.time()
_prev_net = None
_prev_net_time = None
_gpu_cache = None
_gpu_time = 0
_media_cache = None
_media_time = 0
_tweak_state = None
OS = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(platform.system(), "unknown")

MEDIA_TTL = 300.0


def _disk_media_types():
    """SSD/HDD probe. Cached for 5 minutes - spawning wmic per poll is expensive."""
    global _media_cache, _media_time
    now = time.time()
    if _media_cache is not None and (now - _media_time) < MEDIA_TTL:
        return _media_cache
    result = {}
    if os.name == "nt":
        try:
            r = subprocess.run(
                ["wmic", "diskdrive", "get", "Index,MediaType,Model"],
                capture_output=True, text=True, timeout=8,
            )
            for line in r.stdout.strip().split("\n")[1:]:
                if not line.strip():
                    continue
                raw = line.split()
                if len(raw) < 3:
                    continue
                idx = raw[0]
                is_ssd = True if ("SSD" in line or "Solid" in line) else None
                if is_ssd is None and ("HDD" in line or "Fixed" in line):
                    is_ssd = False
                model = " ".join(raw[2:]).strip()
                result[idx] = {"is_ssd": is_ssd, "model": model}
        except Exception:
            result = {}
    _media_cache = result
    _media_time = now
    return result


@system_bp.route("/api/system-info")
def sysinfo():
    global _prev_net, _prev_net_time, _gpu_cache, _gpu_time
    out = {}
    try:
        out["cpu"] = {"percent": psutil.cpu_percent(interval=0), "logical": psutil.cpu_count(), "physical": psutil.cpu_count(False) or 1, "temperature": None}
        try:
            for n, e in psutil.sensors_temperatures().items():
                if e:
                    out["cpu"]["temperature"] = e[0].current
                    break
        except:
            pass
    except:
        out["cpu"] = {"percent": 0, "logical": 1, "physical": 1, "temperature": None}
    try:
        m = psutil.virtual_memory()
        out["memory"] = {"percent": m.percent, "total_gb": round(m.total/1073741824, 1), "used_gb": round(m.used/1073741824, 1), "available_gb": round(m.available/1073741824, 1)}
    except:
        out["memory"] = {"percent": 0, "total_gb": 0, "used_gb": 0, "available_gb": 0}
    try:
        media = _disk_media_types()
        disks = []
        for i, p in enumerate(psutil.disk_partitions(all=False)):
            try:
                u = psutil.disk_usage(p.mountpoint)
                entry = media.get(str(i), {})
                is_ext = p.device not in (os.environ.get("SystemDrive", "C:") + "\\", "/", "C:\\", "D:\\")
                disks.append({
                    "device": p.device, "mountpoint": p.mountpoint, "fstype": p.fstype,
                    "total": u.total, "used": u.used, "free": u.free, "percent": u.percent,
                    "is_ssd": entry.get("is_ssd"),
                    "model": entry.get("model", ""),
                    "is_external": is_ext,
                })
            except Exception:
                pass
        out["disk"] = disks
    except Exception:
        out["disk"] = []
    try:
        s = psutil.net_io_counters()
        now = time.time()
        sp_up = sp_dn = 0
        if _prev_net and _prev_net_time:
            dt = now - _prev_net_time
            if dt > 0:
                sp_up = (s.bytes_sent - _prev_net.bytes_sent) / dt
                sp_dn = (s.bytes_recv - _prev_net.bytes_recv) / dt
        _prev_net = s
        _prev_net_time = now
        out["network"] = {"bytes_sent": s.bytes_sent, "bytes_recv": s.bytes_recv, "speed_up": int(sp_up), "speed_down": int(sp_dn)}
    except:
        out["network"] = {"bytes_sent": 0, "bytes_recv": 0, "speed_up": 0, "speed_down": 0}
    now = time.time()
    if not _gpu_cache or (now - _gpu_time) > 5:
        gpu = {"name": "N/A", "usage": 0, "memory_total": 0, "memory_used": 0, "temperature": 0, "driver": "N/A"}
        try:
            r = subprocess.run(["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu,driver_version", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=2)
            if r.returncode == 0 and r.stdout.strip():
                p = r.stdout.strip().split(", ")
                if len(p) >= 6:
                    gpu = {"name": p[0].strip(), "usage": int(p[1]), "memory_used": int(p[2]), "memory_total": int(p[3]), "temperature": int(p[4]), "driver": p[5].strip()}
        except:
            pass
        if gpu["name"] == "N/A" and os.name == 'nt':
            try:
                r = subprocess.run(["wmic", "path", "win32_VideoController", "get", "Name,AdapterRAM,DriverVersion,CurrentHorizontalResolution,CurrentVerticalResolution", "/format:csv"], capture_output=True, text=True, timeout=5)
                for line in r.stdout.strip().split("\n")[1:]:
                    if line.strip() and "Node" not in line:
                        parts = [x.strip() for x in line.split(",") if x.strip()]
                        for p in parts:
                            if "GB" in p or "MB" in p or not any(c.isdigit() for c in p):
                                continue
                        name = parts[1] if len(parts) > 1 else gpu["name"]
                        ram_str = parts[2] if len(parts) > 2 else "0"
                        driver = parts[3] if len(parts) > 3 else gpu["driver"]
                        try:
                            mem_total = int(ram_str) // (1024*1024) if ram_str.isdigit() else 0
                        except:
                            mem_total = 0
                        if name.lower() != "name":
                            gpu = {"name": name, "usage": gpu["usage"], "memory_total": mem_total, "memory_used": gpu["memory_used"], "temperature": gpu["temperature"], "driver": driver}
            except:
                pass
        _gpu_cache = gpu
        _gpu_time = now
    out["gpu"] = _gpu_cache
    try:
        up = time.time() - _boot
        out["system"] = {"os": platform.system() + " " + platform.release(), "processor": platform.processor() or "Unknown", "uptime": f"{int(up//86400)}d {int((up%86400)//3600)}h {int((up%3600)//60)}m"}
    except:
        out["system"] = {"os": "Unknown", "uptime": "N/A"}
    out["os"] = {"os_name": platform.system(), "release": platform.release()}
    return jsonify(out)


@system_bp.route("/api/smart-detect")
def smart_detect():
    try:
        from core.smart_detect import SmartDetector
        sd = SmartDetector(OS)
        return jsonify({"hardware": sd.get_hardware_info(), "recommendations": sd.get_recommendations()})
    except Exception as e:
        return jsonify({"error": str(e)})


@system_bp.route("/api/tweak-state")
def tweak_state_get():
    global _tweak_state
    if not _tweak_state:
        from core.tweak_state import TweakState
        _tweak_state = TweakState()
    return jsonify(_tweak_state.get_all())


@system_bp.route("/api/tweak-state/set", methods=["POST"])
def tweak_state_set():
    global _tweak_state
    if not _tweak_state:
        from core.tweak_state import TweakState
        _tweak_state = TweakState()
    from flask import request
    d = request.get_json() or {}
    for k, v in d.items():
        _tweak_state.set(k, v)
    return jsonify({"success": True})


@system_bp.route("/api/hardware/detect")
def hw_detect():
    try:
        from core.hardware_detection import HardwareDetector
        d = HardwareDetector()
        return jsonify(d.detect_all())
    except Exception as e:
        return jsonify({"error": str(e)})


@system_bp.route("/api/hardware/is-admin")
def hw_is_admin():
    try:
        import ctypes
        is_admin = os.name == 'nt' and ctypes.windll.shell32.IsUserAnAdmin() != 0
        return jsonify({"is_admin": is_admin})
    except:
        return jsonify({"is_admin": False})


@system_bp.route("/api/optimizations/list")
def opt_list():
    try:
        from core.compatibility_engine import CompatibilityEngine
        ce = CompatibilityEngine(OS)
        return jsonify(ce.get_optimizations_by_category())
    except Exception as e:
        return jsonify({"error": str(e)})


@system_bp.route("/api/optimizations/check/<oid>")
def opt_check(oid):
    try:
        from core.compatibility_engine import CompatibilityEngine
        ce = CompatibilityEngine(OS)
        return jsonify(ce.check(oid))
    except Exception as e:
        return jsonify({"error": str(e)})


@system_bp.route("/api/optimizations/check-multiple", methods=["POST"])
def opt_check_multi():
    try:
        from flask import request
        from core.compatibility_engine import CompatibilityEngine
        d = request.get_json() or {}
        ce = CompatibilityEngine(OS)
        return jsonify(ce.check_multiple(d.get("ids", [])))
    except Exception as e:
        return jsonify({"error": str(e)})


@system_bp.route("/api/reset-to-defaults", methods=["POST"])
def reset_to_defaults():
    try:
        from core.rollback_engine import RollbackEngine
        import ctypes
        is_admin = os.name == 'nt' and ctypes.windll.shell32.IsUserAnAdmin() != 0
        if not is_admin:
            return jsonify({"success": False, "message": "Administrator privileges required"}), 403
        re = RollbackEngine(OS)
        results = []
        registry_keys = [
            (r"HKLM\SYSTEM\CurrentControlSet\Control\PriorityControl", "Win32PrioritySeparation"),
            (r"HKLM\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters", "TcpAckFrequency"),
            (r"HKLM\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters", "TCPNoDelay"),
            (r"HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management", "DisablePagingExecutive"),
            (r"HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management", "LargeSystemCache"),
            (r"HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management\PrefetchParameters", "EnablePrefetcher"),
            (r"HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management\PrefetchParameters", "EnableSuperfetch"),
            (r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile", "SystemResponsiveness"),
            (r"HKLM\SYSTEM\CurrentControlSet\Control\PriorityControl", "IRQ8Priority"),
            (r"HKLM\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters", "MaxHashTableSize"),
            (r"HKLM\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters", "MaxFreeTcbs"),
            (r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System", "EnableLUA"),
            (r"HKLM\SYSTEM\CurrentControlSet\Services\stornvme\Parameters\Device", "QueueDepth"),
            (r"HKLM\SYSTEM\CurrentControlSet\Services\stornvme\Parameters\Device", "ThreadPriority"),
        ]
        for key, val in registry_keys:
            try:
                r = subprocess.run(["reg", "delete", key, "/v", val, "/f"], capture_output=True, text=True, timeout=5)
                results.append({"key": key, "value": val, "success": True, "action": "deleted" if not r.returncode else "not_found"})
            except Exception as e:
                results.append({"key": key, "value": val, "success": False, "error": str(e)})
        bcd_keys = ["useplatformclock", "useplatformtick", "disabledynamictick", "tscsyncpolicy"]
        for bk in bcd_keys:
            try:
                subprocess.run(["bcdedit", "/deletevalue", bk], capture_output=True, text=True, timeout=5)
                results.append({"bcd": bk, "success": True, "action": "deleted"})
            except:
                results.append({"bcd": bk, "success": True, "action": "not_found"})
        try:
            subprocess.run(["powercfg", "/setactive", "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"], capture_output=True, text=True, timeout=5)
            results.append({"action": "power_plan", "plan": "Balanced", "success": True})
        except:
            pass
        snap = re.save_snapshot()
        return jsonify({"success": True, "message": "Reset to Windows defaults completed", "results": results, "total": len(results), "snapshot": os.path.basename(snap)})
    except Exception as e:
        return jsonify({"success": False, "message": f"Reset failed: {e}"})


@system_bp.route("/api/ram-boost", methods=["POST"])
def ram_boost():
    try:
        import ctypes
        try:
            ctypes.windll.ntdll.NtSetSystemInformation(0x57, bytes([0x01, 0x00, 0x00, 0x00]), 4)
        except:
            pass
        subprocess.run(["powershell", "-NoProfile", "-Command", "[System.GC]::Collect(); [System.GC]::WaitForPendingFinalizers()"], capture_output=True, timeout=15)
        return jsonify({"success": True, "message": "RAM standby memory cleared"})
    except Exception as e:
        return jsonify({"success": False, "message": f"RAM boost failed: {e}"})


@system_bp.route("/api/ping", methods=["POST"])
def ping_host():
    from flask import request
    d = request.get_json() or {}
    host = d.get("host", "8.8.8.8")
    try:
        param = "-n" if platform.system().lower() == "windows" else "-c"
        result = subprocess.run(["ping", param, "4", host], capture_output=True, text=True, timeout=10)
        return jsonify({"output": result.stdout, "error": result.stderr})
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Ping timed out"})
    except Exception as e:
        return jsonify({"error": str(e)})


@system_bp.route("/health")
def health():
    return jsonify({"status": "ok", "os": OS})
