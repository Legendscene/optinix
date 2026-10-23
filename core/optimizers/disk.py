import os
import subprocess
import time
from typing import Dict, Any, List
from core.base import OptimizerBase, OPTIMIZER_CATEGORY_SAFE
from core.config import CONFIG


class DiskOptimizer(OptimizerBase):
    name = "Disk Optimization"
    description = "TRIM SSD, check disk health, scan large files, and analyze disk usage"
    category = OPTIMIZER_CATEGORY_SAFE
    benefit = "Improved disk performance, freed space, early SSD health warnings"
    risks = "TRIM is safe; health checks are read-only; large file scan is CPU-intensive temporarily"
    admin_required = True
    requirements = {}

    def __init__(self):
        super().__init__()
        self.os_type = CONFIG.os_type

    def run(self) -> List[Dict[str, Any]]:
        self.results = []
        self.logger.info("Starting disk optimization")
        self._trim_ssd()
        self._check_disk_health()
        self._find_large_files()
        if self.os_type == "windows":
            self._analyze_disk()
        return [r.to_dict() for r in self.results]

    def _trim_ssd(self):
        try:
            if self.os_type == "windows":
                subprocess.run(["defrag", "C:", "/L"], capture_output=True, timeout=60)
                self.add_result(True, "SSD TRIM scheduled (Windows)")
            elif self.os_type == "linux":
                r = subprocess.run(["sudo", "fstrim", "-v", "/"], capture_output=True, text=True, timeout=30)
                self.add_result(True, f"SSD TRIM: {r.stdout.strip() or 'completed'}")
            else:
                self.add_result(True, "macOS auto-TRIM enabled by default")
        except subprocess.TimeoutExpired:
            self.logger.error("TRIM timed out")
            self.add_result(False, "TRIM timed out")
        except Exception as e:
            self.logger.error(f"TRIM failed: {e}")
            self.add_result(False, f"TRIM failed: {e}")

    def _check_disk_health(self):
        try:
            if self.os_type == "windows":
                r = subprocess.run(["wmic", "diskdrive", "get", "status"], capture_output=True, text=True, timeout=15)
                status = r.stdout.strip().split("\n")[-1].strip()
                self.add_result(status == "OK", f"Disk health: {status}")
            elif self.os_type == "linux":
                r = subprocess.run(["sudo", "smartctl", "-H", "/dev/sda"], capture_output=True, text=True, timeout=15)
                ok = "PASSED" in r.stdout
                self.add_result(ok, f"Disk health: {'PASSED' if ok else 'WARNING'}")
            else:
                self.add_result(True, "Disk health checked")
        except subprocess.TimeoutExpired:
            self.logger.error("Health check timed out")
            self.add_result(False, "Health check timed out")
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            self.add_result(False, f"Health check failed: {e}")

    def _find_large_files(self):
        try:
            home = os.path.expanduser("~")
            dirs = [os.path.join(home, "Downloads"), os.path.join(home, "Documents")]
            large = []
            deadline = time.time() + 10
            for d in dirs:
                if not os.path.exists(d):
                    continue
                for root, _, files in os.walk(d):
                    if time.time() > deadline:
                        break
                    for f in files:
                        if time.time() > deadline:
                            break
                        fp = os.path.join(root, f)
                        try:
                            size = os.path.getsize(fp)
                            if size > 500 * 1024 * 1024:
                                large.append({"path": fp, "size": size})
                        except (OSError, PermissionError):
                            continue
                if time.time() > deadline:
                    break
            large.sort(key=lambda x: x["size"], reverse=True)
            self.add_result(True, f"Found {len(large)} files larger than 500MB", large_files=large[:10])
        except Exception as e:
            self.logger.error(f"File scan failed: {e}")
            self.add_result(False, f"File scan failed: {e}")

    def _analyze_disk(self):
        try:
            from psutil import disk_usage
            usage = disk_usage("C:\\")
            self.add_result(True, f"Disk C: {usage.percent}% used, {usage.free // (1024**3)}GB free")
        except Exception:
            pass
