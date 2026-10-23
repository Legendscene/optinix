import psutil
import time
import threading
import subprocess
from datetime import datetime
from typing import Dict, Optional, Any
from ..config import CONFIG
from ..logger import get_logger
from .metrics_store import metrics_store

_logger = get_logger("monitor_engine")

# A nvidia-smi subprocess call costs tens of milliseconds, so it would dominate
# a 3-second sample cadence if run every time. Refresh GPU readings at most this
# often; between refreshes the cached values are reused.
_GPU_TTL = 4.0


def _read_gpu() -> Optional[Dict[str, Any]]:
    """Return GPU load/temp/vram, or None if no GPU could be read.

    Mirrors core.api.system.sysinfo: try nvidia-smi first (works on any box with
    NVIDIA drivers, no third-party module), then GPUtil if it happens to be
    installed. Returning None means "unavailable" — callers surface that as an
    em dash rather than a fabricated 0.
    """
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,temperature.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=2,
        )
        if r.returncode == 0 and r.stdout.strip():
            p = [x.strip() for x in r.stdout.strip().split(",")]
            if len(p) >= 4:
                used, total = int(p[2]), int(p[3])
                return {
                    "gpu": float(p[0]),
                    "gpu_temp": float(p[1]),
                    "gpu_memory_used": round(used / total * 100, 1) if total else None,
                    "vram": round(used / total * 100, 1) if total else None,
                    "fan_speed": None,
                }
    except Exception:
        pass
    try:
        import GPUtil
        gpus = GPUtil.getGPUs()
        if gpus:
            g = gpus[0]
            return {
                "gpu": round(g.load * 100, 1),
                "gpu_temp": g.temperature,
                "gpu_memory_used": round(g.memoryUtil * 100, 1),
                "vram": round(g.memoryUtil * 100, 1),
                "fan_speed": getattr(g, "fanSpeed", None),
            }
    except Exception:
        pass
    return None


class MonitorEngine:
    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._prev_disk = (0, 0)
        self._prev_net = (0, 0)
        self._last_collect = 0.0
        self._last_disk_time = 0.0
        self._last_net_time = 0.0
        self._latest: Dict[str, Any] = {}
        # GPU reads are the slowest part of a sample (a subprocess call), so
        # they are refreshed at most once per _GPU_TTL seconds. None means "no
        # GPU detected yet", distinct from a measured idle reading.
        self._gpu_cache: Optional[Dict[str, Any]] = None
        self._gpu_time = 0.0

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="monitor-engine")
        self._thread.start()
        _logger.info("Monitor engine started")

    def stop(self):
        self._running = False
        _logger.info("Monitor engine stopped")

    def _run_loop(self):
        try:
            init = self.collect_once()
            self._last_collect = time.time()
        except Exception:
            init = {}
        while self._running:
            try:
                time.sleep(CONFIG.system_poll_seconds)
                data = self.collect_once()
                for key, value in data.items():
                    if key in metrics_store.METRICS:
                        if value is not None:
                            metrics_store.push(key, value)
                with self._lock:
                    self._latest.update(data)
                    self._last_collect = time.time()
            except Exception as e:
                _logger.error(f"Collection error: {e}")

    def collect_once(self) -> Dict[str, Any]:
        now = time.time()
        data: Dict[str, Any] = {}

        try:
            data["cpu"] = round(psutil.cpu_percent(interval=0.5), 1)
        except Exception:
            data["cpu"] = None

        try:
            mem = psutil.virtual_memory()
            data["ram"] = round(mem.percent, 1)
            data["ram_used_gb"] = round(mem.used / (1024 ** 3), 1)
            data["ram_total_gb"] = round(mem.total / (1024 ** 3), 1)
        except Exception:
            data["ram"] = None
            data["ram_used_gb"] = None
            data["ram_total_gb"] = None

        try:
            disk = psutil.disk_io_counters()
            if disk:
                delta_t = now - self._last_disk_time if self._last_disk_time > 0 else 1.0
                read_delta = disk.read_bytes - self._prev_disk[0]
                write_delta = disk.write_bytes - self._prev_disk[1]
                data["disk_read"] = round(max(0, read_delta / delta_t) / (1024 * 1024), 2) if delta_t > 0 else 0.0
                data["disk_write"] = round(max(0, write_delta / delta_t) / (1024 * 1024), 2) if delta_t > 0 else 0.0
                self._prev_disk = (disk.read_bytes, disk.write_bytes)
                self._last_disk_time = now
            else:
                data["disk_read"] = 0.0
                data["disk_write"] = 0.0
        except Exception:
            data["disk_read"] = None
            data["disk_write"] = None

        try:
            net = psutil.net_io_counters()
            if net:
                delta_t = now - self._last_net_time if self._last_net_time > 0 else 1.0
                sent_delta = net.bytes_sent - self._prev_net[0]
                recv_delta = net.bytes_recv - self._prev_net[1]
                data["network_upload"] = round(max(0, sent_delta / delta_t) / (1024 * 1024), 2) if delta_t > 0 else 0.0
                data["network_download"] = round(max(0, recv_delta / delta_t) / (1024 * 1024), 2) if delta_t > 0 else 0.0
                self._prev_net = (net.bytes_sent, net.bytes_recv)
                self._last_net_time = now
            else:
                data["network_upload"] = 0.0
                data["network_download"] = 0.0
        except Exception:
            data["network_upload"] = None
            data["network_download"] = None

        try:
            usage = psutil.disk_usage("C:\\")
            data["disk_usage_percent"] = round(usage.percent, 1)
        except Exception:
            data["disk_usage_percent"] = None

        now = time.time()
        if self._gpu_cache is None or now - self._gpu_time >= _GPU_TTL:
            self._gpu_cache = _read_gpu()
            self._gpu_time = now
        if self._gpu_cache is not None:
            data.update(self._gpu_cache)
        else:
            data["gpu"] = None
            data["gpu_temp"] = None
            data["gpu_memory_used"] = None
            data["vram"] = None
            data["fan_speed"] = None

        try:
            bat = psutil.sensors_battery()
            if bat:
                data["battery"] = round(bat.percent, 1)
                data["battery_power_plugged"] = bat.power_plugged
            else:
                data["battery"] = None
                data["battery_power_plugged"] = None
        except Exception:
            data["battery"] = None
            data["battery_power_plugged"] = None

        try:
            temps = psutil.sensors_temperatures()
            if temps:
                cpu_temp = None
                for key in ("coretemp", "cpu_thermal", "k10temp", "cpu-thermal"):
                    if key in temps and temps[key]:
                        cpu_temp = round(temps[key][0].current, 1)
                        break
                data["temperature"] = cpu_temp
            else:
                data["temperature"] = None
        except Exception:
            data["temperature"] = None

        try:
            data["processes"] = len(psutil.pids())
        except Exception:
            data["processes"] = None

        return data

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "running": self._running,
                "last_collect": self._last_collect,
                "last_collect_iso": datetime.fromtimestamp(self._last_collect).isoformat() if self._last_collect else None,
                "metrics": dict(self._latest),
                "poll_seconds": CONFIG.system_poll_seconds,
            }


monitor_engine = MonitorEngine()
