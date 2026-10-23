"""GamingOptimizer — SAFE version.

Removed:
- SystemResponsiveness=0 → Can cause audio crackling and input lag during gaming
- NetworkThrottlingIndex → No effect on modern Windows
- UserPreferencesMask binary → opaque magic value, use VisualFXSetting instead
- VisualFXSetting=2 → UI preference, should be user choice
- Mouse acceleration Registry → Games use raw input API, no effect
- HwSchMode → uses official Windows Game Mode API instead
- TdrDelay/TdrDdiDelay → Longer timeout masks GPU issues, no performance benefit
"""
import subprocess
from core.base import OptimizerBase
from core.config import CONFIG


class GamingOptimizer(OptimizerBase):
    name = "Safe Gaming Optimization"
    description = "Enables Windows Game Mode and disables Game DVR to improve gaming performance"
    category = "safe"
    benefit = "Improves gaming performance by prioritizing game processes and reducing GPU overhead"
    risks = "Minimal. Uses official Windows API. Game DVR disabling can be reverted."
    admin_required = False
    requirements = {}

    def run(self):
        if CONFIG.os_type == "windows":
            self._enable_game_mode()
            self._disable_game_dvr()
        return [r.to_dict() for r in self.results]

    def _enable_game_mode(self):
        """Safe: Enable Windows Game Mode (official API)."""
        try:
            subprocess.run([
                "reg", "add", "HKCU\\Software\\Microsoft\\GameBar",
                "/v", "AllowAutoGameMode", "/t", "REG_DWORD", "/d", "1", "/f"
            ], capture_output=True, timeout=5)
            subprocess.run([
                "reg", "add", "HKCU\\Software\\Microsoft\\GameBar",
                "/v", "AutoGameModeEnabled", "/t", "REG_DWORD", "/d", "1", "/f"
            ], capture_output=True, timeout=5)
            self.add_result(True, "Windows Game Mode enabled")
        except Exception as e:
            self.add_result(False, f"Game Mode: {e}")

    def _disable_game_dvr(self):
        """Safe: Disable Game DVR (background recording)."""
        try:
            subprocess.run([
                "reg", "add", "HKCU\\System\\GameConfigStore",
                "/v", "GameDVR_Enabled", "/t", "REG_DWORD", "/d", "0", "/f"
            ], capture_output=True, timeout=5)
            subprocess.run([
                "reg", "add", "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\GameDVR",
                "/v", "AppCaptureEnabled", "/t", "REG_DWORD", "/d", "0", "/f"
            ], capture_output=True, timeout=5)
            self.add_result(True, "Game DVR disabled (reduces GPU overhead)")
        except Exception as e:
            self.add_result(False, f"Game DVR: {e}")
