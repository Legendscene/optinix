import time
import threading
import json
import os


class MaintenanceScheduler:
    def __init__(self, os_type):
        self.os_type = os_type
        self._running = False
        self._thread = None
        self._config_path = self._get_config_path()
        self._config = self._load_config()

    def _get_config_path(self):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base, "config", "scheduler.json")

    def _load_config(self):
        default = {
            "enabled": False,
            "interval_hours": 24,
            "tasks": {
                "cleanup": True,
                "dns_flush": True,
                "ram_boost": False,
                "disk_trim": False
            }
        }
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path) as f:
                    return {**default, **json.load(f)}
            except Exception:
                pass
        return default

    def save_config(self, config):
        try:
            os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
            with open(self._config_path, "w") as f:
                json.dump(config, f, indent=2)
            self._config = config
            return True
        except Exception:
            return False

    def get_config(self):
        return self._config

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            if self._config.get("enabled"):
                self._run_maintenance()
            time.sleep(60)

    def _run_maintenance(self):
        tasks = self._config.get("tasks", {})
        results = []
        if tasks.get("cleanup"):
            try:
                from core.optimizers.cleanup import CleanupOptimizer
                CleanupOptimizer(self.os_type).run()
                results.append("cleanup")
            except Exception:
                pass
        if tasks.get("dns_flush"):
            try:
                import subprocess
                subprocess.run(["ipconfig", "/flushdns"], capture_output=True, timeout=10)
                results.append("dns_flush")
            except Exception:
                pass
        return results
