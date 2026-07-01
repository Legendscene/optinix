"""ExtremeTuner — SAFE version.

ALL dangerous tweaks removed:
- PROCTHROTTLEMIN 100: NEVER set min processor to 100% (causes overheating, battery drain)
- CPMINCORES 100: Prevents Windows from parking idle cores (no benefit, more power)
- IDLEDISABLE 1: Prevents CPU from entering idle states (can reduce CPU lifespan)
- DisablePagingExecutive: Can cause OOM on <16GB systems
- LargeSystemCache: Windows manages this dynamically
- IoPageLockLimit: No effect on Win 10+
- NetworkThrottlingIndex: Outdated, Windows 11 manages QoS natively
- EnablePrefetcher/EnableSuperfetch=0: HARMS performance on SSD (SysMain optimizes boot/app launch)
- Win32PrioritySeparation: Use default (balanced)
- IRQ8Priority: No effect since Windows XP
- TcpAckFrequency/TCPNoDelay: No effect on Win 10+ TCP stack
- bcdedit useplatformtick/disabledynamictick: TSC is superior to HPET
- GlobalTimerResolutionRequests: Windows manages this
- SystemResponsiveness=0: Can cause audio crackling, input lag
- fsutil memoryusage=2: No documented benefit
"""
import subprocess
from core.rollback_engine import RollbackEngine


class ExtremeTuner:
    def __init__(self, os_type):
        self.os_type = os_type
        self.rollback = RollbackEngine(os_type) if os_type == "windows" else None

    def apply_all(self):
        results = []
        if self.rollback:
            r = self.rollback.create_restore_point("Optinix Extreme Tuning")
            results.append(r)
            self.rollback.snapshot_power_plan()

        if self.os_type == "windows":
            results.extend(self._safe_windows_tweaks())
        elif self.os_type == "linux":
            results.extend(self._linux_extreme())
        elif self.os_type == "macos":
            results.extend(self._macos_extreme())

        if self.rollback:
            self.rollback.save_snapshot()
        return results

    def _safe_windows_tweaks(self):
        """🟢 Safe tweaks only. No powercfg aggressive settings, no bcdedit, no dangerous reg."""
        results = []

        # Safe: enable HW GPU scheduling (user opt-in, modern Windows default)
        try:
            subprocess.run([
                "reg", "add", "HKLM\\SYSTEM\\CurrentControlSet\\Control\\GraphicsDrivers",
                "/v", "HwSchMode", "/t", "REG_DWORD", "/d", "2", "/f"
            ], capture_output=True, timeout=5)
            results.append({"success": True, "message": "GPU: Hardware-accelerated scheduling enabled"})
        except Exception:
            pass

        # Safe: flush DNS
        try:
            subprocess.run(["ipconfig", "/flushdns"], capture_output=True, timeout=10)
            results.append({"success": True, "message": "DNS cache flushed"})
        except Exception:
            pass

        return results

    def _linux_extreme(self):
        results = []
        try:
            settings = {
                "vm.swappiness": "10",
                "vm.dirty_ratio": "20",
                "vm.dirty_background_ratio": "10",
                "vm.vfs_cache_pressure": "100",
            }
            for k, v in settings.items():
                subprocess.run(["sudo", "sysctl", "-w", f"{k}={v}"], capture_output=True, timeout=5)
            results.append({"success": True, "message": "Linux: safe sysctl params applied"})
        except Exception as e:
            results.append({"success": False, "message": f"Linux tuning: {e}"})
        return results

    def _macos_extreme(self):
        return [{"success": True, "message": "macOS manages performance automatically"}]
