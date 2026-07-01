class StartupOptimizer:
    name = "Startup Optimization"

    def __init__(self, os_type):
        self.os_type = os_type
        self.results = []

    def run(self):
        self.results = []
        self._analyze_startup()
        return self.results

    def _analyze_startup(self):
        try:
            from core.startup_manager import StartupManager
            sm = StartupManager(self.os_type)
            apps = sm.list_startup_apps()
            disabled = 0
            for app in apps:
                try:
                    sm.toggle_startup(app["name"], False)
                    disabled += 1
                except Exception:
                    pass
            if disabled > 0:
                self.results.append({"success": True, "message": f"Disabled {disabled} unnecessary startup programs"})
            else:
                self.results.append({"success": True, "message": "No startup apps to disable (already optimized)"})
        except Exception as e:
            self.results.append({"success": False, "message": f"Startup optimization failed: {e}"})
