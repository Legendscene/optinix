import os
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque

from ..config import CONFIG
from ..logger import get_logger


TIMELINE_DIR = os.path.join(CONFIG.base_dir, "data", "timeline")
METRICS_FILE = os.path.join(TIMELINE_DIR, "metrics.json")
EVENTS_FILE = os.path.join(TIMELINE_DIR, "events.json")
HEALTH_SCORES_FILE = os.path.join(TIMELINE_DIR, "health_scores.json")

METRIC_RETENTION_DAYS = 30
EVENT_RETENTION_DAYS = 30
HEALTH_RETENTION_DAYS = 30
SNAPSHOT_INTERVAL = 300
HEALTH_INTERVAL = 900
AUTO_FLUSH_INTERVAL = 60
MAX_METRICS = 8640
MAX_EVENTS = 1000
MAX_HEALTH_SCORES = 2880


class TimelineStore:
    def __init__(self):
        self.logger = get_logger("timeline")
        self._metrics: deque = deque(maxlen=MAX_METRICS)
        self._events: deque = deque(maxlen=MAX_EVENTS)
        self._health_scores: deque = deque(maxlen=MAX_HEALTH_SCORES)
        self._lock = threading.Lock()
        self._snapshot_thread: Optional[threading.Thread] = None
        self._flush_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        os.makedirs(TIMELINE_DIR, exist_ok=True)
        self.load()

    def start(self):
        if self._snapshot_thread and self._snapshot_thread.is_alive():
            return
        self._stop_event.clear()
        self._snapshot_thread = threading.Thread(
            target=self._snapshot_loop, daemon=True, name="timeline-snapshot"
        )
        self._snapshot_thread.start()
        self._flush_thread = threading.Thread(
            target=self._auto_flush_loop, daemon=True, name="timeline-flush"
        )
        self._flush_thread.start()
        self.logger.info("TimelineStore started")

    def stop(self):
        self._stop_event.set()
        if self._snapshot_thread and self._snapshot_thread.is_alive():
            self._snapshot_thread.join(timeout=5)
        if self._flush_thread and self._flush_thread.is_alive():
            self._flush_thread.join(timeout=5)
        self.flush()
        self.logger.info("TimelineStore stopped")

    def record_snapshot(self, metrics: Dict[str, Any]):
        snapshot = {
            "timestamp": time.time(),
            "cpu_percent": metrics.get("cpu_percent", 0.0),
            "ram_percent": metrics.get("ram_percent", 0.0),
            "ram_gb": metrics.get("ram_gb", 0.0),
            "disk_usage_max": metrics.get("disk_usage_max", 0.0),
            "gpu_percent": metrics.get("gpu_percent", 0.0),
            "gpu_memory_percent": metrics.get("gpu_memory_percent", 0.0),
            "battery_percent": metrics.get("battery_percent", 0.0),
            "network_mbps": metrics.get("network_mbps", 0.0),
            "temperature": metrics.get("temperature", 0.0),
            "processes": metrics.get("processes", 0),
            "boot_time": metrics.get("boot_time", 0.0),
            "health_score": metrics.get("health_score", 0),
        }
        with self._lock:
            self._metrics.append(snapshot)

    def record_event(
        self,
        event_type: str,
        name: str,
        details: str,
        benchmark_before: Optional[Dict] = None,
        benchmark_after: Optional[Dict] = None,
        score_before: Optional[int] = None,
        score_after: Optional[int] = None,
    ):
        event = {
            "timestamp": time.time(),
            "type": event_type,
            "name": name,
            "details": details,
            "benchmark_before": benchmark_before,
            "benchmark_after": benchmark_after,
            "score_before": score_before,
            "score_after": score_after,
        }
        with self._lock:
            self._events.append(event)

    def record_health_scores(self, scores: Dict[str, Any]):
        entry = {
            "timestamp": time.time(),
            "pc_health": scores.get("pc_health", 0),
            "windows_health": scores.get("windows_health", 0),
            "gaming": scores.get("gaming", 0),
            "developer": scores.get("developer", 0),
            "security": scores.get("security", 0),
            "storage": scores.get("storage", 0),
            "battery": scores.get("battery", 0),
        }
        with self._lock:
            self._health_scores.append(entry)

    def get_metric_history(self, metric: str, hours: int = 24) -> List[Dict]:
        cutoff = time.time() - (hours * 3600)
        result = []
        with self._lock:
            for snap in self._metrics:
                if snap["timestamp"] >= cutoff and metric in snap:
                    result.append({
                        "timestamp": snap["timestamp"],
                        "value": snap[metric],
                    })
        result.sort(key=lambda x: x["timestamp"])
        return result

    def get_events(
        self, limit: int = 50, event_type: Optional[str] = None
    ) -> List[Dict]:
        result = []
        with self._lock:
            for ev in self._events:
                if event_type and ev["type"] != event_type:
                    continue
                result.append(dict(ev))
        result.sort(key=lambda x: x["timestamp"], reverse=True)
        return result[:limit]

    def get_health_score_history(self, days: int = 7) -> List[Dict]:
        cutoff = time.time() - (days * 86400)
        result = []
        with self._lock:
            for entry in self._health_scores:
                if entry["timestamp"] >= cutoff:
                    result.append(dict(entry))
        result.sort(key=lambda x: x["timestamp"])
        return result

    def get_timeline_summary(self) -> Dict:
        with self._lock:
            total_metrics = len(self._metrics)
            total_events = len(self._events)
            total_health = len(self._health_scores)
            latest_metrics = list(self._metrics)[-1] if self._metrics else {}
            all_types = defaultdict(int)
            for ev in self._events:
                all_types[ev["type"]] += 1

        avg_cpu = 0.0
        avg_ram = 0.0
        if total_metrics > 0:
            with self._lock:
                cpus = [m["cpu_percent"] for m in self._metrics if "cpu_percent" in m]
                rams = [m["ram_percent"] for m in self._metrics if "ram_percent" in m]
            avg_cpu = sum(cpus) / len(cpus) if cpus else 0.0
            avg_ram = sum(rams) / len(rams) if rams else 0.0

        return {
            "total_metrics": total_metrics,
            "total_events": total_events,
            "total_health_scores": total_health,
            "events_by_type": dict(all_types),
            "average_cpu_percent": round(avg_cpu, 1),
            "average_ram_percent": round(avg_ram, 1),
            "latest_metrics": latest_metrics,
            "retention_days": METRIC_RETENTION_DAYS,
        }

    def get_optimization_impact(self) -> List[Dict]:
        result = []
        with self._lock:
            for ev in self._events:
                if ev["benchmark_before"] or ev["benchmark_after"]:
                    result.append(dict(ev))
        result.sort(key=lambda x: x["timestamp"], reverse=True)
        return result

    def get_boot_time_history(self, days: int = 7) -> List[Dict]:
        cutoff = time.time() - (days * 86400)
        result = []
        with self._lock:
            for snap in self._metrics:
                ts = snap.get("timestamp", 0)
                bt = snap.get("boot_time", 0)
                if ts >= cutoff and bt > 0:
                    result.append({"timestamp": ts, "boot_time": bt})
        result.sort(key=lambda x: x["timestamp"])
        return result

    def flush(self):
        self._prune()
        try:
            with self._lock:
                metrics_data = list(self._metrics)
                events_data = list(self._events)
                health_data = list(self._health_scores)
            os.makedirs(TIMELINE_DIR, exist_ok=True)
            with open(METRICS_FILE, "w", encoding="utf-8") as f:
                json.dump(metrics_data, f, default=str)
            with open(EVENTS_FILE, "w", encoding="utf-8") as f:
                json.dump(events_data, f, default=str)
            with open(HEALTH_SCORES_FILE, "w", encoding="utf-8") as f:
                json.dump(health_data, f, default=str)
            self.logger.debug(
                f"Flushed {len(metrics_data)} metrics, {len(events_data)} events, "
                f"{len(health_data)} health scores"
            )
        except (OSError, json.JSONEncodeError) as e:
            self.logger.error(f"Failed to flush timeline data: {e}")

    def load(self):
        try:
            if os.path.isfile(METRICS_FILE):
                with open(METRICS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                with self._lock:
                    self._metrics.extend(data[-MAX_METRICS:])
                self.logger.debug(f"Loaded {len(data)} metrics")
            if os.path.isfile(EVENTS_FILE):
                with open(EVENTS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                with self._lock:
                    self._events.extend(data[-MAX_EVENTS:])
                self.logger.debug(f"Loaded {len(data)} events")
            if os.path.isfile(HEALTH_SCORES_FILE):
                with open(HEALTH_SCORES_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                with self._lock:
                    self._health_scores.extend(data[-MAX_HEALTH_SCORES:])
                self.logger.debug(f"Loaded {len(data)} health scores")
        except (OSError, json.JSONDecodeError) as e:
            self.logger.error(f"Failed to load timeline data: {e}")

    def _prune(self):
        now = time.time()
        metric_cutoff = now - (METRIC_RETENTION_DAYS * 86400)
        event_cutoff = now - (EVENT_RETENTION_DAYS * 86400)
        health_cutoff = now - (HEALTH_RETENTION_DAYS * 86400)

        with self._lock:
            while self._metrics and self._metrics[0]["timestamp"] < metric_cutoff:
                self._metrics.popleft()
            while self._events and self._events[0]["timestamp"] < event_cutoff:
                self._events.popleft()
            while self._health_scores and self._health_scores[0]["timestamp"] < health_cutoff:
                self._health_scores.popleft()

    def _snapshot_loop(self):
        snapshot_counter = 0
        health_counter = 0
        while not self._stop_event.is_set():
            self._stop_event.wait(SNAPSHOT_INTERVAL)
            if self._stop_event.is_set():
                break
            snapshot_counter += 1
            health_counter += 1
            if snapshot_counter * SNAPSHOT_INTERVAL >= SNAPSHOT_INTERVAL:
                self.logger.debug("Snapshot interval elapsed (waiting for external data)")
                snapshot_counter = 0
            if health_counter * HEALTH_INTERVAL >= HEALTH_INTERVAL:
                self.logger.debug("Health score interval elapsed (waiting for external data)")
                health_counter = 0

    def _auto_flush_loop(self):
        while not self._stop_event.is_set():
            self._stop_event.wait(AUTO_FLUSH_INTERVAL)
            if not self._stop_event.is_set():
                self.flush()


timeline_store = TimelineStore()
