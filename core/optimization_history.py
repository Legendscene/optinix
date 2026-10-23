import json
import os
import random
import string
from datetime import datetime
from typing import Any, Dict, List, Optional

from .config import CONFIG
from .logger import get_logger


class HistoryEntry:
    def __init__(self, entry_id: str, optimizer_name: str, category: str,
                 timestamp: str, duration_ms: int, success_count: int, total_count: int,
                 rollback_id: Optional[str] = None, reboot_required: bool = False,
                 benchmark_before: Optional[Dict[str, float]] = None,
                 benchmark_after: Optional[Dict[str, float]] = None,
                 results: Optional[List[Dict[str, Any]]] = None,
                 error: Optional[str] = None):
        self.entry_id = entry_id
        self.optimizer_name = optimizer_name
        self.category = category
        self.timestamp = timestamp
        self.duration_ms = duration_ms
        self.success_count = success_count
        self.total_count = total_count
        self.rollback_id = rollback_id
        self.reboot_required = reboot_required
        self.benchmark_before = benchmark_before or {}
        self.benchmark_after = benchmark_after or {}
        self.results = results or []
        self.error = error

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HistoryEntry":
        return cls(
            entry_id=data["entry_id"],
            optimizer_name=data["optimizer_name"],
            category=data["category"],
            timestamp=data["timestamp"],
            duration_ms=data["duration_ms"],
            success_count=data["success_count"],
            total_count=data["total_count"],
            rollback_id=data.get("rollback_id"),
            reboot_required=data.get("reboot_required", False),
            benchmark_before=data.get("benchmark_before"),
            benchmark_after=data.get("benchmark_after"),
            results=data.get("results"),
            error=data.get("error"),
        )

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "entry_id": self.entry_id,
            "optimizer_name": self.optimizer_name,
            "category": self.category,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "success_count": self.success_count,
            "total_count": self.total_count,
            "rollback_id": self.rollback_id,
            "reboot_required": self.reboot_required,
            "benchmark_before": self.benchmark_before,
            "benchmark_after": self.benchmark_after,
            "results": self.results,
            "error": self.error,
        }
        return {k: v for k, v in d.items() if v is not None}


def _generate_entry_id() -> str:
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"opt_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{suffix}"


class OptimizationHistory:
    def __init__(self):
        self.logger = get_logger("history")
        self._history_dir = os.path.join(CONFIG.base_dir, "data", "history")
        try:
            os.makedirs(self._history_dir, exist_ok=True)
            self.logger.debug(f"History directory: {self._history_dir}")
        except OSError as e:
            self.logger.error(f"Failed to create history directory: {e}")
        self._index: Dict[str, str] = {}
        self._rebuild_index()

    def _rebuild_index(self) -> None:
        self._index.clear()
        try:
            if not os.path.isdir(self._history_dir):
                return
            for f in os.listdir(self._history_dir):
                if f.endswith(".json"):
                    entry_id = f[:-5]
                    self._index[entry_id] = os.path.join(self._history_dir, f)
        except OSError as e:
            self.logger.error(f"Failed to rebuild index: {e}")

    def _entry_path(self, entry_id: str) -> str:
        return os.path.join(self._history_dir, f"{entry_id}.json")

    def add_entry(self, entry: HistoryEntry) -> str:
        if not entry.entry_id:
            entry.entry_id = _generate_entry_id()
        path = self._entry_path(entry.entry_id)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(entry.to_dict(), f, indent=2)
            self._index[entry.entry_id] = path
            self.logger.info(f"Saved history entry: {entry.entry_id}")
        except OSError as e:
            self.logger.error(f"Failed to save entry {entry.entry_id}: {e}")
        return entry.entry_id

    def get_entry(self, entry_id: str) -> Optional[HistoryEntry]:
        path = self._index.get(entry_id)
        if not path or not os.path.isfile(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return HistoryEntry.from_dict(data)
        except (OSError, json.JSONDecodeError, KeyError) as e:
            self.logger.error(f"Failed to load entry {entry_id}: {e}")
            return None

    def get_all(self, limit: int = 50, offset: int = 0,
                category: Optional[str] = None) -> Dict[str, Any]:
        entries = []
        for entry_id in sorted(self._index.keys(), reverse=True):
            entry = self.get_entry(entry_id)
            if entry is None:
                continue
            if category and entry.category != category:
                continue
            entries.append(entry.to_dict())
        total = len(entries)
        sliced = entries[offset:offset + limit]
        return {
            "entries": sliced,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def _summarize_benchmark_comparison(self) -> tuple:
        improvements = []
        declines = []
        for entry_id in sorted(self._index.keys(), reverse=True)[:100]:
            entry = self.get_entry(entry_id)
            if entry is None or not entry.benchmark_before or not entry.benchmark_after:
                continue
            before = entry.benchmark_before
            after = entry.benchmark_after
            keys = set(before.keys()) & set(after.keys())
            if not keys:
                continue
            improved = any(after.get(k, 0) > before.get(k, 0) for k in keys)
            declined = any(after.get(k, 0) < before.get(k, 0) for k in keys)
            if improved and not declined:
                improvements.append(entry.to_dict())
            elif declined and not improved:
                declines.append(entry.to_dict())
        return improvements[:10], declines[:10]

    def get_summary(self) -> Dict[str, Any]:
        total_opt = len(self._index)
        total_success = 0
        total_failures = 0
        total_duration = 0
        by_category: Dict[str, Dict[str, int]] = {}
        for entry_id in self._index:
            entry = self.get_entry(entry_id)
            if entry is None:
                continue
            total_success += entry.success_count
            if entry.error:
                total_failures += 1
            total_duration += entry.duration_ms
            if entry.category not in by_category:
                by_category[entry.category] = {"total": 0, "success": 0}
            by_category[entry.category]["total"] += entry.total_count
            by_category[entry.category]["success"] += entry.success_count
        improvements, declines = self._summarize_benchmark_comparison()
        avg_duration = total_duration / total_opt if total_opt > 0 else 0.0
        return {
            "total_optimizations": total_opt,
            "total_success": total_success,
            "total_failures": total_failures,
            "by_category": by_category,
            "recent_improvements": improvements,
            "recent_declines": declines,
            "average_duration_ms": avg_duration,
        }

    def clear(self) -> bool:
        try:
            for entry_id in list(self._index.keys()):
                path = self._index[entry_id]
                try:
                    os.remove(path)
                except OSError as e:
                    self.logger.error(f"Failed to delete {entry_id}: {e}")
            self._index.clear()
            self.logger.info("Cleared all history entries")
            return True
        except Exception as e:
            self.logger.error(f"Failed to clear history: {e}")
            return False

    def latest_for_optimizer(self, name: str) -> Optional[HistoryEntry]:
        candidates = []
        for entry_id in self._index:
            entry = self.get_entry(entry_id)
            if entry and entry.optimizer_name == name:
                candidates.append(entry)
        if not candidates:
            return None
        candidates.sort(key=lambda e: e.timestamp, reverse=True)
        return candidates[0]

    def compare_optimizer(self, name: str, count: int = 2) -> Dict[str, Any]:
        candidates = []
        for entry_id in self._index:
            entry = self.get_entry(entry_id)
            if entry and entry.optimizer_name == name:
                candidates.append(entry)
        candidates.sort(key=lambda e: e.timestamp, reverse=True)
        selected = candidates[:count]
        if not selected:
            return {"optimizer_name": name, "entries": [], "trend": "unknown"}
        trend = "stable"
        if len(selected) >= 2:
            prev = selected[-1]
            curr = selected[0]
            if prev.benchmark_before and curr.benchmark_after:
                keys = set(prev.benchmark_before.keys()) & set(curr.benchmark_after.keys())
                if keys:
                    improved = sum(1 for k in keys if curr.benchmark_after.get(k, 0) > prev.benchmark_before.get(k, 0))
                    declined = sum(1 for k in keys if curr.benchmark_after.get(k, 0) < prev.benchmark_before.get(k, 0))
                    if improved > declined:
                        trend = "improving"
                    elif declined > improved:
                        trend = "declining"
        return {
            "optimizer_name": name,
            "entries": [e.to_dict() for e in selected],
            "trend": trend,
        }
