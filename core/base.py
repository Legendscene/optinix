from abc import ABC, abstractmethod
from typing import Callable, Dict, Any, List, Optional
from .logger import get_logger
from .errors import OptimizerError, AdminRequiredError, CompatibilityError
from .config import CONFIG
import time
import uuid
from datetime import datetime


OPTIMIZER_CATEGORY_SAFE = "safe"
OPTIMIZER_CATEGORY_ADVANCED = "advanced"
OPTIMIZER_CATEGORY_EXPERIMENTAL = "experimental"


class OptimizerResult:
    def __init__(self, success: bool, message: str, details: Optional[Dict[str, Any]] = None):
        self.success = success
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {"success": self.success, "message": self.message, "timestamp": self.timestamp, **self.details}


class OptimizerBase(ABC):
    name: str = ""
    description: str = ""
    category: str = OPTIMIZER_CATEGORY_SAFE
    benefit: str = ""
    risks: str = ""
    admin_required: bool = False
    requires_reboot: bool = False
    requirements: Dict[str, Any] = {}
    rollback_supported: bool = True

    def __init__(self):
        self.logger = get_logger(f"optimizer.{self.name or self.__class__.__name__}")
        self.results: List[OptimizerResult] = []
        self._compatibility_check: Optional[Dict[str, str]] = None
        self._benchmark_before: Optional[Dict[str, Any]] = None
        self._benchmark_after: Optional[Dict[str, Any]] = None
        self._history_entry_id: Optional[str] = None

    def check_admin(self):
        if not self.admin_required:
            return
        import ctypes
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
            if not is_admin:
                raise AdminRequiredError(f"{self.name} requires Administrator privileges")
        except AdminRequiredError:
            raise
        except:
            raise AdminRequiredError("Cannot verify admin privileges")

    def check_compatibility(self, detector=None):
        if not self.requirements:
            return True
        if detector is None:
            from .hardware_detection import HardwareDetector
            detector = HardwareDetector()
        compat = detector.check_compatibility(self.requirements)
        failures = {k: v for k, v in compat.items() if v.startswith("fail:")}
        self._compatibility_check = compat
        if failures:
            msg = "; ".join(failures.values())
            raise CompatibilityError(f"{self.name}: {msg}")
        return True

    def create_snapshot(self, rollback_engine=None):
        if not self.rollback_supported:
            return
        if rollback_engine is None:
            from .rollback_engine import RollbackEngine
            rollback_engine = RollbackEngine(CONFIG.os_type)
        rollback_engine.snapshot_power_plan()
        rollback_engine.snapshot.registry.update(self._registry_keys())
        rollback_engine.save_snapshot()
        return rollback_engine

    def _registry_keys(self) -> Dict[str, Any]:
        return {}

    def add_result(self, success: bool, message: str, **details):
        self.results.append(OptimizerResult(success, message, details))

    @abstractmethod
    def run(self) -> List[Dict[str, Any]]:
        ...

    def execute(self, progress_callback: Optional[Callable[[int, int, str], None]] = None) -> Dict[str, Any]:
        self.logger.info(f"Starting {self.name}")
        start_time = time.time()
        rollback_id = None
        error = None

        try:
            self.check_admin()

            self.check_compatibility()

            self._report_progress(progress_callback, 0, 100, "Benchmarking before...")
            self._benchmark_before = self._run_benchmark()

            self.results = []
            self._report_progress(progress_callback, 30, 100, "Running optimization...")
            raw_results = self.run()

            if not self.results:
                for r in raw_results:
                    self.results.append(OptimizerResult(
                        success=r.get("success", False),
                        message=r.get("message", ""),
                    ))

            success_count = sum(1 for r in raw_results if r.get("success"))

            self._report_progress(progress_callback, 70, 100, "Creating rollback snapshot...")
            rollback_engine = self._create_snapshot()
            if rollback_engine:
                rollback_id = rollback_engine.session_id if hasattr(rollback_engine, 'session_id') else None

            self._report_progress(progress_callback, 85, 100, "Benchmarking after...")
            self._benchmark_after = self._run_benchmark()

            duration_ms = int((time.time() - start_time) * 1000)

            self.logger.info(f"{self.name} completed: {success_count}/{len(raw_results)} OK in {duration_ms}ms")

        except (OptimizerError, AdminRequiredError, CompatibilityError) as e:
            error = str(e)
            self.logger.error(f"{self.name} failed: {e}")
            duration_ms = int((time.time() - start_time) * 1000)

        except Exception as e:
            error = f"Unexpected: {e}"
            self.logger.error(f"{self.name} unexpected error: {e}", exc_info=True)
            duration_ms = int((time.time() - start_time) * 1000)

        finally:
            self._report_progress(progress_callback, 95, 100, "Saving to history...")
            self._save_to_history(duration_ms, rollback_id, error)
            self._report_progress(progress_callback, 100, 100, "Complete")

        return self._build_result(duration_ms, rollback_id, error)

    def _run_benchmark(self) -> Optional[Dict[str, Any]]:
        try:
            from .benchmark_engine import BenchmarkEngine
            engine = BenchmarkEngine()
            results = engine.benchmark_all()
            return {k: v.value if hasattr(v, 'value') else v for k, v in results.items()}
        except Exception as e:
            self.logger.debug(f"Benchmark unavailable: {e}")
            return None

    def _create_snapshot(self) -> Optional[Any]:
        if not self.rollback_supported:
            return None
        from .rollback_engine import RollbackEngine
        from .config import CONFIG
        engine = RollbackEngine(CONFIG.os_type)
        try:
            engine.create_restore_point(f"Optinix: {self.name}")
            engine.snapshot_power_plan()
            reg_keys = self._registry_keys()
            if reg_keys:
                engine.snapshot.registry.update(reg_keys)
            engine.save_snapshot()
            return engine
        except Exception as e:
            self.logger.error(f"Snapshot creation failed: {e}")
            return None

    def _save_to_history(self, duration_ms: int, rollback_id: Optional[str] = None, error: Optional[str] = None):
        try:
            from .optimization_history import OptimizationHistory, HistoryEntry
            entry = HistoryEntry(
                entry_id=f"opt_{uuid.uuid4().hex[:12]}",
                optimizer_name=self.name,
                category=self.category,
                timestamp=datetime.now().isoformat(),
                duration_ms=duration_ms,
                success_count=sum(1 for r in self.results if r.success) if self.results else 0,
                total_count=len(self.results),
                rollback_id=rollback_id,
                reboot_required=self.requires_reboot,
                benchmark_before=self._benchmark_before,
                benchmark_after=self._benchmark_after,
                results=[r.to_dict() for r in self.results],
                error=error,
            )
            history = OptimizationHistory()
            self._history_entry_id = history.add_entry(entry)
        except Exception as e:
            self.logger.error(f"Failed to save history: {e}")

    def _build_result(self, duration_ms: int, rollback_id: Optional[str] = None, error: Optional[str] = None) -> Dict[str, Any]:
        result = {
            "category": self.category,
            "name": self.name,
            "description": self.description,
            "benefit": self.benefit,
            "risks": self.risks,
            "admin_required": self.admin_required,
            "requires_reboot": self.requires_reboot,
            "rollback_supported": self.rollback_supported,
            "results": [r.to_dict() for r in self.results],
            "success_count": sum(1 for r in self.results if r.success),
            "total_count": len(self.results),
            "duration_ms": duration_ms,
            "rollback_id": rollback_id,
            "history_entry_id": self._history_entry_id,
            "benchmark_before": self._benchmark_before,
            "benchmark_after": self._benchmark_after,
        }
        if self._benchmark_before and self._benchmark_after:
            result["benchmark_comparison"] = self._compare_benchmarks()
        if error:
            result["error"] = error
        return result

    def _compare_benchmarks(self) -> Dict[str, Any]:
        comparison = {}
        for key in self._benchmark_before or {}:
            b = self._benchmark_before.get(key)
            a = self._benchmark_after.get(key)
            if b is not None and a is not None and isinstance(b, (int, float)):
                delta = a - b
                pct = ((delta / b) * 100) if b != 0 else 0
                if abs(pct) < 1:
                    verdict = "unchanged"
                elif pct > 0:
                    verdict = "improved"
                else:
                    verdict = "declined"
                comparison[key] = {
                    "before": round(b, 2),
                    "after": round(a, 2),
                    "delta": round(delta, 2),
                    "percent_change": round(pct, 1),
                    "verdict": verdict,
                }
        return comparison

    @staticmethod
    def _report_progress(callback: Optional[Callable[[int, int, str], None]], current: int, total: int, message: str):
        if callback:
            try:
                callback(current, total, message)
            except Exception:
                pass

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "benefit": self.benefit,
            "risks": self.risks,
            "admin_required": self.admin_required,
            "requires_reboot": self.requires_reboot,
            "rollback_supported": self.rollback_supported,
        }
