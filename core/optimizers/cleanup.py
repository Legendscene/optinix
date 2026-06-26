import os
import shutil
import subprocess


class CleanupOptimizer:
    name = "System Cleanup"

    def __init__(self, os_type):
        self.os_type = os_type
        self.results = []

    def run(self):
        self.results = []
        self._clean_temp()
        self._clean_crash_dumps()
        self._clean_thumbnails()
        self._clean_dns()
        self._clean_browser_cache()
        self._clean_logs()
        self._clean_prefetch()
        self._clean_windows_update()
        if self.os_type == "windows":
            self._clean_recycle_bin()
            self._clean_windows_temp()
            self._clean_old_logs()
        elif self.os_type == "macos":
            self._clean_macos_cache()
        elif self.os_type == "linux":
            self._clean_linux_cache()
        return self.results

    def _clean_temp(self):
        temp_dirs = [os.environ.get("TEMP", ""), os.environ.get("TMP", "")]
        if self.os_type == "linux":
            temp_dirs.extend(["/tmp", "/var/tmp"])
        elif self.os_type == "macos":
            temp_dirs.append(os.path.expanduser("~/Library/Caches"))

        cleaned = 0
        for d in temp_dirs:
            if not d or not os.path.exists(d):
                continue
            try:
                for item in os.listdir(d):
                    path = os.path.join(d, item)
                    try:
                        if os.path.isfile(path):
                            os.remove(path)
                            cleaned += 1
                        elif os.path.isdir(path):
                            shutil.rmtree(path, ignore_errors=True)
                            cleaned += 1
                    except (PermissionError, OSError):
                        continue
            except (PermissionError, OSError):
                continue
        self.results.append({"success": True, "message": f"Temp files cleaned ({cleaned} items)"})

    def _clean_crash_dumps(self):
        dirs = []
        if self.os_type == "windows":
            home = os.path.expanduser("~")
            dirs = [os.path.join(home, "AppData", "Local", "CrashDumps"),
                    os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Minidump")]
        elif self.os_type == "macos":
            dirs = [os.path.expanduser("~/Library/Logs/DiagnosticReports")]
        elif self.os_type == "linux":
            dirs = ["/var/crash", "/var/log/apport"]

        cleaned = 0
        for d in dirs:
            if os.path.exists(d):
                try:
                    for f in os.listdir(d):
                        fp = os.path.join(d, f)
                        try:
                            os.remove(fp) if os.path.isfile(fp) else shutil.rmtree(fp, ignore_errors=True)
                            cleaned += 1
                        except (PermissionError, OSError):
                            continue
                except (PermissionError, OSError):
                    continue
        self.results.append({"success": True, "message": f"Crash dumps cleaned ({cleaned} files)"})

    def _clean_thumbnails(self):
        dirs = []
        if self.os_type == "windows":
            home = os.path.expanduser("~")
            dirs = [os.path.join(home, "AppData", "Local", "Microsoft", "Windows", "Explorer")]
        elif self.os_type == "macos":
            dirs = [os.path.expanduser("~/Library/Caches/com.apple.thumbnails")]

        cleaned = 0
        for d in dirs:
            if os.path.exists(d):
                try:
                    for f in os.listdir(d):
                        if "thumbcache" in f or "Thumbnail" in f:
                            fp = os.path.join(d, f)
                            try:
                                os.remove(fp)
                                cleaned += 1
                            except (PermissionError, OSError):
                                continue
                except (PermissionError, OSError):
                    continue
        self.results.append({"success": True, "message": f"Thumbnail cache cleaned ({cleaned} files)"})

    def _clean_dns(self):
        try:
            if self.os_type == "windows":
                subprocess.run(["ipconfig", "/flushdns"], capture_output=True, timeout=10)
            elif self.os_type == "macos":
                subprocess.run(["sudo", "dscacheutil", "-flushcache"], capture_output=True, timeout=10)
                subprocess.run(["sudo", "killall", "-HUP", "mDNSResponder"], capture_output=True, timeout=10)
            elif self.os_type == "linux":
                subprocess.run(["sudo", "systemd-resolve", "--flush-caches"], capture_output=True, timeout=10)
            self.results.append({"success": True, "message": "DNS cache flushed"})
        except Exception as e:
            self.results.append({"success": False, "message": f"DNS flush failed: {e}"})

    def _clean_browser_cache(self):
        home = os.path.expanduser("~")
        cache_map = {}
        if self.os_type == "windows":
            cache_map = {
                "Chrome": [os.path.join(home, "AppData", "Local", "Google", "Chrome", "User Data", "Default", "Cache")],
                "Firefox": [os.path.join(home, "AppData", "Local", "Mozilla", "Firefox", "Profiles")],
                "Edge": [os.path.join(home, "AppData", "Local", "Microsoft", "Edge", "User Data", "Default", "Cache")],
                "Brave": [os.path.join(home, "AppData", "Local", "BraveSoftware", "Brave-Browser", "User Data", "Default", "Cache")],
                "Opera": [os.path.join(home, "AppData", "Local", "Opera Software", "Opera Stable", "Cache")]
            }
        elif self.os_type == "macos":
            cache_map = {
                "Chrome": [os.path.join(home, "Library", "Caches", "Google", "Chrome")],
                "Firefox": [os.path.join(home, "Library", "Caches", "Firefox")],
                "Safari": [os.path.join(home, "Library", "Caches", "com.apple.Safari")]
            }
        elif self.os_type == "linux":
            cache_map = {
                "Chrome": [os.path.join(home, ".cache", "google-chrome")],
                "Firefox": [os.path.join(home, ".cache", "mozilla")]
            }

        cleaned = 0
        for browser, paths in cache_map.items():
            for path in paths:
                if os.path.exists(path):
                    try:
                        shutil.rmtree(path, ignore_errors=True)
                        cleaned += 1
                    except (PermissionError, OSError):
                        continue
        self.results.append({"success": True, "message": f"Browser caches cleaned ({cleaned} browsers)"})

    def _clean_logs(self):
        log_dirs = []
        if self.os_type == "windows":
            log_dirs = [os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Logs")]
        elif self.os_type == "macos":
            log_dirs = [os.path.expanduser("~/Library/Logs")]
        elif self.os_type == "linux":
            log_dirs = ["/var/log"]

        cleaned = 0
        for d in log_dirs:
            if os.path.exists(d):
                try:
                    for f in os.listdir(d):
                        if f.endswith((".log", ".log.1", ".log.2", ".etl")):
                            fp = os.path.join(d, f)
                            try:
                                os.remove(fp)
                                cleaned += 1
                            except (PermissionError, OSError):
                                continue
                except (PermissionError, OSError):
                    continue
        self.results.append({"success": True, "message": f"Log files cleaned ({cleaned} files)"})

    def _clean_prefetch(self):
        if self.os_type == "windows":
            pf = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Prefetch")
            cleaned = 0
            if os.path.exists(pf):
                for f in os.listdir(pf):
                    try:
                        os.remove(os.path.join(pf, f))
                        cleaned += 1
                    except (PermissionError, OSError):
                        continue
            self.results.append({"success": True, "message": f"Prefetch cleaned ({cleaned} files)"})

    def _clean_windows_update(self):
        try:
            wu_path = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "SoftwareDistribution", "Download")
            cleaned = 0
            if os.path.exists(wu_path):
                for f in os.listdir(wu_path):
                    fp = os.path.join(wu_path, f)
                    try:
                        os.remove(fp) if os.path.isfile(fp) else shutil.rmtree(fp, ignore_errors=True)
                        cleaned += 1
                    except (PermissionError, OSError):
                        continue
            self.results.append({"success": True, "message": f"Windows Update cache cleaned ({cleaned} items)"})
        except Exception:
            pass

    def _clean_recycle_bin(self):
        try:
            subprocess.run(
                ["powershell", "-Command", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"],
                capture_output=True, timeout=30
            )
            self.results.append({"success": True, "message": "Recycle Bin emptied"})
        except Exception as e:
            self.results.append({"success": False, "message": f"Recycle Bin failed: {e}"})

    def _clean_windows_temp(self):
        try:
            win_temp = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Temp")
            cleaned = 0
            if os.path.exists(win_temp):
                for f in os.listdir(win_temp):
                    fp = os.path.join(win_temp, f)
                    try:
                        os.remove(fp) if os.path.isfile(fp) else shutil.rmtree(fp, ignore_errors=True)
                        cleaned += 1
                    except (PermissionError, OSError):
                        continue
            self.results.append({"success": True, "message": f"Windows Temp cleaned ({cleaned} items)"})
        except Exception:
            pass

    def _clean_old_logs(self):
        home = os.path.expanduser("~")
        log_dirs = [os.path.join(home, "AppData", "Local", "D3DSCache"),
                     os.path.join(home, "AppData", "Local", "Microsoft", "Windows", "INetCache")]
        cleaned = 0
        for d in log_dirs:
            if os.path.exists(d):
                try:
                    shutil.rmtree(d, ignore_errors=True)
                    cleaned += 1
                except (PermissionError, OSError):
                    continue
        self.results.append({"success": True, "message": f"Old cache directories cleaned ({cleaned} dirs)"})

    def _clean_macos_cache(self):
        try:
            cache_dir = os.path.expanduser("~/Library/Caches")
            cleaned = 0
            if os.path.exists(cache_dir):
                for app in os.listdir(cache_dir):
                    app_cache = os.path.join(cache_dir, app)
                    try:
                        shutil.rmtree(app_cache, ignore_errors=True)
                        cleaned += 1
                    except (PermissionError, OSError):
                        continue
            self.results.append({"success": True, "message": f"macOS cache cleaned ({cleaned} apps)"})
        except Exception:
            pass

    def _clean_linux_cache(self):
        try:
            cache_dir = os.path.expanduser("~/.cache")
            cleaned = 0
            if os.path.exists(cache_dir):
                for app in os.listdir(cache_dir):
                    app_cache = os.path.join(cache_dir, app)
                    try:
                        shutil.rmtree(app_cache, ignore_errors=True)
                        cleaned += 1
                    except (PermissionError, OSError):
                        continue
            self.results.append({"success": True, "message": f"Linux cache cleaned ({cleaned} apps)"})
        except Exception:
            pass
