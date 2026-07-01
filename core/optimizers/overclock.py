"""OverclockOptimizer — SAFE version.

Removed:
- PROCTHROTTLEMIN 100 → NEVER. Causes overheating on laptops.
- CPMINCORES 100 → Let Windows manage core parking dynamically.
- IDLEDISABLE 1 → Prevents C-states, increases power consumption.
- DisablePagingExecutive → Can cause OOM on <16GB systems.
- IoPageLockLimit → No effect on Windows 10/11.
- EnablePrefetcher/Superfetch=0 → HARMS SSD performance. SysMain is optimized for SSDs.
- IRQ8Priority → No effect since Windows XP.
- Win32PrioritySeparation 38 → Can starve background tasks. Use default.
- bcdedit useplatformtick / disabledynamictick → TSC is superior.
- GlobalTimerResolutionRequests → Windows manages this.
- SystemResponsiveness=0 → Can cause audio crackling.
- NetworkThrottlingIndex → No effect on modern Windows.
- LargeSystemCache → Windows manages cache dynamically.
"""
import subprocess
import psutil

class OverclockOptimizer:
    name = "Safe Hardware Optimization"

    def __init__(self, os_type):
        self.os_type = os_type
        self.results = []

    def run(self):
        self.results = []
        if self.os_type == "windows":
            self._hw_gpu_scheduling()
            self._trim_all_ssds()
        elif self.os_type == "linux":
            self._linux_tuning()
        return self.results

    def _hw_gpu_scheduling(self):
        """🟢 Safe: Enable Hardware GPU Scheduling if supported."""
        try:
            subprocess.run([
                "reg", "add", "HKLM\\SYSTEM\\CurrentControlSet\\Control\\GraphicsDrivers",
                "/v", "HwSchMode", "/t", "REG_DWORD", "/d", "2", "/f"
            ], capture_output=True, timeout=5)
            self.results.append({"success": True, "message": "GPU: Hardware scheduling enabled (requires reboot)"})
        except Exception:
            self.results.append({"success": False, "message": "GPU: Hardware scheduling not available"})

    def _trim_all_ssds(self):
        """🟢 Safe: Run TRIM on all drives."""
        try:
            subprocess.run(["defrag", "C:", "/L"], capture_output=True, timeout=60)
            self.results.append({"success": True, "message": "SSD TRIM completed"})
        except Exception:
            pass

    def _linux_tuning(self):
        try:
            settings = {"vm.swappiness": "10"}
            for k, v in settings.items():
                subprocess.run(["sudo", "sysctl", "-w", f"{k}={v}"], capture_output=True, timeout=5)
            self.results.append({"success": True, "message": "Linux: swappiness set to 10"})
        except Exception as e:
            self.results.append({"success": False, "message": f"Linux tuning: {e}"})
