import os
import json
import time
import threading
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from ..config import CONFIG
from ..logger import get_logger

_logger = get_logger("metrics_store")


def _get_data_dir() -> str:
    if hasattr(CONFIG, "data_dir") and CONFIG.data_dir:
        return CONFIG.data_dir
    return os.path.join(CONFIG.base_dir, "data")


DATA_DIR = _get_data_dir()
METRICS_DIR = os.path.join(DATA_DIR, "metrics")


class MetricsStore:
    GRANULARITIES = {
        "1h":  {"maxlen": 720,  "interval": 5},
        "24h": {"maxlen": 1440, "interval": 60},
        "7d":  {"maxlen": 2016, "interval": 300},
    }

    METRICS = [
        "cpu", "gpu", "ram", "vram",
        "disk_read", "disk_write",
        "network_download", "network_upload",
        "battery", "temperature", "fan_speed", "fps",
    ]

    def __init__(self):
        self._lock = threading.Lock()
        self._data: Dict[str, Dict[str, deque]] = {
            m: {p: deque(maxlen=info["maxlen"]) for p, info in self.GRANULARITIES.items()}
            for m in self.METRICS
        }
        self._last_push: Dict[str, Dict[str, float]] = {
            m: {p: 0.0 for p in self.GRANULARITIES}
            for m in self.METRICS
        }
        self._latest: Dict[str, Optional[float]] = {m: None for m in self.METRICS}
        self._latest_ts: Dict[str, float] = {m: 0.0 for m in self.METRICS}

        os.makedirs(METRICS_DIR, exist_ok=True)
        self.load()
        self._start_auto_flush()

    def _start_auto_flush(self):
        def _flush_loop():
            while True:
                time.sleep(60)
                try:
                    self.flush()
                except Exception:
                    pass

        t = threading.Thread(target=_flush_loop, daemon=True)
        t.start()

    def push(self, category: str, value: float):
        now = time.time()
        with self._lock:
            if category not in self._data:
                return
            self._latest[category] = value
            self._latest_ts[category] = now
            for period, info in self.GRANULARITIES.items():
                interval = info["interval"]
                if now - self._last_push[category][period] >= interval:
                    self._data[category][period].append({"timestamp": now, "value": value})
                    self._last_push[category][period] = now

    def get_history(self, category: str, period: str = "1h") -> List[Dict]:
        if category not in self._data or period not in self.GRANULARITIES:
            return []
        with self._lock:
            return list(self._data[category][period])

    def get_all_current(self) -> Dict[str, Optional[float]]:
        with self._lock:
            return dict(self._latest)

    def get_current(self, category: str) -> Optional[float]:
        with self._lock:
            return self._latest.get(category)

    def get_stats(self, category: str, period: str = "1h") -> Dict:
        entries = self.get_history(category, period)
        if not entries:
            return {
                "min": None,
                "max": None,
                "avg": None,
                "current": self.get_current(category),
                "count": 0,
                "period": period,
            }
        values = [e["value"] for e in entries]
        return {
            "min": round(min(values), 2),
            "max": round(max(values), 2),
            "avg": round(sum(values) / len(values), 2),
            "current": self.get_current(category),
            "count": len(values),
            "period": period,
        }

    def flush(self):
        try:
            os.makedirs(METRICS_DIR, exist_ok=True)
            path = os.path.join(METRICS_DIR, f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            with self._lock:
                payload = {
                    "timestamp": time.time(),
                    "latest": dict(self._latest),
                    "latest_ts": dict(self._latest_ts),
                    "last_push": {cat: dict(pmap) for cat, pmap in self._last_push.items()},
                    "data": {
                        cat: {p: list(self._data[cat][p]) for p in self.GRANULARITIES}
                        for cat in self.METRICS
                    },
                }
            with open(path, "w") as f:
                json.dump(payload, f, indent=2)
            _logger.info(f"Metrics flushed to {path}")
            self._cleanup_old_files()
        except Exception as e:
            _logger.error(f"Failed to flush metrics: {e}")

    def load(self):
        try:
            if not os.path.isdir(METRICS_DIR):
                return
            files = sorted(
                [f for f in os.listdir(METRICS_DIR) if f.startswith("metrics_") and f.endswith(".json")],
                reverse=True,
            )
            if not files:
                return
            path = os.path.join(METRICS_DIR, files[0])
            with open(path, "r") as f:
                payload = json.load(f)
            with self._lock:
                for cat in self.METRICS:
                    if cat in payload.get("data", {}):
                        for period in self.GRANULARITIES:
                            if period in payload["data"][cat]:
                                entries = payload["data"][cat][period]
                                self._data[cat][period].clear()
                                self._data[cat][period].extend(entries)
                    if cat in payload.get("latest", {}):
                        self._latest[cat] = payload["latest"][cat]
                    if cat in payload.get("latest_ts", {}):
                        self._latest_ts[cat] = payload["latest_ts"][cat]
                    if cat in payload.get("last_push", {}):
                        for period in self.GRANULARITIES:
                            if period in payload["last_push"][cat]:
                                self._last_push[cat][period] = payload["last_push"][cat][period]
            _logger.info(f"Loaded metrics from {path}")
        except Exception as e:
            _logger.error(f"Failed to load metrics: {e}")

    def _cleanup_old_files(self, keep: int = 5):
        try:
            files = sorted(
                [f for f in os.listdir(METRICS_DIR) if f.startswith("metrics_") and f.endswith(".json")],
            )
            while len(files) > keep:
                os.remove(os.path.join(METRICS_DIR, files[0]))
                files.pop(0)
        except Exception:
            pass


metrics_store = MetricsStore()
