import psutil
import platform
import subprocess


class SmartDetector:
    def __init__(self, os_type):
        self.os_type = os_type
        self._info = None

    def get_recommendations(self):
        info = self.get_hardware_info()
        recs = []

        if info.get("ram_gb", 0) <= 8:
            recs.append({"type": "memory", "priority": "high",
                         "message": "Low RAM detected. Close background apps and disable startup programs to free memory."})

        if info.get("is_laptop"):
            recs.append({"type": "power", "priority": "medium",
                         "message": "Laptop detected. Consider balanced power plan when on battery."})

        if info.get("is_ssd"):
            recs.append({"type": "disk", "priority": "medium",
                         "message": "SSD detected. TRIM is enabled. Do NOT defrag this drive."})

        if info.get("is_hdd"):
            recs.append({"type": "disk", "priority": "low",
                         "message": "HDD detected. Regular defragmentation recommended."})

        if info.get("gpu_name") and "nvidia" in info["gpu_name"].lower():
            recs.append({"type": "gpu", "priority": "medium",
                         "message": "NVIDIA GPU detected. Enable hardware scheduling and persistent mode."})
        elif info.get("gpu_name") and "amd" in info["gpu_name"].lower():
            recs.append({"type": "gpu", "priority": "medium",
                         "message": "AMD GPU detected. Disable ULPS and deep sleep for lower latency."})

        if info.get("cpu_cores", 0) >= 8:
            recs.append({"type": "cpu", "priority": "low",
                         "message": "8+ cores detected. Consider core parking disable for full performance."})

        if info.get("uptime_days", 0) > 7:
            recs.append({"type": "system", "priority": "medium",
                         "message": f"System up for {info['uptime_days']} days. Restart recommended to clear memory leaks."})

        return recs

    def get_hardware_info(self):
        if self._info:
            return self._info

        info = {"os": platform.system() + " " + platform.release(),
                "cpu_brand": platform.processor() or "Unknown",
                "cpu_cores": psutil.cpu_count(logical=False) or 1,
                "cpu_threads": psutil.cpu_count(logical=True) or 1,
                "ram_gb": round(psutil.virtual_memory().total / (1024**3), 1),
                "is_laptop": self._detect_laptop(),
                "is_ssd": None,
                "is_hdd": None,
                "gpu_name": "N/A",
                "uptime_days": round((time.time() - psutil.boot_time()) / 86400, 1)}

        try:
            for part in psutil.disk_partitions():
                if part.mountpoint == "C:\\" or part.mountpoint == "/":
                    try:
                        r = subprocess.run(
                            ["powershell", "-NoProfile", "-Command",
                             "Get-CimInstance -Namespace root\\cimv2 -ClassName MSFT_PhysicalDisk | "
                             "Select-Object -First 1 MediaType | ConvertTo-Json"],
                            capture_output=True, text=True, timeout=10
                        )
                        if r.stdout.strip():
                            import json
                            mt = json.loads(r.stdout)
                            if mt == 4:
                                info["is_ssd"] = True
                            else:
                                info["is_ssd"] = False
                    except Exception:
                        pass
                    break
        except Exception:
            pass

        try:
            if self.os_type == "windows":
                r = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     "Get-CimInstance Win32_VideoController -EA SilentlyContinue | Select -First 1 Name | ConvertTo-Json"],
                    capture_output=True, text=True, timeout=10
                )
                if r.stdout.strip():
                    import json
                    data = json.loads(r.stdout)
                    if isinstance(data, dict):
                        info["gpu_name"] = data.get("Name", "N/A")
        except Exception:
            pass

        self._info = info
        return info

    def _detect_laptop(self):
        try:
            if self.os_type == "windows":
                r = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     "Get-CimInstance -ClassName Win32_Battery -EA SilentlyContinue | Select-Object -First 1 | ConvertTo-Json"],
                    capture_output=True, text=True, timeout=10
                )
                return bool(r.stdout.strip())
            return False
        except Exception:
            return False


import time
