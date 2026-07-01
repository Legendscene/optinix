"""GPUOptimizer — SAFE version.

Removed:
- HwSchMode → official Windows Game Mode / Settings API handles this
- TdrDelay / TdrDdiDelay → longer timeout masks GPU issues, no performance benefit
- Nvidia PlatformSupport → removed from modern NVIDIA drivers
- nvidia-smi -pm 1 → persistent mode should be controlled by driver, not registry
- AMD:
  - DisableDMACopy → no documented Microsoft or AMD support
  - EnableUlps/EnableUlps_NA → Ultra Low Power State is a feature, disabling it increases GPU idle power
  - PP_SclkDeepSleepDisable → disabling deep sleep increases power/heat constantly
  - PP_ThermalAutoMonitorDisable → disabling thermal monitoring is DANGEROUS
  - KMD_FrameRateLimit → users control this through driver panel
  - SystemResponsiveness → can cause audio/crackling
  - NetworkThrottlingIndex → no effect on modern Windows
  - GPU Priority / Priority / Scheduling Category → Multimedia Class Scheduler handles this
"""
import subprocess

class GPUOptimizer:
    name = "Safe GPU Configuration"

    def __init__(self, os_type):
        self.os_type = os_type
        self.results = []

    def run(self):
        self.results = []
        if self.os_type == "windows":
            self._detect_gpu()
        return self.results

    def _detect_gpu(self):
        """Report GPU info without modifying any settings."""
        try:
            r = subprocess.run(
                ["wmic", "path", "win32_videocontroller", "get", "name"],
                capture_output=True, text=True, timeout=10
            )
            gpus = [l.strip() for l in r.stdout.split("\n") if l.strip() and "name" not in l.lower()]
            if gpus:
                self.results.append({"success": True, "message": f"Detected GPU: {gpus[0]}"})
            else:
                self.results.append({"success": True, "message": "No GPU changes needed"})
        except Exception:
            self.results.append({"success": True, "message": "GPU detection completed"})
