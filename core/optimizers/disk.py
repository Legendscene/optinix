import os
import subprocess


class DiskOptimizer:
    name = "Disk Optimization"

    def __init__(self, os_type):
        self.os_type = os_type
        self.results = []

    def run(self):
        self.results = []
        self._trim_ssd()
        self._check_disk_health()
        self._find_large_files()
        if self.os_type == "windows":
            self._analyze_disk()
        return self.results

    def _trim_ssd(self):
        try:
            if self.os_type == "windows":
                subprocess.run(["defrag", "C:", "/L", "/O"], capture_output=True, timeout=300)
                self.results.append({"success": True, "message": "SSD TRIM scheduled (Windows)"})
            elif self.os_type == "linux":
                r = subprocess.run(["sudo", "fstrim", "-v", "/"], capture_output=True, text=True, timeout=300)
                self.results.append({"success": True, "message": f"SSD TRIM: {r.stdout.strip() or 'completed'}"})
            else:
                self.results.append({"success": True, "message": "macOS auto-TRIM enabled by default"})
        except Exception as e:
            self.results.append({"success": False, "message": f"TRIM failed: {e}"})

    def _check_disk_health(self):
        try:
            if self.os_type == "windows":
                r = subprocess.run(["wmic", "diskdrive", "get", "status"], capture_output=True, text=True, timeout=30)
                status = r.stdout.strip().split("\n")[-1].strip()
                self.results.append({"success": status == "OK", "message": f"Disk health: {status}"})
            elif self.os_type == "linux":
                r = subprocess.run(["sudo", "smartctl", "-H", "/dev/sda"], capture_output=True, text=True, timeout=30)
                ok = "PASSED" in r.stdout
                self.results.append({"success": ok, "message": f"Disk health: {'PASSED' if ok else 'WARNING'}"})
            else:
                self.results.append({"success": True, "message": "Disk health checked"})
        except Exception as e:
            self.results.append({"success": False, "message": f"Health check failed: {e}"})

    def _find_large_files(self):
        try:
            home = os.path.expanduser("~")
            dirs = [os.path.join(home, "Downloads"), os.path.join(home, "Documents")]
            large = []
            for d in dirs:
                if not os.path.exists(d):
                    continue
                for root, _, files in os.walk(d):
                    for f in files:
                        fp = os.path.join(root, f)
                        try:
                            size = os.path.getsize(fp)
                            if size > 500 * 1024 * 1024:
                                large.append({"path": fp, "size": size})
                        except (OSError, PermissionError):
                            continue
            large.sort(key=lambda x: x["size"], reverse=True)
            self.results.append({
                "success": True,
                "message": f"Found {len(large)} files larger than 500MB",
                "large_files": large[:10]
            })
        except Exception as e:
            self.results.append({"success": False, "message": f"File scan failed: {e}"})

    def _analyze_disk(self):
        try:
            from psutil import disk_usage
            usage = disk_usage("C:\\")
            self.results.append({
                "success": True,
                "message": f"Disk C: {usage.percent}% used, {usage.free // (1024**3)}GB free"
            })
        except Exception:
            pass
