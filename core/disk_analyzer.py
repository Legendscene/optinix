import os
import subprocess
from typing import Dict, List, Any

class DiskAnalyzer:
    def __init__(self, os_type: str):
        self.os_type = os_type

    def scan(self, drive: str = "C:") -> Dict[str, Any]:
        if self.os_type != "windows":
            return {"categories": [], "total_bytes": 0}

        categories = []
        total_bytes = 0

        cat_config = [
            ("Temp Files", self._scan_temp, "Temp files from running apps and system"),
            ("Windows Temp", self._scan_win_temp, "Windows system temporary files"),
            ("Recycle Bin", self._scan_recycle_bin, "Deleted files still in Recycle Bin"),
            ("Browser Cache", self._scan_browser_cache, "Chrome, Edge, Firefox, Brave, Opera caches"),
            ("System Logs", self._scan_logs, "Windows event logs and log files"),
            ("Windows Update", self._scan_wu, "Windows Update download cache"),
            ("Delivery Opt.", self._scan_delivery_opt, "Delivery Optimization cached updates"),
            ("Crash Dumps", self._scan_dumps, "System and app crash dumps"),
            ("Thumbnails", self._scan_thumbnails, "Thumbnail cache files"),
            ("Prefetch", self._scan_prefetch, "App prefetch files"),
            ("Old Windows", self._scan_old_windows, "Previous Windows installation(s)"),
            ("Recycle Bin", self._scan_recycle_bin, "Files in Recycle Bin"),
        ]

        for name, scanner, desc in cat_config:
            try:
                items = scanner(drive)
                cat_bytes = sum(i.get("size", 0) for i in items)
                total_bytes += cat_bytes
                categories.append({
                    "name": name,
                    "description": desc,
                    "items": len(items),
                    "bytes": cat_bytes,
                    "files": items[:20],
                })
            except Exception:
                pass

        return {"categories": categories, "total_bytes": total_bytes, "drive": drive}

    def _dir_size(self, path: str) -> List[Dict[str, Any]]:
        items = []
        if not os.path.exists(path):
            return items
        try:
            for entry in os.listdir(path):
                try:
                    fp = os.path.join(path, entry)
                    if os.path.isfile(fp):
                        items.append({"path": fp, "size": os.path.getsize(fp)})
                    elif os.path.isdir(fp):
                        sz = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fn in os.walk(fp) for f in fn if os.path.isfile(os.path.join(dp, f))) if os.path.exists(fp) else 0
                        items.append({"path": fp, "size": sz})
                except (PermissionError, OSError):
                    continue
        except (PermissionError, OSError):
            pass
        return items

    def _scan_temp(self, drive: str) -> List[Dict[str, Any]]:
        return self._dir_size(os.environ.get("TEMP", ""))

    def _scan_win_temp(self, drive: str) -> List[Dict[str, Any]]:
        wt = os.path.join(drive + "\\", "Windows", "Temp")
        return self._dir_size(wt)

    def _scan_recycle_bin(self, drive: str) -> List[Dict[str, Any]]:
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"(Get-ChildItem '::{drive[0]}645FF040-5081-101B-9F08-00AA002F954E}' -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum"],
                capture_output=True, text=True, timeout=10
            )
            sz = int(r.stdout.strip()) if r.stdout.strip().isdigit() else 0
            return [{"path": f"{drive}\\$Recycle.Bin", "size": sz}] if sz > 0 else []
        except Exception:
            return []

    def _scan_browser_cache(self, drive: str) -> List[Dict[str, Any]]:
        home = os.path.expanduser("~")
        paths = {
            "Chrome": os.path.join(home, "AppData", "Local", "Google", "Chrome", "User Data", "Default", "Cache"),
            "Edge": os.path.join(home, "AppData", "Local", "Microsoft", "Edge", "User Data", "Default", "Cache"),
            "Brave": os.path.join(home, "AppData", "Local", "BraveSoftware", "Brave-Browser", "User Data", "Default", "Cache"),
            "Firefox": os.path.join(home, "AppData", "Local", "Mozilla", "Firefox", "Profiles"),
            "Opera": os.path.join(home, "AppData", "Local", "Opera Software", "Opera Stable", "Cache"),
        }
        items = []
        for name, path in paths.items():
            if os.path.exists(path):
                sz = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fn in os.walk(path) for f in fn if os.path.isfile(os.path.join(dp, f))) if os.path.exists(path) else 0
                if sz > 0:
                    items.append({"path": path, "size": sz, "browser": name})
        return items

    def _scan_logs(self, drive: str) -> List[Dict[str, Any]]:
        logs = os.path.join(drive + "\\", "Windows", "Logs")
        return self._dir_size(logs)

    def _scan_wu(self, drive: str) -> List[Dict[str, Any]]:
        wu = os.path.join(drive + "\\", "Windows", "SoftwareDistribution", "Download")
        return self._dir_size(wu)

    def _scan_delivery_opt(self, drive: str) -> List[Dict[str, Any]]:
        do = os.path.join(drive + "\\", "Windows", "ServiceProfiles", "LocalService", "AppData", "Local", "Microsoft", "DeliveryOptimization")
        return self._dir_size(do)

    def _scan_dumps(self, drive: str) -> List[Dict[str, Any]]:
        home = os.path.expanduser("~")
        items = []
        cd = os.path.join(home, "AppData", "Local", "CrashDumps")
        md = os.path.join(drive + "\\", "Windows", "Minidump")
        for p in [cd, md]:
            items.extend(self._dir_size(p))
        return items

    def _scan_thumbnails(self, drive: str) -> List[Dict[str, Any]]:
        home = os.path.expanduser("~")
        tb = os.path.join(home, "AppData", "Local", "Microsoft", "Windows", "Explorer")
        items = []
        if os.path.exists(tb):
            for f in os.listdir(tb):
                if "thumbcache" in f or "Thumbnail" in f:
                    fp = os.path.join(tb, f)
                    if os.path.isfile(fp):
                        try:
                            items.append({"path": fp, "size": os.path.getsize(fp)})
                        except (PermissionError, OSError):
                            continue
        return items

    def _scan_prefetch(self, drive: str) -> List[Dict[str, Any]]:
        pf = os.path.join(drive + "\\", "Windows", "Prefetch")
        return self._dir_size(pf)

    def _scan_old_windows(self, drive: str) -> List[Dict[str, Any]]:
        items = []
        old = os.path.join(drive + "\\", "Windows.old")
        if os.path.exists(old):
            sz = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fn in os.walk(old) for f in fn if os.path.isfile(os.path.join(dp, f)))
            items.append({"path": old, "size": sz})
        return items

    def clean_category(self, category_name: str, drive: str = "C:") -> Dict[str, Any]:
        mapping = {
            "Temp Files": ("TEMP", ["%TEMP%"]),
            "Windows Temp": ("WinTemp", [drive + "\\Windows\\Temp"]),
            "Browser Cache": ("Browser", [
                os.path.join(os.path.expanduser("~"), "AppData", "Local", "Google", "Chrome", "User Data", "Default", "Cache"),
                os.path.join(os.path.expanduser("~"), "AppData", "Local", "Microsoft", "Edge", "User Data", "Default", "Cache"),
            ]),
            "System Logs": ("Logs", [drive + "\\Windows\\Logs"]),
            "Windows Update": ("WindowsUpdate", [drive + "\\Windows\\SoftwareDistribution\\Download"]),
            "Crash Dumps": ("Dumps", [
                os.path.join(os.path.expanduser("~"), "AppData", "Local", "CrashDumps"),
                drive + "\\Windows\\Minidump",
            ]),
            "Thumbnails": ("Thumbnails", [os.path.join(os.path.expanduser("~"), "AppData", "Local", "Microsoft", "Windows", "Explorer")]),
            "Prefetch": ("Prefetch", [drive + "\\Windows\\Prefetch"]),
            "Old Windows": ("OldWindows", [drive + "\\Windows.old"]),
        }
        if category_name not in mapping:
            return {"success": False, "message": f"Unknown category: {category_name}"}

        _, paths = mapping[category_name]
        cleaned = 0
        freed = 0
        for path in paths:
            if not os.path.exists(path):
                continue
            try:
                for f in os.listdir(path):
                    fp = os.path.join(path, f)
                    try:
                        if os.path.isfile(fp):
                            freed += os.path.getsize(fp)
                            os.remove(fp)
                        elif os.path.isdir(fp):
                            freed += sum(os.path.getsize(os.path.join(dp, fn)) for dp, _, fns in os.walk(fp) for fn in fns if os.path.isfile(os.path.join(dp, fn)))
                            import shutil
                            shutil.rmtree(fp, ignore_errors=True)
                        cleaned += 1
                    except (PermissionError, OSError):
                        continue
            except Exception:
                pass
        return {"success": True, "message": f"Cleaned {cleaned} items ({freed // (1024*1024)} MB freed)"}

    def clean_all(self, drive: str = "C:") -> Dict[str, Any]:
        results = []
        categories = ["Temp Files", "Windows Temp", "Browser Cache", "System Logs",
                      "Windows Update", "Crash Dumps", "Thumbnails", "Prefetch"]
        for cat in categories:
            results.append(self.clean_category(cat, drive))
        try:
            subprocess.run(["powershell", "-Command", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"],
                           capture_output=True, timeout=30)
            results.append({"success": True, "message": "Recycle Bin emptied"})
        except Exception:
            pass
        return {"success": True, "results": results}
