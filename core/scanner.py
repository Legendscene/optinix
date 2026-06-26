import psutil
import time
import subprocess
import platform


class SystemScanner:
    def __init__(self, os_type):
        self.os_type = os_type
        self._prev_net = None
        self._prev_net_time = None
        self._cpu_count = psutil.cpu_count(logical=True)
        # Warm up cpu_percent
        psutil.cpu_percent(interval=0)
        psutil.cpu_percent(interval=0, percpu=True)

    def full_scan(self):
        return {
            "cpu": self.scan_cpu(),
            "memory": self.scan_memory(),
            "disk": self.scan_disk(),
            "network": self.scan_network(),
            "gpu": self.scan_gpu(),
            "processes": self.scan_processes(),
            "system": self.scan_system()
        }

    def scan_cpu(self):
        try:
            percent = psutil.cpu_percent(interval=0.1)
            per_cpu = psutil.cpu_percent(interval=0, percpu=True)
        except Exception:
            percent = 0
            per_cpu = []

        freq = psutil.cpu_freq()
        try:
            temps = psutil.sensors_temperatures()
            cpu_temp = None
            for name, entries in temps.items():
                if any(k in name.lower() for k in ["core", "cpu", "k10", "zen"]):
                    cpu_temp = entries[0].current if entries else None
                    break
        except Exception:
            cpu_temp = None

        return {
            "percent": percent,
            "logical": self._cpu_count,
            "physical": psutil.cpu_count(logical=False),
            "freq": freq._asdict() if freq else None,
            "per_cpu": per_cpu,
            "temperature": cpu_temp
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
            except PermissionError:
                continue
        return disks

    def scan_network(self):
        stats = psutil.net_io_counters()
        now = time.time()
        speed_up = speed_down = 0
        if self._prev_net and self._prev_net_time:
            dt = now - self._prev_net_time
            if dt > 0:
                speed_up = (stats.bytes_sent - self._prev_net.bytes_sent) / dt
                speed_down = (stats.bytes_recv - self._prev_net.bytes_recv) / dt
        self._prev_net = stats
        self._prev_net_time = now
        interfaces = []
        try:
            addrs = psutil.net_if_addrs()
            stats2 = psutil.net_if_stats()
            for name in addrs:
                info = {"name": name}
                if name in stats2:
                    info["is_up"] = stats2[name].isup
                    info["speed"] = stats2[name].speed
                interfaces.append(info)
        except Exception:
            pass
        return {
            "bytes_sent": stats.bytes_sent, "bytes_recv": stats.bytes_recv,
            "speed_up": round(speed_up), "speed_down": round(speed_down),
            "interfaces": interfaces
        }

    def scan_gpu(self):
        gpu = {"name": "N/A", "usage": 0, "memory_total": 0, "memory_used": 0, "temperature": 0, "driver": "N/A"}
        if self.os_type == "windows":
            try:
                r = subprocess.run(
                    ["powershell", "-Command",
                     "Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM, DriverVersion | ConvertTo-Json"],
                    capture_output=True, text=True, timeout=10
                )
                if r.stdout.strip():
                    import json
                    data = json.loads(r.stdout)
                    if isinstance(data, list): data = data[0] if data else {}
                    gpu["name"] = data.get("Name", "N/A")
                    gpu["driver"] = data.get("DriverVersion", "N/A")
                    gpu["memory_total"] = data.get("AdapterRAM", 0)
            except Exception:
                pass
            try:
                r = subprocess.run(
                    ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
                     "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=5
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
                if info['cpu_percent'] is not None:
                    procs.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        procs.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
        return procs[:top_n]

    def scan_system(self):
        boot = psutil.boot_time()
        uptime = time.time() - boot
        return {
            "os": platform.system() + " " + platform.release(),
            "platform": platform.platform(),
            "processor": platform.processor(),
            "machine": platform.machine(),
            "uptime": f"{int(uptime//86400)}d {int((uptime%86400)//3600)}h {int((uptime%3600)//60)}m",
            "uptime_seconds": int(uptime)
        }
