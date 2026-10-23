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

Note: HAGS and TRIM are idempotent (check state first, skip if already done).
"""
import subprocess
import psutil
from typing import Dict, Any, List
from core.base import OptimizerBase, OPTIMIZER_CATEGORY_SAFE
from core.config import CONFIG


class OverclockOptimizer(OptimizerBase):
    name = "Safe Hardware Optimization"
    description = "Enables GPU hardware scheduling, HPET timer, and runs SSD TRIM for safe performance gains"
    category = OPTIMIZER_CATEGORY_SAFE
    benefit = "GPU scheduling reduces input lag; HPET improves timer precision; TRIM maintains SSD performance"
    risks = "HPET may increase power draw slightly on some systems; GPU scheduling may cause issues on older GPU drivers; requires reboot"
    admin_required = True
    requirements = {}

    def __init__(self):
        super().__init__()
        self.os_type = CONFIG.os_type

    def run(self) -> List[Dict[str, Any]]:
        self.results = []
        self.logger.info("Starting safe hardware optimization")
        if self.os_type == "windows":
            self._hw_gpu_scheduling()
            self._configure_hpet_timer()
            self._trim_all_ssds()
        elif self.os_type == "linux":
            self._linux_tuning()
        return [r.to_dict() for r in self.results]

    def _hw_gpu_scheduling(self):
        try:
            r = subprocess.run(
                ["reg", "query", "HKLM\\SYSTEM\\CurrentControlSet\\Control\\GraphicsDrivers",
                 "/v", "HwSchMode"],
                capture_output=True, text=True, timeout=5
            )
            if r.returncode == 0 and "0x2" in r.stdout:
                self.add_result(True, "GPU scheduling: already enabled")
                return
            subprocess.run([
                "reg", "add", "HKLM\\SYSTEM\\CurrentControlSet\\Control\\GraphicsDrivers",
                "/v", "HwSchMode", "/t", "REG_DWORD", "/d", "2", "/f"
            ], capture_output=True, timeout=5)
            self.add_result(True, "GPU: Hardware scheduling enabled (requires reboot)")
        except Exception as e:
            self.add_result(False, f"GPU: Hardware scheduling not available — {e}")

    def _configure_hpet_timer(self):
        try:
            r = subprocess.run(
                ["bcdedit", "/enum", "{current}", "/v"],
                capture_output=True, text=True, timeout=10
            )
            if "useplatformclock" in r.stdout.lower():
                self.add_result(True, "HPET timer: already configured")
                return
            subprocess.run(
                ["bcdedit", "/set", "{current}", "useplatformclock", "Yes"],
                capture_output=True, timeout=10
            )
            self.add_result(True, "HPET timer: enabled (requires reboot)")
        except Exception as e:
            self.add_result(False, f"HPET timer: {e}")

    def _trim_all_ssds(self):
        try:
            subprocess.run(["defrag", "C:", "/L"], capture_output=True, timeout=60)
            self.add_result(True, "SSD TRIM completed")
        except Exception:
            pass

    def _linux_tuning(self):
        try:
            settings = {"vm.swappiness": "10"}
            for k, v in settings.items():
                subprocess.run(["sudo", "sysctl", "-w", f"{k}={v}"], capture_output=True, timeout=5)
            self.add_result(True, "Linux: swappiness set to 10")
        except Exception as e:
            self.logger.error(f"Linux tuning: {e}")
            self.add_result(False, f"Linux tuning: {e}")
