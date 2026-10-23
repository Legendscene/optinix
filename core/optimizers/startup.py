from typing import Dict, Any, List
from core.base import OptimizerBase, OPTIMIZER_CATEGORY_ADVANCED
from core.config import CONFIG

SAFE_STARTUP_PREFIXES = [
    "Windows Security", "Microsoft Defender", "Windows Defender",
    "SecurityHealth", "OneDrive", "Microsoft OneDrive",
    "Microsoft Teams", "Teams", "Discord", "Slack",
    "Steam", "Epic Games", "Battle.net", "GOG Galaxy",
    "Spotify", "Apple Music", "iTunes",
    "Dropbox", "Google Drive", "Box Sync",
    "Java", "Adobe", "Creative Cloud",
    "Intel", "AMD", "NVIDIA", "Realtek",
    "Synaptics", "Dell", "HP", "Lenovo", "ASUS",
    "Logitech", "Corsair", "Razer", "SteelSeries",
    "Python", "Node.js", "Git",
    "Microsoft Edge", "Chrome", "Firefox", "Brave", "Opera",
    "Cortana",
]


class StartupOptimizer(OptimizerBase):
    name = "Startup Optimization"
    description = "Disables all unnecessary startup programs for faster boot times"
    category = OPTIMIZER_CATEGORY_ADVANCED
    benefit = "Faster boot times, reduced background resource usage"
    risks = "May disable legitimate startup programs needed for some hardware or software"
    admin_required = True
    requirements = {}

    def __init__(self):
        super().__init__()
        self.os_type = CONFIG.os_type

    def run(self) -> List[Dict[str, Any]]:
        self.results = []
        self.logger.info("Starting startup optimization")
        self._analyze_startup()
        return [r.to_dict() for r in self.results]

    def _analyze_startup(self):
        try:
            from core.startup_manager import StartupManager
            sm = StartupManager(self.os_type)
            apps = sm.list_startup_apps()
            disabled = 0
            kept = 0
            for app in apps:
                if any(app["name"].startswith(p) for p in SAFE_STARTUP_PREFIXES):
                    kept += 1
                    continue
                try:
                    sm.toggle_startup(app["name"], False)
                    disabled += 1
                except Exception:
                    pass
            if disabled > 0:
                self.add_result(True, f"Disabled {disabled} startup programs, kept {kept} safe entries")
            else:
                self.add_result(True, f"No startup apps to disable (kept {kept} safe entries)")
        except Exception as e:
            self.logger.error(f"Startup optimization failed: {e}")
            self.add_result(False, f"Startup optimization failed: {e}")
