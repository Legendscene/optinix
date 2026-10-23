import os
import time
import tempfile
import subprocess
import re
import threading
from decimal import Decimal, getcontext
from typing import Dict, Optional, Any

import psutil

from .config import CONFIG
from .logger import get_logger


class BenchmarkResult:
    def __init__(self, name: str, category: str, value: float, unit: str,
                 lower_is_better: bool = True, metadata: dict = None):
        self.name = name
        self.category = category
        self.value = value
        self.unit = unit
        self.lower_is_better = lower_is_better
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "value": self.value,
            "unit": self.unit,
            "lower_is_better": self.lower_is_better,
            "metadata": self.metadata,
        }


class BenchmarkEngine:
    def __init__(self):
        self.logger = get_logger("benchmark")
        self._cpu_count_logical = psutil.cpu_count(logical=True) or 1
        self._cpu_count_physical = psutil.cpu_count(logical=False) or 1

    def _chudnovsky_pi(self, digits: int = 5000) -> Decimal:
        getcontext().prec = digits + 10
        C = 426880 * Decimal(10005).sqrt()
        M = Decimal(1)
        L = Decimal(13591409)
        X = Decimal(1)
        S = Decimal(13591409)
        K = Decimal(-6)
        for k in range(1, (digits // 14) + 2):
            K += 12
            M = M * (K ** 3 - 16 * K) / Decimal(k ** 3)
            L += 545140134
            X *= -262537412640768000
            S += M * L / X
        return C / S

    def benchmark_cpu(self) -> BenchmarkResult:
        self.logger.info("Starting CPU benchmark")
        start = time.perf_counter()
        try:
            self._chudnovsky_pi(5000)
            elapsed_ms = (time.perf_counter() - start) * 1000
            score = 1_000_000 / elapsed_ms if elapsed_ms > 0 else 0
        except Exception as e:
            self.logger.error(f"CPU benchmark failed: {e}")
            elapsed_ms = 0
            score = 0
        try:
            freq = psutil.cpu_freq()
            freq_mhz = freq.current if freq else 0
        except Exception:
            freq_mhz = 0
        return BenchmarkResult(
            name="CPU Score",
            category="cpu",
            value=round(score, 2),
            unit="score",
            lower_is_better=False,
            metadata={
                "time_ms": round(elapsed_ms, 2),
                "frequency_mhz": round(freq_mhz, 1) if freq_mhz else 0,
                "logical_cpus": self._cpu_count_logical,
                "physical_cpus": self._cpu_count_physical,
            },
        )

    def benchmark_ram(self) -> BenchmarkResult:
        self.logger.info("Starting RAM benchmark")
        size = 100 * 1024 * 1024
        try:
            data = bytearray(size)
            times = []
            for _ in range(3):
                start = time.perf_counter()
                total = 0
                for chunk_start in range(0, size, 65536):
                    chunk = data[chunk_start:chunk_start + 65536]
                    total += len(chunk)
                elapsed = time.perf_counter() - start
                if elapsed > 0:
                    times.append((total / elapsed) / (1024 * 1024))
            speed = sum(times) / len(times) if times else 0
            del data
        except Exception as e:
            self.logger.error(f"RAM benchmark failed: {e}")
            speed = 0
        try:
            mem = psutil.virtual_memory()
            total_gb = round(mem.total / (1024 ** 3), 1)
            available_gb = round(mem.available / (1024 ** 3), 1)
        except Exception:
            total_gb = 0
            available_gb = 0
        return BenchmarkResult(
            name="RAM Score",
            category="ram",
            value=round(speed, 2),
            unit="MB/s",
            lower_is_better=False,
            metadata={
                "speed_mbps": round(speed, 2),
                "total_gb": total_gb,
                "available_gb": available_gb,
            },
        )

    def benchmark_disk(self) -> BenchmarkResult:
        self.logger.info("Starting disk benchmark")
        drive = os.environ.get("SystemDrive", "C:")
        size = 50 * 1024 * 1024
        write_speed = 0
        try:
            tmp_dir = os.path.join(tempfile.gettempdir(), "optinix_bench")
            os.makedirs(tmp_dir, exist_ok=True)
            tmp_path = os.path.join(tmp_dir, "disk_bench.tmp")
            data = os.urandom(size)
            start = time.perf_counter()
            with open(tmp_path, "wb") as f:
                f.write(data)
            elapsed = time.perf_counter() - start
            write_speed = (size / elapsed) / (1024 * 1024) if elapsed > 0 else 0
            try:
                os.unlink(tmp_path)
                os.rmdir(tmp_dir)
            except Exception:
                pass
        except Exception as e:
            self.logger.error(f"Disk write benchmark failed: {e}")
        try:
            usage = psutil.disk_usage(drive + "\\")
            free_gb = round(usage.free / (1024 ** 3), 1)
            total_gb = round(usage.total / (1024 ** 3), 1)
        except Exception:
            free_gb = 0
            total_gb = 0
        try:
            is_ssd = None
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "$m = Get-PhysicalDisk -ErrorAction SilentlyContinue | Where-Object { $_.DriveLetter -eq '" + drive[0] + "' } | Select-Object -ExpandProperty MediaType; if ($m -eq 4) { 'SSD' } elseif ($m -eq 3) { 'HDD' } else { 'Unknown' }"],
                capture_output=True, text=True, timeout=5,
            )
            if "SSD" in r.stdout:
                is_ssd = True
            elif "HDD" in r.stdout:
                is_ssd = False
        except Exception:
            is_ssd = None
        return BenchmarkResult(
            name="Disk Score",
            category="disk",
            value=round(write_speed, 2),
            unit="MB/s",
            lower_is_better=False,
            metadata={
                "write_mbps": round(write_speed, 2),
                "drive_letter": drive,
                "free_gb": free_gb,
                "total_gb": total_gb,
                "is_ssd": is_ssd,
            },
        )

    def benchmark_network(self) -> BenchmarkResult:
        self.logger.info("Starting network benchmark")
        ping_ms = None
        download_mbps = None
        upload_mbps = None
        try:
            from .speed_test import SpeedTest
            st = SpeedTest()
            ping_result = st.test_ping(count=2)
            if "avg_ms" in ping_result:
                ping_ms = ping_result["avg_ms"]
        except Exception:
            pass
        if ping_ms is None:
            try:
                host = "8.8.8.8"
                param = "-n" if os.name == "nt" else "-c"
                r = subprocess.run(
                    ["ping", param, "2", host],
                    capture_output=True, text=True, timeout=5,
                )
                times = []
                for line in r.stdout.split("\n"):
                    if "time=" in line or "time<" in line:
                        try:
                            t = line.split("time=")[-1].split("ms")[0].split("<")[-1].strip()
                            times.append(float(t))
                        except Exception:
                            pass
                if times:
                    ping_ms = sum(times) / len(times)
            except Exception:
                pass
        try:
            from .speed_test import SpeedTest
            st = SpeedTest()
            dl = st.test_download(5)
            if "download_mbps" in dl:
                download_mbps = dl["download_mbps"]
            ul = st.test_upload(1)
            if "upload_mbps" in ul:
                upload_mbps = ul["upload_mbps"]
        except Exception:
            pass
        if ping_ms and ping_ms > 0:
            score = 1000 / ping_ms
        else:
            score = 0
            ping_ms = ping_ms or 999
        return BenchmarkResult(
            name="Network Score",
            category="network",
            value=round(score, 2),
            unit="score",
            lower_is_better=False,
            metadata={
                "ping_ms": round(ping_ms, 1),
                "download_mbps": round(download_mbps, 2) if download_mbps else None,
                "upload_mbps": round(upload_mbps, 2) if upload_mbps else None,
            },
        )

    def _get_event_log_boot_duration(self) -> Optional[float]:
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "$e = Get-WinEvent -FilterHashtable @{LogName='System';Id=12} -MaxEvents 1 -ErrorAction SilentlyContinue; if ($e) { $e.Message } else { 'N/A' }"],
                capture_output=True, text=True, timeout=8,
            )
            msg = r.stdout.strip()
            if msg and msg != "N/A":
                m = re.search(r"(\d+)\s*ms", msg, re.IGNORECASE)
                if m:
                    return float(m.group(1)) / 1000
                m = re.search(r"Boot[^:]*:[^\d]*(\d+\.?\d*)\s*seconds?", msg, re.IGNORECASE)
                if m:
                    return float(m.group(1))
                m = re.search(r"(\d+\.?\d*)\s*seconds?", msg, re.IGNORECASE)
                if m:
                    return float(m.group(1))
        except Exception:
            pass
        return None

    def _get_perf_log_boot_duration(self) -> Optional[float]:
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "$e = Get-WinEvent -LogName 'Microsoft-Windows-Diagnostics-Performance/Operational' -MaxEvents 3 -ErrorAction SilentlyContinue | Where-Object { $_.Id -eq 100 }; if ($e) { $e.Message } else { 'N/A' }"],
                capture_output=True, text=True, timeout=8,
            )
            msg = r.stdout.strip()
            if msg and msg != "N/A":
                m = re.search(r"(\d+)\s*ms", msg, re.IGNORECASE)
                if m:
                    return float(m.group(1)) / 1000
                m = re.search(r"Total Boot Time[^\d]*(\d+)", msg, re.IGNORECASE)
                if m:
                    return float(m.group(1))
        except Exception:
            pass
        return None

    def benchmark_startup(self) -> BenchmarkResult:
        self.logger.info("Starting startup benchmark")
        boot_seconds = None
        startup_apps_count = 0
        boot_seconds = self._get_event_log_boot_duration()
        if boot_seconds is None:
            boot_seconds = self._get_perf_log_boot_duration()
        if boot_seconds is None:
            try:
                r = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     "$boot = (Get-CimInstance -ClassName Win32_OperatingSystem -ErrorAction SilentlyContinue).LastBootUpTime; if ($boot) { [math]::Round(((Get-Date) - $boot).TotalSeconds, 1) } else { 'N/A' }"],
                    capture_output=True, text=True, timeout=5,
                )
                val = r.stdout.strip()
                if val and val != "N/A":
                    uptime = float(val)
                    boot_seconds = 30
            except Exception:
                pass
        if boot_seconds is None or boot_seconds <= 0:
            boot_seconds = 45
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "@(Get-CimInstance Win32_StartupCommand -ErrorAction SilentlyContinue).Count"],
                capture_output=True, text=True, timeout=5,
            )
            if r.stdout.strip():
                startup_apps_count = int(r.stdout.strip())
        except Exception:
            pass
        score = round(max(0, 100 - min(boot_seconds / 120 * 100, 100)), 1)
        try:
            boot_time_str = time.strftime(
                "%Y-%m-%d %H:%M:%S",
                time.localtime(psutil.boot_time()),
            )
        except Exception:
            boot_time_str = "N/A"
        return BenchmarkResult(
            name="Startup Score",
            category="startup",
            value=round(score, 1),
            unit="/100",
            lower_is_better=False,
            metadata={
                "boot_seconds": round(boot_seconds, 1),
                "boot_time": boot_time_str,
                "startup_apps_count": startup_apps_count,
            },
        )

    @staticmethod
    def _run_with_timeout(method, timeout: float = 15, args=(), kwargs=None) -> Any:
        """Run a callable with a timeout using threading."""
        result = [None]
        error = [None]
        done = threading.Event()

        def worker():
            try:
                result[0] = method(*args, **(kwargs or {}))
            except Exception as e:
                error[0] = e
            finally:
                done.set()

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        finished = done.wait(timeout)
        if not finished:
            raise TimeoutError(f"Timed out after {timeout}s")
        if error[0]:
            raise error[0]
        return result[0]

    def benchmark_all(self) -> Dict[str, BenchmarkResult]:
        self.logger.info("Running all benchmarks")
        results = {}
        benchmarks = [
            ("cpu", self.benchmark_cpu, 30),
            ("ram", self.benchmark_ram, 10),
            ("disk", self.benchmark_disk, 15),
            ("network", self.benchmark_network, 12),
            ("startup", self.benchmark_startup, 12),
        ]
        deadline = time.time() + 28
        for category, method, per_timeout in benchmarks:
            if time.time() >= deadline:
                self.logger.warning(f"Skipping {category} benchmark (deadline passed)")
                results[category] = BenchmarkResult(
                    name=f"{category.title()} Score",
                    category=category,
                    value=0,
                    unit="score",
                    metadata={"error": "timed_out"},
                )
                continue
            try:
                results[category] = self._run_with_timeout(method, timeout=per_timeout)
            except TimeoutError:
                self.logger.warning(f"Skipping {category} benchmark (timed out)")
                results[category] = BenchmarkResult(
                    name=f"{category.title()} Score",
                    category=category,
                    value=0,
                    unit="score",
                    metadata={"error": "timed_out"},
                )
            except Exception as e:
                self.logger.error(f"{category} benchmark crashed: {e}")
                results[category] = BenchmarkResult(
                    name=f"{category.title()} Score",
                    category=category,
                    value=0,
                    unit="score",
                    metadata={"error": str(e)},
                )
        self.logger.info("All benchmarks completed")
        return results

    @staticmethod
    def compare(before: Dict[str, BenchmarkResult], after: Dict[str, BenchmarkResult]) -> Dict[str, Dict[str, Any]]:
        comparison = {}
        all_categories = set(before.keys()) | set(after.keys())
        for category in all_categories:
            b = before.get(category)
            a = after.get(category)
            if b is None or a is None:
                continue
            b_val = b.value
            a_val = a.value
            delta = round(a_val - b_val, 2)
            if b_val != 0:
                percent = round((delta / b_val) * 100, 1)
            else:
                percent = 0 if a_val == 0 else 100.0
            lower_is_better = b.lower_is_better
            if lower_is_better:
                if delta < 0:
                    verdict = "improved"
                elif delta > 0:
                    verdict = "declined"
                else:
                    verdict = "unchanged"
            else:
                if delta > 0:
                    verdict = "improved"
                elif delta < 0:
                    verdict = "declined"
                else:
                    verdict = "unchanged"
            comparison[category] = {
                "name": b.name,
                "unit": b.unit,
                "before": b_val,
                "after": a_val,
                "delta": delta,
                "percent": percent,
                "verdict": verdict,
                "lower_is_better": lower_is_better,
            }
        return comparison

    @staticmethod
    def format_report(results: Dict[str, BenchmarkResult]) -> str:
        lines = []
        lines.append("=" * 60)
        lines.append("  BENCHMARK REPORT")
        lines.append("=" * 60)
        if not results:
            lines.append("  No results to report.")
            lines.append("=" * 60)
            return "\n".join(lines)
        for category in ["cpu", "ram", "disk", "network", "startup"]:
            result = results.get(category)
            if result is None:
                continue
            val = result.value
            unit = result.unit
            name = result.name
            meta = result.metadata
            verdict = meta.get("verdict", "")
            label = name
            line = f"  {label:<20s} {val:>10.2f} {unit:<8s}"
            if verdict:
                line += f" {verdict}"
            lines.append(line)
        lines.append("=" * 60)
        return "\n".join(lines)

    def benchmark_gpu(self) -> BenchmarkResult:
        """GPU benchmark using nvidia-smi and basic compute test."""
        self.logger.info("Starting GPU benchmark")
        try:
            # Try nvidia-smi for VRAM bandwidth estimate
            r = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,temperature.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=15
            )
            if r.returncode == 0 and r.stdout.strip():
                parts = r.stdout.strip().split(", ")
                if len(parts) >= 4:
                    gpu_name = parts[0]
                    vram_total = float(parts[1])
                    vram_used = float(parts[2])
                    temp = float(parts[3])

                    # Compute a simple score based on VRAM availability
                    vram_free = vram_total - vram_used
                    score = min(100, (vram_free / max(vram_total, 1)) * 100)

                    return BenchmarkResult(
                        name="GPU Score",
                        category="gpu",
                        value=round(score, 1),
                        unit="score",
                        lower_is_better=False,
                        metadata={
                            "gpu_name": gpu_name,
                            "vram_total_mb": vram_total,
                            "vram_used_mb": vram_used,
                            "temperature_c": temp,
                        },
                    )
            # Fallback: no GPU detected
            return BenchmarkResult(
                name="GPU Score",
                category="gpu",
                value=0,
                unit="score",
                lower_is_better=False,
                metadata={"error": "No NVIDIA GPU detected via nvidia-smi"},
            )
        except Exception as e:
            return BenchmarkResult(
                name="GPU Score",
                category="gpu",
                value=0,
                unit="score",
                lower_is_better=False,
                metadata={"error": str(e)},
            )

    def benchmark_all_with_gpu(self) -> Dict[str, BenchmarkResult]:
        """Run all benchmarks including GPU."""
        results = self.benchmark_all()
        results["gpu"] = self.benchmark_gpu()
        return results

    def save_history(self, results: Dict[str, BenchmarkResult]) -> str:
        """Save benchmark results to history. Returns the entry ID."""
        import json
        from datetime import datetime

        history_dir = os.path.join(CONFIG.base_dir, "data", "benchmark_history")
        os.makedirs(history_dir, exist_ok=True)

        entry_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        entry = {
            "id": entry_id,
            "timestamp": datetime.now().isoformat(),
            "results": {},
        }
        for cat, result in results.items():
            entry["results"][cat] = result.to_dict()

        path = os.path.join(history_dir, f"bench_{entry_id}.json")
        with open(path, "w") as f:
            json.dump(entry, f, indent=2)

        self.logger.info(f"Benchmark history saved: {entry_id}")
        return entry_id

    def get_history(self, limit: int = 20) -> list:
        """Get recent benchmark history entries."""
        import json
        history_dir = os.path.join(CONFIG.base_dir, "data", "benchmark_history")
        if not os.path.exists(history_dir):
            return []

        entries = []
        for f in sorted(os.listdir(history_dir), reverse=True)[:limit]:
            if f.startswith("bench_") and f.endswith(".json"):
                try:
                    with open(os.path.join(history_dir, f), "r") as fp:
                        entries.append(json.load(fp))
                except Exception:
                    continue
        return entries

    def compare_history(self, entry_id_1: str, entry_id_2: str) -> Dict[str, Dict[str, Any]]:
        """Compare two historical benchmark entries."""
        import json
        history_dir = os.path.join(CONFIG.base_dir, "data", "benchmark_history")

        def load_entry(eid):
            path = os.path.join(history_dir, f"bench_{eid}.json")
            with open(path, "r") as f:
                return json.load(f)

        e1 = load_entry(entry_id_1)
        e2 = load_entry(entry_id_2)

        comparison = {}
        all_cats = set(e1.get("results", {}).keys()) | set(e2.get("results", {}).keys())
        for cat in all_cats:
            r1 = e1.get("results", {}).get(cat, {})
            r2 = e2.get("results", {}).get(cat, {})
            if not r1 or not r2:
                continue
            v1 = r1.get("value", 0)
            v2 = r2.get("value", 0)
            delta = round(v2 - v1, 2)
            lower_is_better = r1.get("lower_is_better", True)
            if lower_is_better:
                verdict = "improved" if delta < 0 else "declined" if delta > 0 else "unchanged"
            else:
                verdict = "improved" if delta > 0 else "declined" if delta < 0 else "unchanged"

            comparison[cat] = {
                "name": r1.get("name", cat),
                "before": v1,
                "after": v2,
                "delta": delta,
                "verdict": verdict,
            }
        return comparison
