import psutil


class SystemScanner:
    def __init__(self, os_type):
        self.os_type = os_type

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
        return {
            "bytes_sent": stats.bytes_sent, "bytes_recv": stats.bytes_recv,
            "packets_sent": stats.packets_sent, "packets_recv": stats.packets_recv
        }

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
