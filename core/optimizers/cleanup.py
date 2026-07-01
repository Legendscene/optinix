import os
import subprocess

class CleanupOptimizer:
    name = "System Cleanup"

    def __init__(self, os_type):
        self.os_type = os_type
        self.results = []

    def run(self):
        self.results = []
        if self.os_type == "windows":
            self._clean_temp_files()
            self._empty_recycle_bin()
        return self.results

    def _clean_temp_files(self):
        try:
            import shutil
            tp = os.environ.get("TEMP", "")
            if not tp or not os.path.exists(tp):
                self.results.append({"success": True, "message": "Temp folder not found"})
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
            self.results.append({"success": True, "message": f"Cleaned {cleaned} temp files"})
        except Exception as e:
            self.results.append({"success": False, "message": f"Temp cleanup: {e}"})

    def _empty_recycle_bin(self):
        try:
            subprocess.run(
                ["powershell", "-Command", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"],
                capture_output=True, timeout=30
            )
            self.results.append({"success": True, "message": "Recycle Bin emptied"})
        except Exception as e:
            self.results.append({"success": False, "message": f"Recycle Bin: {e}"})
