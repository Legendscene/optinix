import psutil
import time
import subprocess
import platform
import json


class SystemScanner:
    def __init__(self, os_type):
        self.os_type = os_type
        self._prev_net = None
        self._prev_net_time = None
        self._cpu_count = psutil.cpu_count(logical=True) or 1
        try:
            psutil.cpu_percent(interval=0)
            psutil.cpu_percent(interval=0, percpu=True)
        except Exception:
            pass

    def full_scan(self):
        result = {}
        try:
            result["cpu"] = self.scan_cpu()
        except Exception:
            result["cpu"] = {"percent": 0, "logical": 1, "physical": 1, "freq": None, "per_cpu": [], "temperature": None}
        try:
            result["memory"] = self.scan_memory()
        except Exception:
            result["memory"] = {"total": 0, "used": 0, "percent": 0, "total_gb": 0, "used_gb": 0}
        try:
            result["disk"] = self.scan_disk()
        except Exception:
            result["disk"] = []
        try:
            result["network"] = self.scan_network()
        except Exception:
            result["network"] = {"bytes_sent": 0, "bytes_recv": 0, "speed_up": 0, "speed_down": 0}
        try:
            result["gpu"] = self.scan_gpu()
        except Exception:
            result["gpu"] = {"name": "N/A", "usage": 0, "memory_total": 0, "memory_used": 0, "temperature": 0}
        try:
            result["processes"] = self.scan_processes()
        except Exception:
            result["processes"] = []
        try:
            result["system"] = self.scan_system()
        except Exception:
            result["system"] = {"os": platform.system(), "uptime": "N/A"}
        try:
            result["os"] = {"os_name": platform.system(), "release": platform.release()}
        except Exception:
            result["os"] = {"os_name": "Unknown", "release": ""}
        return result

    def scan_cpu(self):
        try:
            percent = psutil.cpu_percent(interval=0.1)
            per_cpu = psutil.cpu_percent(interval=0, percpu=True)
        except Exception:
            percent = 0
            per_cpu = []
        try:
            freq = psutil.cpu_freq()
            freq_dict = freq._asdict() if freq else None
        except Exception:
            freq_dict = None
        temp = None
        try:
            temps = psutil.sensors_temperatures()
            for name, entries in temps.items():
                if entries:
                    temp = entries[0].current
                    break
        except Exception:
            pass
        return {
            "percent": percent,
            "logical": self._cpu_count,
            "physical": psutil.cpu_count(logical=False) or 1,
            "freq": freq_dict,
            "per_cpu": per_cpu,
            "temperature": temp
        }

    def scan_memory(self):
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return {
            "total": mem.total, "available": mem.available,
            "used": mem.used, "percent": mem.percent,
            "total_gb": round(mem.total / (1024**3), 1),
            "used_gb": round(mem.used / (1024**3), 1),
            "available_gb": round(mem.available / (1024**3), 1),
            "swap_total": swap.total, "swap_used": swap.used, "swap_percent": swap.percent
        }

    def scan_disk(self):
        disks = []
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
                disks.append({
                    "device": part.device, "mountpoint": part.mountpoint,
                    "fstype": part.fstype, "total": usage.total,
                    "used": usage.used, "free": usage.free, "percent": usage.percent
                })
            except Exception:
                continue
        return disks

    def scan_network(self):
        try:
            stats = psutil.net_io_counters()
        except Exception:
            return {"bytes_sent": 0, "bytes_recv": 0, "speed_up": 0, "speed_down": 0, "interfaces": []}
        now = time.time()
        speed_up = speed_down = 0
        if self._prev_net and self._prev_net_time:
            dt = now - self._prev_net_time
            if dt > 0:
                speed_up = (stats.bytes_sent - self._prev_net.bytes_sent) / dt
                speed_down = (stats.bytes_recv - self._prev_net.bytes_recv) / dt
        self._prev_net = stats
        self._prev_net_time = now
        return {
            "bytes_sent": stats.bytes_sent, "bytes_recv": stats.bytes_recv,
            "speed_up": round(speed_up), "speed_down": round(speed_down),
            "interfaces": []
        }

    def scan_gpu(self):
        gpu = {"name": "N/A", "usage": 0, "memory_total": 0, "memory_used": 0, "temperature": 0, "driver": "N/A"}
        if self.os_type == "windows":
            try:
                r = subprocess.run(
                    ["powershell", "-Command",
                     "Get-CimInstance Win32_VideoController -ErrorAction SilentlyContinue | Select-Object -First 1 Name, AdapterRAM, DriverVersion | ConvertTo-Json"],
                    capture_output=True, text=True, timeout=5
                )
                if r.stdout.strip():
                    data = json.loads(r.stdout)
                    if isinstance(data, list):
                        data = data[0] if data else {}
                    gpu["name"] = data.get("Name", "N/A")
                    gpu["driver"] = data.get("DriverVersion", "N/A")
                    gpu["memory_total"] = data.get("AdapterRAM", 0)
            except Exception:
                pass
            try:
                r = subprocess.run(
                    ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
                     "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=3
                )
                if r.returncode == 0 and r.stdout.strip():
                    parts = r.stdout.strip().split(", ")
                    if len(parts) >= 4:
                        gpu["usage"] = int(parts[0])
                        gpu["memory_used"] = int(parts[1])
                        gpu["memory_total"] = int(parts[2])
                        gpu["temperature"] = int(parts[3])
            except Exception:
                pass
        return gpu

    def scan_processes(self, top_n=10):
        procs = []
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                info = p.info
                if info.get('cpu_percent') is not None:
                    procs.append(info)
            except Exception:
                continue
        procs.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
        return procs[:top_n]

    def scan_system(self):
        try:
            boot = psutil.boot_time()
            uptime = time.time() - boot
            return {
                "os": platform.system() + " " + platform.release(),
                "platform": platform.platform(),
                "processor": platform.processor() or "Unknown",
                "machine": platform.machine(),
                "uptime": f"{int(uptime//86400)}d {int((uptime%86400)//3600)}h {int((uptime%3600)//60)}m",
                "uptime_seconds": int(uptime)
            }
        except Exception:
            return {"os": "Unknown", "uptime": "N/A"}
