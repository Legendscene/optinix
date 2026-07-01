import psutil
import subprocess
from typing import Dict, List, Any

class MemoryManager:
    def __init__(self, os_type: str):
        self.os_type = os_type

    def get_processes(self) -> List[Dict[str, Any]]:
        procs = []
        for p in psutil.process_iter(['pid', 'name', 'memory_info', 'memory_percent', 'cpu_percent', 'status']):
            try:
                mi = p.info.get('memory_info')
                procs.append({
                    "pid": p.info['pid'],
                    "name": p.info['name'] or "Unknown",
                    "rss_mb": round(mi.rss / (1024 * 1024), 1) if mi else 0,
                    "vms_mb": round(mi.vms / (1024 * 1024), 1) if mi else 0,
                    "memory_percent": round(p.info.get('memory_percent', 0) or 0, 1),
                    "cpu_percent": round(p.info.get('cpu_percent', 0) or 0, 1),
                    "status": p.info.get('status', ''),
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        procs.sort(key=lambda x: x['rss_mb'], reverse=True)
        return procs[:50]

    def free_ram(self) -> Dict[str, Any]:
        results = []
        if self.os_type == "windows":
            try:
                subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     "[System.GC]::Collect(); [System.GC]::WaitForPendingFinalizers()"],
                    capture_output=True, timeout=15
                )
                results.append({"success": True, "message": "GC completed"})
            except Exception as e:
                results.append({"success": False, "message": f"GC failed: {e}"})
            try:
                import ctypes
                ctypes.windll.ntdll.NtSetSystemInformation(
                    0x57,
                    bytes([0x01, 0x00, 0x00, 0x00]),
                    4
                )
                results.append({"success": True, "message": "Standby list purged"})
            except Exception:
                pass
        return {"success": True, "results": results}

    def auto_optimize(self) -> Dict[str, Any]:
        results = []
        targets = ["Spotify", "Discord", "Skype", "OneDrive", "Teams", "Slack"]
        killed = 0
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] in targets:
                    proc.kill()
                    killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        results.append({"success": True, "message": f"Killed {killed} heavy processes"})
        ram = self.free_ram()
        results.extend(ram.get("results", []))
        return {"success": True, "results": results}

    def get_info(self) -> Dict[str, Any]:
        vm = psutil.virtual_memory()
        sm = psutil.swap_memory()
        return {
            "total_gb": round(vm.total / (1024**3), 1),
            "available_gb": round(vm.available / (1024**3), 1),
            "used_gb": round(vm.used / (1024**3), 1),
            "percent": vm.percent,
            "swap_total_gb": round(sm.total / (1024**3), 1),
            "swap_used_gb": round(sm.used / (1024**3), 1),
            "swap_percent": sm.percent,
        }
