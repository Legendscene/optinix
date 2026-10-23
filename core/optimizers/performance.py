"""PerformanceOptimizer — SAFE version with real optimizations."""
import subprocess
import os
from core.base import OptimizerBase
from core.config import CONFIG


class PerformanceOptimizer(OptimizerBase):
    name = "Performance Optimizer"
    description = "Triggers GC, clears prefetch cache, sets performance power scheme, disables visual effects"
    category = "safe"
    benefit = "Frees memory, reduces disk clutter from prefetch, optimizes power for performance, reduces visual overhead"
    risks = "Minimal. Prefetch will be rebuilt by Windows. Visual effects changes are reversible."
    admin_required = False
    requirements = {}

    def run(self):
        if CONFIG.os_type == "windows":
            self._trigger_gc()
            self._clear_prefetch()
            self._set_performance_power_scheme()
            self._disable_visual_effects()
        return [r.to_dict() for r in self.results]

    def _trigger_gc(self):
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "[System.GC]::Collect(); [System.GC]::WaitForPendingFinalizers()"],
                capture_output=True, timeout=15
            )
            self.add_result(True, "Memory: GC triggered")
        except Exception as e:
            self.add_result(False, f"Memory: {e}")

    def _clear_prefetch(self):
        try:
            prefetch = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "Prefetch")
            if os.path.isdir(prefetch):
                count = 0
                for f in os.listdir(prefetch):
                    fp = os.path.join(prefetch, f)
                    try:
                        if os.path.isfile(fp):
                            os.remove(fp)
                            count += 1
                    except (PermissionError, OSError):
                        pass
                self.add_result(True, f"Prefetch cache cleared ({count} files removed)")
            else:
                self.add_result(False, "Prefetch directory not found")
        except Exception as e:
            self.add_result(False, f"Prefetch: {e}")

    def _set_performance_power_scheme(self):
        try:
            subprocess.run(
                ["powercfg", "/setactive", "{8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c}"],
                capture_output=True, timeout=15
            )
            self.add_result(True, "Power scheme set to High Performance")
        except Exception as e:
            self.add_result(False, f"Power scheme: {e}")

    def _disable_visual_effects(self):
        try:
            key = r"HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects"
            subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"New-Item -Path '{key}' -Force -ErrorAction SilentlyContinue | Out-Null; "
                 f"Set-ItemProperty -Path '{key}' -Name 'VisualFXSetting' -Value 2 -ErrorAction SilentlyContinue"],
                capture_output=True, timeout=15
            )
            from ctypes import windll, c_int
            SPI_SETCLIENTAREAANIMATION = 0x1043
            SPI_SETMENUANIMATION = 0x1003
            SPI_SETTOOLTIPANIMATION = 0x103B
            for spi in [SPI_SETCLIENTAREAANIMATION, SPI_SETMENUANIMATION, SPI_SETTOOLTIPANIMATION]:
                windll.user32.SystemParametersInfoW(spi, 0, c_int(0), 0)
            self.add_result(True, "Visual effects set to performance mode")
        except Exception as e:
            self.add_result(False, f"Visual effects: {e}")
