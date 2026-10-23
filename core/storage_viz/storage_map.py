import os
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict
from ..config import CONFIG
from ..logger import get_logger

logger = get_logger(__name__)

SKIP_DIRS = {
    "WinSxS", "Installer", "$Recycle.Bin", "System Volume Information",
    "Recovery", "Config.Msi", "Windows.old", "$Windows.~WS",
    "$WinREAgent", "MSOCache", "Intel", "PerfLogs",
}

CATEGORY_MAP = {
    "System": {"exts": {"sys", "dll", "exe", "mui", "cat", "msu", "ocx", "cpl", "drv", "dat", "bin"}, "color": "#e74c3c"},
    "Media": {"exts": {"mp4", "avi", "mkv", "mov", "wmv", "flv", "mp3", "wav", "flac", "wma", "aac", "jpg", "jpeg", "png", "gif", "bmp", "webp", "svg", "raw", "psd", "tiff", "ico", "heic", "heif", "webm", "m4a", "ogg", "opus"}, "color": "#9b59b6"},
    "Documents": {"exts": {"pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "rtf", "odt", "csv", "epub", "mobi", "md", "log", "msg", "eml", "pages", "numbers", "key"}, "color": "#3498db"},
    "Archives": {"exts": {"zip", "rar", "7z", "tar", "gz", "bz2", "iso", "img", "cab", "xz", "lz", "lzma", "zst", "arj", "lzh"}, "color": "#f39c12"},
    "Applications": {"exts": {"msi", "appx", "appxbundle", "deb", "rpm", "apk", "dmg", "pkg", "exe"}, "color": "#2ecc71"},
    "Code": {"exts": {"py", "js", "ts", "html", "css", "scss", "java", "cpp", "c", "h", "hpp", "cs", "go", "rs", "rb", "php", "sql", "json", "xml", "yaml", "toml", "sh", "bat", "ps1", "swift", "kt", "dart", "lua", "scala", "hs"}, "color": "#1abc9c"},
    "Other": {"exts": set(), "color": "#95a5a6"},
}


def _get_category_color(category: str) -> str:
    return CATEGORY_MAP.get(category, CATEGORY_MAP["Other"])["color"]


def _categorize_extension(ext: str) -> str:
    ext = ext.lower().lstrip(".")
    if not ext:
        return "Other"
    for cat_name, cat_info in CATEGORY_MAP.items():
        if ext in cat_info["exts"]:
            return cat_name
    return "Other"


class StorageMapAnalyzer:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._results: Optional[Dict] = None
        self._scanning = False
        self._cancel_event = threading.Event()
        self._scan_thread: Optional[threading.Thread] = None

    @property
    def is_scanning(self) -> bool:
        return self._scanning

    @property
    def results(self) -> Optional[Dict]:
        return self._results

    def analyze_drive(self, drive: str = "C:\\", max_depth: int = 5, max_folders: int = 5000) -> Dict:
        self._scanning = True
        self._cancel_event.clear()
        start = time.perf_counter()

        drive_path = Path(drive).resolve()
        drive_root = str(drive_path)[:2]

        try:
            usage = self._get_drive_usage(drive_root)
            total = usage["total"]
            free = usage["free"]
        except Exception:
            total = 0
            free = 0

        scanned = [0]
        tree = self._build_tree(
            path=str(drive_path),
            depth=0,
            max_depth=max_depth,
            max_folders=max_folders,
            folder_count=scanned,
        )
        truncated = scanned[0] >= max_folders

        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

        largest_files = self._gather_largest(tree, "files", 100)
        largest_folders = self._gather_largest(tree, "folders", 100)
        ext_breakdown = self._gather_extension_breakdown(tree)
        file_type_chart = self._gather_file_type_chart(ext_breakdown)

        result = {
            "drive": drive_root,
            "total_size": total,
            "free_space": free,
            "used_space": total - free,
            "scan_time_ms": elapsed_ms,
            "scanning": False,
            # The UI shows a "partial scan" notice instead of implying a
            # complete picture of the drive.
            "truncated": truncated,
            "folder_limit": max_folders,
            "tree": tree,
            "largest_files": largest_files,
            "largest_folders": largest_folders,
            "extension_breakdown": ext_breakdown,
            "file_type_chart": file_type_chart,
        }

        self._results = result
        self._scanning = False
        return result

    def start_scan(self, drive: str = "C:\\", callback=None):
        if self._scanning:
            logger.warning("Scan already in progress")
            return

        def _run():
            try:
                results = self.analyze_drive(drive=drive)
                if callback:
                    callback(results)
            except Exception as e:
                logger.error(f"Scan failed: {e}")
                self._scanning = False

        self._scan_thread = threading.Thread(target=_run, daemon=True)
        self._scan_thread.start()

    def get_results(self) -> Optional[Dict]:
        return self._results

    def cancel_scan(self):
        self._cancel_event.set()

    def _get_drive_usage(self, drive_root: str) -> Dict:
        try:
            usage = os.statvfs(drive_root) if hasattr(os, "statvfs") else None
            if usage:
                total = usage.f_frsize * usage.f_blocks
                free = usage.f_frsize * usage.f_bfree
            else:
                import ctypes
                free_bytes = ctypes.c_ulonglong(0)
                total_bytes = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    ctypes.c_wchar_p(drive_root),
                    None,
                    ctypes.byref(total_bytes),
                    ctypes.byref(free_bytes),
                )
                total = total_bytes.value
                free = free_bytes.value
            return {"total": total, "free": free}
        except Exception:
            return {"total": 0, "free": 0}

    def _build_tree(self, path: str, depth: int, max_depth: int, max_folders: int, folder_count: List[int]) -> Optional[Dict]:
        if self._cancel_event.is_set():
            return None

        if folder_count[0] >= max_folders:
            return self._aggregate_dir(path)

        name = os.path.basename(path) or path
        node: Dict = {
            "path": path,
            "name": name,
            "size": 0,
            "is_dir": True,
            "file_count": 0,
            "folder_count": 0,
            "children": [],
        }

        try:
            with os.scandir(path) as entries:
                for entry in entries:
                    if self._cancel_event.is_set():
                        return None

                    try:
                        if entry.is_dir(follow_symlinks=False):
                            if entry.name in SKIP_DIRS:
                                skipped_sz = self._skip_dir_size(entry.path)
                                node["size"] += skipped_sz
                                node["folder_count"] += 1
                                child = {
                                    "path": entry.path,
                                    "name": entry.name,
                                    "size": skipped_sz,
                                    "is_dir": True,
                                    "file_count": 0,
                                    "folder_count": 0,
                                }
                                node["children"].append(child)
                                continue

                            folder_count[0] += 1

                            if depth < max_depth:
                                child = self._build_tree(
                                    path=entry.path,
                                    depth=depth + 1,
                                    max_depth=max_depth,
                                    max_folders=max_folders,
                                    folder_count=folder_count,
                                )
                            else:
                                child = self._aggregate_dir(entry.path)

                            if child is not None:
                                node["size"] += child["size"]
                                node["file_count"] += child.get("file_count", 0)
                                node["folder_count"] += 1 + child.get("folder_count", 0)
                                node["children"].append(child)

                        elif entry.is_file(follow_symlinks=False):
                            try:
                                fsize = entry.stat(follow_symlinks=False).st_size
                            except (OSError, AttributeError):
                                fsize = 0

                            ext = os.path.splitext(entry.name)[1].lstrip(".").lower()
                            category = _categorize_extension(ext)
                            child = {
                                "path": entry.path,
                                "name": entry.name,
                                "size": fsize,
                                "is_dir": False,
                                "extension": ext,
                                "category": category,
                                "category_color": _get_category_color(category),
                            }
                            node["size"] += fsize
                            node["file_count"] += 1
                            node["children"].append(child)

                    except (PermissionError, OSError):
                        continue
        except (PermissionError, OSError) as e:
            logger.debug(f"Cannot scan {path}: {e}")
            return None

        node["children"].sort(key=lambda c: c.get("size", 0), reverse=True)
        return node

    def _aggregate_dir(self, path: str) -> Dict:
        name = os.path.basename(path) or path
        node: Dict = {
            "path": path,
            "name": name,
            "size": 0,
            "is_dir": True,
            "file_count": 0,
            "folder_count": 0,
        }

        try:
            for root, dirs, files in os.walk(path):
                if self._cancel_event.is_set():
                    break

                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

                for f in files:
                    try:
                        fp = os.path.join(root, f)
                        node["size"] += os.path.getsize(fp)
                        node["file_count"] += 1
                    except (OSError, PermissionError):
                        continue

                node["folder_count"] += len(dirs)
        except (PermissionError, OSError):
            pass

        return node

    def _skip_dir_size(self, path: str) -> int:
        try:
            total = 0
            count = 0
            with os.scandir(path) as entries:
                for entry in entries:
                    try:
                        if entry.is_file(follow_symlinks=False):
                            total += entry.stat(follow_symlinks=False).st_size
                            count += 1
                    except (OSError, PermissionError):
                        continue
            return total
        except (PermissionError, OSError):
            return 0

    def _gather_largest(self, tree: Optional[Dict], kind: str, limit: int) -> List[Dict]:
        if tree is None:
            return []

        items = []
        stack = [tree]

        while stack:
            node = stack.pop()
            if not node.get("is_dir"):
                continue
            children = node.get("children", [])
            for child in children:
                if child.get("is_dir"):
                    if kind == "folders":
                        items.append({
                            "path": child["path"],
                            "size": child["size"],
                            "file_count": child.get("file_count", 0),
                            "folder_count": child.get("folder_count", 0),
                        })
                    stack.append(child)
                else:
                    if kind == "files":
                        items.append({
                            "path": child["path"],
                            "size": child["size"],
                            "extension": child.get("extension", ""),
                            "category": child.get("category", "Other"),
                        })

        items.sort(key=lambda x: x["size"], reverse=True)
        return items[:limit]

    def _gather_extension_breakdown(self, tree: Optional[Dict]) -> Dict:
        if tree is None:
            return {}

        breakdown = defaultdict(lambda: {"count": 0, "size": 0})
        stack = [tree]

        while stack:
            node = stack.pop()
            children = node.get("children", [])
            for child in children:
                if child.get("is_dir"):
                    stack.append(child)
                else:
                    ext = child.get("extension", "") or "none"
                    breakdown[ext]["count"] += 1
                    breakdown[ext]["size"] += child["size"]

        return dict(sorted(breakdown.items(), key=lambda x: x[1]["size"], reverse=True))

    def _gather_file_type_chart(self, ext_breakdown: Dict) -> Dict:
        chart = {}
        for cat_name in CATEGORY_MAP:
            chart[cat_name] = {"size": 0, "count": 0, "color": CATEGORY_MAP[cat_name]["color"]}

        for ext, data in ext_breakdown.items():
            cat = _categorize_extension(ext)
            chart[cat]["size"] += data["size"]
            chart[cat]["count"] += data["count"]

        return {k: v for k, v in chart.items() if v["count"] > 0 or v["size"] > 0}


storage_map_analyzer = StorageMapAnalyzer()
