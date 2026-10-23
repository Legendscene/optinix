import os
import json
import time
import threading
import subprocess
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from collections import deque
from ..config import CONFIG
from ..logger import get_logger

logger = get_logger("notifications")


class Notification:
    def __init__(self, notif_id: str, type: str, title: str, message: str,
                 severity: str = "info", timestamp: float = None,
                 read: bool = False, action: str = None, dismissed: bool = False):
        self.id = notif_id
        self.type = type
        self.title = title
        self.message = message
        self.severity = severity
        self.timestamp = timestamp or time.time()
        self.read = read
        self.action = action
        self.dismissed = dismissed

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "message": self.message,
            "severity": self.severity,
            "timestamp": self.timestamp,
            "read": self.read,
            "action": self.action,
            "dismissed": self.dismissed,
        }


class NotificationManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True
        self._notifications: deque = deque(maxlen=200)
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._checkers: List[Callable] = []
        self._throttle: Dict[str, float] = {}
        self._seen_issues: Dict[str, float] = {}
        self._seen_ttl: Dict[str, int] = {
            "ssd_full": 3600,
            "battery_health": 3600,
            "driver_outdated": 86400,
            "windows_update": 21600,
            "startup_time": 3600,
            "high_cpu": 300,
            "high_ram": 300,
            "high_temp": 300,
        }
        self._high_cpu_streak = 0
        self._prev_boot_time: Optional[float] = None
        self._notif_path = os.path.join(CONFIG.base_dir, "data", "notifications.json")
        os.makedirs(os.path.dirname(self._notif_path), exist_ok=True)
        self._register_checkers()
        self._load()

    def _register_checkers(self):
        self._checkers = [
            ("ssd_full", self._check_ssd_full, 60),
            ("battery_health", self._check_battery_health, 300),
            ("driver_outdated", self._check_driver_outdated, 86400),
            ("windows_update", self._check_windows_update, 21600),
            ("startup_time", self._check_startup_time, 3600),
            ("high_cpu", self._check_high_cpu, 60),
            ("high_ram", self._check_high_ram, 60),
            ("high_temp", self._check_high_temp, 60),
        ]

    def start(self):
        with self._lock:
            if self._running:
                return
            self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Notification monitoring started")

    def stop(self):
        with self._lock:
            self._running = False
        logger.info("Notification monitoring stopped")

    def add_notification(self, type: str, title: str, message: str,
                         severity: str = "info", action: str = None) -> Notification:
        notif_id = f"{type}_{int(time.time() * 1000)}_{hash(message) % 10000}"
        notif = Notification(
            notif_id=notif_id,
            type=type,
            title=title,
            message=message,
            severity=severity,
            action=action,
        )
        with self._lock:
            self._notifications.appendleft(notif)
            self._seen_issues[type] = time.time()
            self._save()
        logger.info(f"Notification: [{severity}] {title}")
        return notif

    def get_all(self, include_dismissed: bool = False, limit: int = 50) -> List[Dict]:
        with self._lock:
            result = []
            for n in self._notifications:
                if not include_dismissed and n.dismissed:
                    continue
                result.append(n.to_dict())
                if len(result) >= limit:
                    break
            return result

    def get_unread_count(self) -> int:
        with self._lock:
            return sum(1 for n in self._notifications if not n.read and not n.dismissed)

    def mark_read(self, notif_id: str):
        with self._lock:
            for n in self._notifications:
                if n.id == notif_id:
                    n.read = True
                    self._save()
                    break

    def mark_all_read(self):
        with self._lock:
            for n in self._notifications:
                n.read = True
            self._save()

    def dismiss(self, notif_id: str):
        with self._lock:
            for n in self._notifications:
                if n.id == notif_id:
                    n.dismissed = True
                    self._save()
                    break

    def dismiss_all(self):
        with self._lock:
            for n in self._notifications:
                n.dismissed = True
            self._save()

    def get_by_type(self, type: str) -> List[Dict]:
        with self._lock:
            return [n.to_dict() for n in self._notifications if n.type == type and not n.dismissed]

    def get_recent(self, seconds: int = 3600) -> List[Dict]:
        cutoff = time.time() - seconds
        with self._lock:
            return [n.to_dict() for n in self._notifications if n.timestamp >= cutoff and not n.dismissed]

    def _save(self):
        try:
            data = [n.to_dict() for n in self._notifications]
            tmp = self._notif_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, self._notif_path)
        except Exception as e:
            logger.error(f"Failed to save notifications: {e}")

    def _load(self):
        try:
            if os.path.isfile(self._notif_path):
                with open(self._notif_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for item in data:
                    notif = Notification(
                        notif_id=item["id"],
                        type=item["type"],
                        title=item["title"],
                        message=item["message"],
                        severity=item.get("severity", "info"),
                        timestamp=item.get("timestamp", time.time()),
                        read=item.get("read", False),
                        action=item.get("action"),
                        dismissed=item.get("dismissed", False),
                    )
                    self._notifications.append(notif)
                logger.info(f"Loaded {len(data)} notifications from disk")
        except Exception as e:
            logger.error(f"Failed to load notifications: {e}")

    def _is_throttled(self, name: str, interval: int) -> bool:
        now = time.time()
        last = self._throttle.get(name, 0)
        if now - last < interval:
            return True
        self._throttle[name] = now
        return False

    def _is_seen(self, issue_type: str, ttl: int = 3600) -> bool:
        now = time.time()
        last = self._seen_issues.get(issue_type, 0)
        if now - last < ttl:
            return True
        return False

    def _run_loop(self):
        while True:
            with self._lock:
                if not self._running:
                    break
            try:
                self._check_conditions()
            except Exception as e:
                logger.error(f"Notification check error: {e}")
            time.sleep(60)

    def _check_conditions(self):
        for name, checker, interval in self._checkers:
            try:
                if not self._is_throttled(name, interval):
                    checker()
            except Exception as e:
                logger.error(f"Checker '{name}' failed: {e}")

    def _check_ssd_full(self):
        for part in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(part.mountpoint)
                free_pct = usage.free / usage.total * 100
                if free_pct < 10 and not self._is_seen("ssd_full_" + part.device, 3600):
                    self._seen_issues["ssd_full_" + part.device] = time.time()
                    self.add_notification(
                        type="ssd_full",
                        title="Drive Running Out of Space",
                        message=f"{part.device} ({part.mountpoint}) has only {free_pct:.1f}% free space remaining.",
                        severity="critical" if free_pct < 5 else "warning",
                        action="cleanup",
                    )
            except Exception:
                pass

    def _check_battery_health(self):
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "Get-WmiObject -Namespace root/wmi -Class BatteryFullChargedCapacity | "
                 "Select-Object DesignedCapacity, FullChargedCapacity | ConvertTo-Json"],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode != 0 or not result.stdout.strip():
                return
            data = json.loads(result.stdout.strip())
            if isinstance(data, list):
                data = data[0] if data else None
            if not data:
                return
            designed = int(data.get("DesignedCapacity", 0))
            full = int(data.get("FullChargedCapacity", 0))
            if designed <= 0:
                return
            health = full / designed * 100
            if health < 60 and not self._is_seen("battery_health_critical", 3600):
                self._seen_issues["battery_health_critical"] = time.time()
                self.add_notification(
                    type="battery_health",
                    title="Battery Health Critical",
                    message=f"Battery health is at {health:.1f}%. Consider replacing the battery.",
                    severity="critical",
                )
            elif health < 80 and not self._is_seen("battery_health_warning", 3600):
                self._seen_issues["battery_health_warning"] = time.time()
                self.add_notification(
                    type="battery_health",
                    title="Battery Health Low",
                    message=f"Battery health is at {health:.1f}%. It may need replacement soon.",
                    severity="warning",
                )
        except Exception as e:
            logger.debug(f"Battery health check failed: {e}")

    def _check_driver_outdated(self):
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "Get-WmiObject -Class Win32_PnPSignedDriver | Where-Object {$_.IsSigned -eq $false} | "
                 "Select-Object DeviceName, DriverVersion | ConvertTo-Json"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0 or not result.stdout.strip():
                return
            data = json.loads(result.stdout.strip())
            drivers = data if isinstance(data, list) else [data]
            unsigned = [d for d in drivers if d and d.get("DeviceName")]
            if unsigned and not self._is_seen("driver_outdated", 86400):
                self._seen_issues["driver_outdated"] = time.time()
                names = ", ".join(d["DeviceName"] for d in unsigned[:5])
                count = len(unsigned)
                msg = f"{count} unsigned driver(s) found: {names}"
                if count > 5:
                    msg += f" and {count - 5} more"
                self.add_notification(
                    type="driver_outdated",
                    title="Unsigned Drivers Detected",
                    message=msg,
                    severity="warning",
                )
        except Exception as e:
            logger.debug(f"Driver check failed: {e}")

    def _check_windows_update(self):
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "Get-ItemProperty -Path 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\WindowsUpdate\\Auto Update\\RebootRequired' -Name 'RebootRequired' -ErrorAction SilentlyContinue; "
                 "$wu = New-Object -ComObject 'Microsoft.Update.Session'; $searcher = $wu.CreateUpdateSearcher(); "
                 "$count = $searcher.GetTotalHistoryCount(); if ($count -gt 0) { $searcher.QueryHistory(0, $count) | "
                 "Where-Object { $_.ResultCode -eq 2 -and $_.Date -gt (Get-Date).AddDays(-7) } | Measure-Object | "
                 "Select-Object -ExpandProperty Count } else { 0 }"],
                capture_output=True, text=True, timeout=30,
            )
            output = result.stdout.strip()
            if "RebootRequired" in result.stdout:
                if not self._is_seen("windows_update_reboot", 21600):
                    self._seen_issues["windows_update_reboot"] = time.time()
                    self.add_notification(
                        type="windows_update",
                        title="Restart Required for Updates",
                        message="A restart is pending to finish installing Windows updates.",
                        severity="warning",
                        action="restart",
                    )
        except Exception as e:
            logger.debug(f"Windows update check failed: {e}")

    def _check_startup_time(self):
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "Get-WinEvent -FilterHashtable @{LogName='System'; ID=12} -MaxEvents 1 | "
                 "Select-Object -ExpandProperty TimeCreated | ConvertTo-Json"],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode != 0 or not result.stdout.strip():
                return
            boot_str = json.loads(result.stdout.strip())
            if isinstance(boot_str, list):
                boot_str = boot_str[0] if boot_str else None
            if not boot_str:
                return
            boot_time = datetime.fromisoformat(boot_str.replace("Z", "+00:00")).timestamp()
            if self._prev_boot_time is not None:
                diff = abs(boot_time - self._prev_boot_time)
                if diff > 30 and diff > abs(self._prev_boot_time * 0.3) and not self._is_seen("startup_time", 3600):
                    self._seen_issues["startup_time"] = time.time()
                    self.add_notification(
                        type="startup_time",
                        title="Startup Time Increased",
                        message=f"Boot time is {diff:.0f}s slower than the previous startup.",
                        severity="warning",
                        action="startup_manager",
                    )
            self._prev_boot_time = boot_time
        except Exception as e:
            logger.debug(f"Startup time check failed: {e}")

    def _check_high_cpu(self):
        try:
            cpu_pct = psutil.cpu_percent(interval=1)
            if cpu_pct > 90:
                self._high_cpu_streak += 1
            else:
                self._high_cpu_streak = 0
            if self._high_cpu_streak >= 3 and not self._is_seen("high_cpu", 300):
                self._seen_issues["high_cpu"] = time.time()
                self._high_cpu_streak = 0
                self.add_notification(
                    type="high_cpu",
                    title="High CPU Usage",
                    message=f"CPU usage has been above 90% for {self._high_cpu_streak} consecutive checks.",
                    severity="warning",
                    action="task_manager",
                )
        except Exception as e:
            logger.debug(f"CPU check failed: {e}")

    def _check_high_ram(self):
        try:
            mem = psutil.virtual_memory()
            if mem.percent > 90 and not self._is_seen("high_ram", 300):
                self._seen_issues["high_ram"] = time.time()
                self.add_notification(
                    type="high_ram",
                    title="High RAM Usage",
                    message=f"Memory usage is at {mem.percent:.1f}% ({mem.used // (1024**3)}GB / {mem.total // (1024**3)}GB).",
                    severity="warning",
                    action="memory_manager",
                )
        except Exception as e:
            logger.debug(f"RAM check failed: {e}")

    def _check_high_temp(self):
        try:
            temps = psutil.sensors_temperatures()
            if not temps:
                return
            for name, entries in temps.items():
                for entry in entries:
                    if entry.current and entry.current > 85:
                        if not self._is_seen("high_temp_" + name, 300):
                            self._seen_issues["high_temp_" + name] = time.time()
                            self.add_notification(
                                type="high_temp",
                                title=f"High Temperature: {name}",
                                message=f"{name} sensor reads {entry.current}°C. Critical threshold is 85°C.",
                                severity="critical",
                            )
        except Exception as e:
            logger.debug(f"Temperature check failed: {e}")


notification_manager = NotificationManager()
