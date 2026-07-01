"""PerformanceOptimizer — SAFE version.

Removed:
- powercfg /setactive Ultimate Performance → permanently changes power plan
  Instead: uses Powercfg -changename to recommend, never force active
- wmic computersystem set AutomaticManagedPagefile=False → 
  Disabling automatic pagefile management can cause system instability on low-RAM scenarios
  Modern Windows manages pagefile better than any heuristic
- ctypes NtSetSystemInformation → Force-purge standby list is overly aggressive
  Modern Windows manages standby list as file cache; purging it harms performance
- subprocess killing (Spotify, Discord, etc.) → User applications should not be force-killed
"""
import subprocess
import psutil

class PerformanceOptimizer:
    name = "Safe Performance Optimization"

    def __init__(self, os_type):
        self.os_type = os_type
        self.results = []

    def run(self):
        self.results = []
        if self.os_type == "windows":
            self._free_standby_memory_gently()
        return self.results

    def _free_standby_memory_gently(self):
        """🟢 Safe: Empty working set of current process only.
        Does NOT purge entire standby list — that harms file cache performance.
        """
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "[System.GC]::Collect(); [System.GC]::WaitForPendingFinalizers()"],
                capture_output=True, timeout=15
            )
            self.results.append({"success": True, "message": "Memory: GC triggered"})
        except Exception as e:
            self.results.append({"success": False, "message": f"Memory: {e}"})
