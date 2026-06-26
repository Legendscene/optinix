import psutil
import time


class SystemScanner:
    def __init__(self, os_type):
        self.os_type = os_type
        self._prev_net = None
        self._prev_net_time = None

    def full_scan(self):
        return {
            "cpu": self.scan_cpu(),
            "memory": self.scan_memory(),
            "disk": self.scan_disk(),
            "network": self.scan_network(),
            "processes": self.scan_processes()
        }

    def scan_cpu(self):
        return {
            "percent": psutil.cpu_percent(interval=0.5),
            "logical": psutil.cpu_count(logical=True),
            "physical": psutil.cpu_count(logical=False),
            "freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
        }

    def scan_memory(self):
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return {
            "total": mem.total, "available": mem.available,
            "used": mem.used, "percent": mem.percent,
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
        speed_up = 0
        speed_down = 0

        if self._prev_net and self._prev_net_time:
            dt = now - self._prev_net_time
            if dt > 0:
                speed_up = (stats.bytes_sent - self._prev_net.bytes_sent) / dt
                speed_down = (stats.bytes_recv - self._prev_net.bytes_recv) / dt

        self._prev_net = stats
        self._prev_net_time = now

        return {
            "bytes_sent": stats.bytes_sent,
            "bytes_recv": stats.bytes_recv,
            "packets_sent": stats.packets_sent,
            "packets_recv": stats.packets_recv,
            "speed_up": round(speed_up),
            "speed_down": round(speed_down)
        }
