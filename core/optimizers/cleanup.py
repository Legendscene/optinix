import os
import subprocess
from core.base import OptimizerBase
from core.config import CONFIG


class CleanupOptimizer(OptimizerBase):
    name = "System Cleanup"
    description = "Cleans temporary files and empties the recycle bin"
    category = "safe"
    benefit = "Frees up disk space by removing temporary files and emptying the recycle bin"
    risks = "Minimal. May remove files currently in use by applications."
    admin_required = False
    requirements = {}

    def run(self):
        if CONFIG.os_type == "windows":
            self._clean_temp_files()
            self._empty_recycle_bin()
        return [r.to_dict() for r in self.results]

    def _clean_temp_files(self):
        try:
            import shutil
            tp = os.environ.get("TEMP", "")
            if not tp or not os.path.exists(tp):
                self.add_result(True, "Temp folder not found")
                return
            cleaned = 0
            for f in os.listdir(tp):
                fp = os.path.join(tp, f)
                try:
                    if os.path.isfile(fp):
                        os.remove(fp)
                        cleaned += 1
                    elif os.path.isdir(fp):
                        shutil.rmtree(fp, ignore_errors=True)
                        cleaned += 1
                except (PermissionError, OSError):
                    continue
            self.add_result(True, f"Cleaned {cleaned} temp files")
        except Exception as e:
            self.add_result(False, f"Temp cleanup: {e}")

    def _empty_recycle_bin(self):
        try:
            subprocess.run(
                ["powershell", "-Command", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"],
                capture_output=True, timeout=30
            )
            self.add_result(True, "Recycle Bin emptied")
        except Exception as e:
            self.add_result(False, f"Recycle Bin: {e}")
