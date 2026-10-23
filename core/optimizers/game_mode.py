import subprocess
import psutil
from core.base import OptimizerBase
from core.config import CONFIG
from core.game_mode import GameMode


class GameModeOptimizer(OptimizerBase):
    name = "Game Mode Optimizer"
    description = "Enables Windows Game Mode, detects running game processes, boosts their priority to HIGH, and disables Game DVR to reduce GPU overhead"
    category = "safe"
    benefit = "Improves gaming performance by prioritizing game processes and reducing background GPU recording overhead"
    risks = "Minimal. Uses official Windows Game Mode API. Game DVR disabling can be reverted via Windows Settings."
    admin_required = False
    requirements = {}

    def run(self):
        game_mode = GameMode(CONFIG.os_type)

        games = game_mode.get_game_processes()
        game_count = len(games)
        if game_count > 0:
            self.add_result(True, f"{game_count} game process(es) detected", games_detected=game_count)
        else:
            self.add_result(False, "No game processes detected", games_detected=0)

        self._enable_game_mode_registry()
        self._boost_game_priorities(games)
        self._disable_game_dvr()

        return [r.to_dict() for r in self.results]

    def _enable_game_mode_registry(self):
        try:
            subprocess.run([
                "reg", "add", "HKCU\\Software\\Microsoft\\GameBar",
                "/v", "AllowAutoGameMode", "/t", "REG_DWORD", "/d", "1", "/f"
            ], capture_output=True, timeout=5)
            self.add_result(True, "Windows Game Mode enabled (registry)", registry_key="AllowAutoGameMode")
        except Exception as e:
            self.add_result(False, f"Game Mode registry: {e}")

    def _boost_game_priorities(self, games):
        boosted = 0
        for game in games:
            try:
                p = psutil.Process(game["pid"])
                p.nice(psutil.HIGH_PRIORITY_CLASS)
                boosted += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                self.add_result(False, f"Could not boost {game['name']} (PID {game['pid']}): {e}")
        if boosted > 0:
            self.add_result(True, f"Priority boosted to HIGH for {boosted} game process(es)", priority_boosted=boosted)
        elif len(games) > 0:
            self.add_result(False, "No game processes could be boosted", priority_boosted=0)

    def _disable_game_dvr(self):
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
