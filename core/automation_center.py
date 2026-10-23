import os
import sys
import json
import time
import uuid
import threading
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from core.config import CONFIG
from core.logger import get_logger
from core.base import OptimizerBase, OPTIMIZER_CATEGORY_SAFE


TASKS_FILE = os.path.join(CONFIG.rollback_dir, "automation_tasks.json")
HISTORY_FILE = os.path.join(CONFIG.rollback_dir, "automation_history.json")
SCHEDULER_CHECK_INTERVAL = 30


@dataclass
class ScheduledTask:
    id: str
    name: str
    action: str
    interval_hours: int
    enabled: bool = True
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    config: Dict[str, Any] = field(default_factory=dict)


class AutomationScheduler:
    def __init__(self):
        self.logger = get_logger("automation")
        self.tasks: Dict[str, ScheduledTask] = {}
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._started_at: Optional[str] = None
        self._load_tasks()

    def _tasks_path(self) -> str:
        return TASKS_FILE

    def _history_path(self) -> str:
        return HISTORY_FILE

    def _load_tasks(self):
        path = self._tasks_path()
        if not os.path.exists(path):
            self.tasks = {}
            return
        try:
            with open(path, "r") as f:
                data = json.load(f)
            self.tasks = {}
            for tid, tdata in data.items():
                self.tasks[tid] = ScheduledTask(**tdata)
        except Exception as e:
            self.logger.error(f"Failed to load tasks: {e}")
            self.tasks = {}

    def _save_tasks(self):
        path = self._tasks_path()
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                data = {tid: {
                    "id": t.id,
                    "name": t.name,
                    "action": t.action,
                    "interval_hours": t.interval_hours,
                    "enabled": t.enabled,
                    "last_run": t.last_run,
                    "next_run": t.next_run,
                    "created_at": t.created_at,
                    "config": t.config,
                } for tid, t in self.tasks.items()}
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save tasks: {e}")

    def _load_history(self) -> Dict[str, List[Dict[str, Any]]]:
        path = self._history_path()
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load history: {e}")
            return {}

    def _save_history(self, history: Dict[str, List[Dict[str, Any]]]):
        path = self._history_path()
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save history: {e}")

    def _append_history(self, task_id: str, entry: Dict[str, Any]):
        history = self._load_history()
        if task_id not in history:
            history[task_id] = []
        history[task_id].append(entry)
        limit = 100
        if len(history[task_id]) > limit:
            history[task_id] = history[task_id][-limit:]
        self._save_history(history)

    def add_task(self, task: ScheduledTask) -> bool:
        try:
            if task.id in self.tasks:
                self.logger.warning(f"Task {task.id} already exists")
                return False
            now = datetime.now()
            if task.interval_hours > 0:
                task.next_run = (now + timedelta(hours=task.interval_hours)).isoformat()
            self.tasks[task.id] = task
            self._save_tasks()
            self.logger.info(f"Added task: {task.name} ({task.id})")
            return True
        except Exception as e:
            self.logger.error(f"Failed to add task: {e}")
            return False

    def remove_task(self, task_id: str) -> bool:
        try:
            if task_id not in self.tasks:
                self.logger.warning(f"Task {task_id} not found")
                return False
            del self.tasks[task_id]
            self._save_tasks()
            self.logger.info(f"Removed task: {task_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to remove task: {e}")
            return False

    def update_task(self, task_id: str, **kwargs) -> bool:
        try:
            if task_id not in self.tasks:
                self.logger.warning(f"Task {task_id} not found")
                return False
            task = self.tasks[task_id]
            for key, val in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, val)
            if "interval_hours" in kwargs and kwargs["interval_hours"] > 0:
                last = datetime.fromisoformat(task.last_run) if task.last_run else datetime.now()
                task.next_run = (last + timedelta(hours=task.interval_hours)).isoformat()
            self._save_tasks()
            self.logger.info(f"Updated task: {task_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to update task: {e}")
            return False

    def enable_task(self, task_id: str) -> bool:
        return self.update_task(task_id, enabled=True)

    def disable_task(self, task_id: str) -> bool:
        return self.update_task(task_id, enabled=False)

    def run_task_now(self, task_id: str) -> Dict[str, Any]:
        if task_id not in self.tasks:
            return {"success": False, "error": f"Task {task_id} not found"}
        task = self.tasks[task_id]
        self.logger.info(f"Running task now: {task.name} ({task.id})")
        result = TaskActions.execute_action(task.action, task.config)
        now_iso = datetime.now().isoformat()
        task.last_run = now_iso
        if task.interval_hours > 0:
            task.next_run = (datetime.now() + timedelta(hours=task.interval_hours)).isoformat()
        else:
            task.next_run = None
        self._save_tasks()
        self._append_history(task_id, {
            "timestamp": now_iso,
            "action": task.action,
            "result": result,
        })
        return result

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        if task_id not in self.tasks:
            return None
        t = self.tasks[task_id]
        return {
            "id": t.id,
            "name": t.name,
            "action": t.action,
            "interval_hours": t.interval_hours,
            "enabled": t.enabled,
            "last_run": t.last_run,
            "next_run": t.next_run,
            "created_at": t.created_at,
            "config": t.config,
        }

    def list_tasks(self) -> List[Dict[str, Any]]:
        return [self.get_task(tid) for tid in sorted(self.tasks.keys())]

    def get_task_history(self, task_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        history = self._load_history()
        entries = history.get(task_id, [])
        return entries[-limit:]

    def get_status(self) -> Dict[str, Any]:
        next_run_time = None
        for t in self.tasks.values():
            if t.enabled and t.next_run:
                if next_run_time is None or t.next_run < next_run_time:
                    next_run_time = t.next_run
        return {
            "running": self._running,
            "task_count": len(self.tasks),
            "enabled_count": sum(1 for t in self.tasks.values() if t.enabled),
            "next_run": next_run_time,
            "started_at": self._started_at,
            "uptime_seconds": int(time.time() - datetime.fromisoformat(self._started_at).timestamp()) if self._started_at else 0,
        }

    def start(self):
        if self._running:
            self.logger.warning("Scheduler already running")
            return
        self._running = True
        self._started_at = datetime.now().isoformat()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self.logger.info("Scheduler started")

    def stop(self):
        self._running = False
        self.logger.info("Scheduler stopped")

    def _loop(self):
        while self._running:
            try:
                self._check_tasks()
            except Exception as e:
                self.logger.error(f"Scheduler loop error: {e}", exc_info=True)
            time.sleep(SCHEDULER_CHECK_INTERVAL)

    def _check_tasks(self):
        now = datetime.now()
        for task in list(self.tasks.values()):
            if not task.enabled:
                continue
            if task.interval_hours <= 0:
                continue
            if not task.next_run:
                task.next_run = (now + timedelta(hours=task.interval_hours)).isoformat()
                self._save_tasks()
                continue
            try:
                next_dt = datetime.fromisoformat(task.next_run)
            except Exception:
                task.next_run = (now + timedelta(hours=task.interval_hours)).isoformat()
                self._save_tasks()
                continue
            if now >= next_dt:
                self.logger.info(f"Triggering scheduled task: {task.name}")
                self.run_task_now(task.id)

    def start_windows_task(self, task_name: str) -> bool:
        try:
            exe = sys.executable if hasattr(sys, 'executable') else "python"
            script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "run_automation.py")
            if not os.path.exists(script):
                script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run_automation.py")
            r = subprocess.run([
                "schtasks", "/Create", "/TN", task_name, "/SC", "ONLOGON",
                "/TR", f'"{exe}" "{script}"',
                "/RL", "HIGHEST", "/F",
            ], capture_output=True, text=True, timeout=15)
            ok = r.returncode == 0
            if ok:
                self.logger.info(f"Windows task '{task_name}' created")
            else:
                self.logger.error(f"Failed to create Windows task: {r.stderr}")
            return ok
        except Exception as e:
            self.logger.error(f"Windows task creation error: {e}")
            return False

    def remove_windows_task(self, task_name: str) -> bool:
        try:
            r = subprocess.run([
                "schtasks", "/Delete", "/TN", task_name, "/F",
            ], capture_output=True, text=True, timeout=15)
            ok = r.returncode == 0
            if ok:
                self.logger.info(f"Windows task '{task_name}' removed")
            else:
                self.logger.error(f"Failed to remove Windows task: {r.stderr}")
            return ok
        except Exception as e:
            self.logger.error(f"Windows task removal error: {e}")
            return False


class TaskActions:
    @staticmethod
    def execute_action(action: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
        config = config or {}
        method_map = {
            "cleanup": TaskActions.run_cleanup,
            "optimize": TaskActions.run_full_optimization,
            "backup": TaskActions.run_backup,
            "scan": TaskActions.run_system_scan,
            "custom": lambda: TaskActions.run_custom(config.get("command", "")),
        }
        handler = method_map.get(action)
        if not handler:
            return {"success": False, "error": f"Unknown action: {action}"}
        try:
            return handler()
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def run_cleanup() -> Dict[str, Any]:
        from core.optimizers.cleanup import CleanupOptimizer
        result = CleanupOptimizer().execute()
        return result

    @staticmethod
    def run_full_optimization() -> Dict[str, Any]:
        results = {}
        optimizers = ['cleanup', 'network', 'disk', 'performance', 'security', 'overclock']
        for name in optimizers:
            try:
                mod = __import__(f"core.optimizers.{name}", fromlist=[f"{name.title()}Optimizer"])
                cls = getattr(mod, f"{name.title()}Optimizer")
                results[name] = cls().execute()
            except Exception as e:
                results[name] = {"success": 0, "error": str(e)}
        return {"success": True, "results": results}

    @staticmethod
    def run_backup() -> Dict[str, Any]:
        from core.rollback_engine import RollbackEngine
        re = RollbackEngine(CONFIG.os_type)
        re.snapshot_power_plan()
        fp = re.save_snapshot()
        return {"success": True, "file": fp}

    @staticmethod
    def run_system_scan() -> Dict[str, Any]:
        try:
            from core.ai.health_analyzer import HealthAnalyzer
            ha = HealthAnalyzer()
            return ha.analyze()
        except Exception as e:
            return {"success": False, "error": f"Health analyzer not available: {e}"}

    @staticmethod
    def run_custom(command: str) -> Dict[str, Any]:
        if not command or not command.strip():
            return {"success": False, "error": "No command provided"}
        try:
            r = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=120
            )
            return {
                "success": r.returncode == 0,
                "stdout": r.stdout[:2000],
                "stderr": r.stderr[:2000],
                "returncode": r.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timed out after 120s"}
        except Exception as e:
            return {"success": False, "error": str(e)}


class AutomationCenter:
    def __init__(self):
        self.scheduler = AutomationScheduler()
        self.actions = TaskActions()

    def get_presets(self) -> Dict[str, List[Dict[str, Any]]]:
        return {
            "weekly_maintenance": [
                {"name": "Cleanup", "action": "cleanup", "interval_hours": 168},
                {"name": "Health Scan", "action": "scan", "interval_hours": 168},
                {"name": "Backup", "action": "backup", "interval_hours": 168},
            ],
            "daily_quick": [
                {"name": "Quick Cleanup", "action": "cleanup", "interval_hours": 24},
            ],
            "gaming_mode": [
                {"name": "Game Ready", "action": "optimize", "interval_hours": 0, "config": {"type": "gaming"}},
            ],
        }

    def apply_preset(self, preset_name: str) -> bool:
        presets = self.get_presets()
        if preset_name not in presets:
            return False
        for item in presets[preset_name]:
            task = ScheduledTask(
                id=str(uuid.uuid4()),
                name=item["name"],
                action=item["action"],
                interval_hours=item["interval_hours"],
                config=item.get("config", {}),
            )
            self.scheduler.add_task(task)
        self.scheduler._save_tasks()
        return True
