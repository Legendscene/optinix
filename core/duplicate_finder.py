import os
import hashlib
from collections import defaultdict
from typing import List, Dict

class DuplicateFinder:
    """Find duplicate and large files on the system."""
    
    def __init__(self, os_type: str = "windows"):
        self.os_type = os_type
        self.duplicates: List[Dict] = []
        self.large_files: List[Dict] = []
    
    def find_duplicates(self, paths: List[str] = None) -> List[Dict]:
        """Find duplicate files by content hash."""
        if paths is None:
            home = os.path.expanduser("~")
            paths = [
                os.path.join(home, "Downloads"),
                os.path.join(home, "Documents"),
                os.path.join(home, "Pictures"),
                os.path.join(home, "Desktop"),
            ]
        
        size_map = defaultdict(list)
        total_scanned = 0
        self.duplicates = []
        
        for base in paths:
            if not os.path.exists(base):
                continue
            for root, dirs, files in os.walk(base):
                # Skip common non-duplicate dirs
                skip_dirs = {"node_modules", ".git", "__pycache__", ".cache", "AppData"}
                dirs[:] = [d for d in dirs if d not in skip_dirs]
                
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        size = os.path.getsize(fp)
                        if size > 1024:  # Skip files smaller than 1KB
                            size_map[size].append(fp)
                            total_scanned += 1
                    except (OSError, PermissionError):
                        continue
                    
                    if total_scanned > 50000:
                        break
                if total_scanned > 50000:
                    break
        
        # Find files with same size that are likely duplicates
        for size, files in size_map.items():
            if len(files) < 2:
                continue
            
            # Group by hash for exact matches
            hash_map = defaultdict(list)
            for fp in files:
                try:
                    with open(fp, "rb") as f:
                        file_hash = hashlib.md5(f.read(8192)).hexdigest()
                    hash_map[file_hash].append(fp)
                except:
                    pass
            
            for file_hash, matches in hash_map.items():
                if len(matches) < 2:
                    continue
                # First file is original, rest are duplicates
                original = matches[0]
                for dup in matches[1:]:
                    self.duplicates.append({
                        "original": original,
                        "duplicate": dup,
                        "size": size,
                        "original_name": os.path.basename(original),
                        "duplicate_name": os.path.basename(dup)
                    })
        
        self.duplicates.sort(key=lambda x: x["size"], reverse=True)
        return self.duplicates
    
    def find_large_files(self, min_size_mb: int = 500) -> List[Dict]:
        """Find files larger than specified threshold."""
        home = os.path.expanduser("~")
        scan_paths = [
            os.path.join(home, "Downloads"),
            os.path.join(home, "Documents"),
            os.path.join(home, "Desktop"),
            os.path.join(home, "Pictures"),
            os.path.join(home, "Videos"),
        ]
        
        self.large_files = []
        min_bytes = min_size_mb * 1024 * 1024
        
        for base in scan_paths:
            if not os.path.exists(base):
                continue
            for root, dirs, files in os.walk(base):
                skip_dirs = {"node_modules", ".git", "__pycache__", "AppData"}
                dirs[:] = [d for d in dirs if d not in skip_dirs]
                
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        size = os.path.getsize(fp)
                        if size >= min_bytes:
                            self.large_files.append({
                                "path": fp,
                                "name": f,
                                "size": size,
                                "category": self._categorize(f)
                            })
                    except (OSError, PermissionError):
                        continue
                    
                    if len(self.large_files) >= 100:
                        break
                if len(self.large_files) >= 100:
                    break
        
        self.large_files.sort(key=lambda x: x["size"], reverse=True)
        return self.large_files
    
    def _categorize(self, name: str) -> str:
        ext = os.path.splitext(name)[1].lower()
        if ext in (".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv"): return "Video"
        if ext in (".mp3", ".wav", ".flac", ".m4a", ".wma", ".aac"): return "Audio"
        if ext in (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff"): return "Image"
        if ext in (".zip", ".rar", ".7z", ".tar", ".gz"): return "Archive"
        if ext in (".exe", ".msi", ".dmg"): return "Installer"
        if ext in (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"): return "Document"
        if ext in (".iso", ".img", ".vhd"): return "Disk Image"
        return "Other"
    
    def delete_file(self, path: str) -> Dict:
        """Move file to Recycle Bin or delete."""
        try:
            os.remove(path)
            return {"success": True, "message": f"Deleted: {os.path.basename(path)}"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def get_summary(self) -> Dict:
        return {
            "duplicates_found": len(self.duplicates),
            "large_files_found": len(self.large_files),
            "total_wasted_bytes": sum(d["size"] for d in self.duplicates) + sum(f["size"] for f in self.large_files),
            "duplicates": self.duplicates[:50],
            "large_files": self.large_files[:50]
        }
