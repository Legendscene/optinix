import os
import subprocess
import shutil
import tempfile
import time
from typing import List, Dict

class DiskTools:
    def __init__(self, os_type: str = "windows"):
        self.os_type = os_type
    
    def defragment(self, drive: str = "C:") -> Dict:
        """Defragment HDD or optimize SSD."""
        try:
            if self.os_type == "windows":
                r = subprocess.run(["defrag", drive, "/O", "/V"], capture_output=True, text=True, timeout=300)
                return {"success": True, "message": f"Drive {drive} optimized", "output": r.stdout[:500]}
            return {"success": False, "message": "Defrag only supported on Windows"}
        except subprocess.TimeoutExpired:
            return {"success": False, "message": "Defrag timed out"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def trim(self, drive: str = "C:") -> Dict:
        """Manually TRIM an SSD."""
        try:
            if self.os_type == "windows":
                r = subprocess.run(["defrag", drive, "/L"], capture_output=True, text=True, timeout=60)
                return {"success": True, "message": f"TRIM command sent to {drive}", "output": r.stdout[:300]}
            elif self.os_type == "linux":
                r = subprocess.run(["sudo", "fstrim", "-v", "/"], capture_output=True, text=True, timeout=60)
                return {"success": True, "message": f"TRIM: {r.stdout.strip()}"}
            return {"success": False, "message": "TRIM not supported on this OS"}
        except subprocess.TimeoutExpired:
            return {"success": False, "message": "TRIM timed out"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def shred_file(self, path: str, passes: int = 3) -> Dict:
        """Securely delete a file by overwriting it."""
        if not os.path.exists(path):
            return {"success": False, "message": "File not found"}
        try:
            size = os.path.getsize(path)
            with open(path, "wb") as f:
                for p in range(passes):
                    f.seek(0)
                    if p % 3 == 0:
                        f.write(os.urandom(size))
                    elif p % 3 == 1:
                        f.write(b'\x00' * size)
                    else:
                        f.write(b'\xFF' * size)
                    f.flush()
                    os.fsync(f.fileno())
            os.remove(path)
            return {"success": True, "message": f"File shredded and deleted ({passes} passes)", "size": size}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def shred_folder(self, path: str, passes: int = 3) -> Dict:
        """Securely delete all files in a folder."""
        if not os.path.exists(path):
            return {"success": False, "message": "Folder not found"}
        total = 0
        errors = 0
        for root, dirs, files in os.walk(path):
            for f in files:
                try:
                    self.shred_file(os.path.join(root, f), passes)
                    total += 1
                except:
                    errors += 1
        return {"success": True, "message": f"Shredded {total} files ({errors} errors)"}
    
    def get_drive_info(self, drive: str = "C:") -> Dict:
        """Get detailed drive info including whether it's SSD/HDD."""
        info = {"drive": drive}
        try:
            import psutil
            usage = psutil.disk_usage(drive + "\\")
            info.update({
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "percent": usage.percent
            })
        except:
            pass
        try:
            r = subprocess.run(["wmic", "diskdrive", "where", f"DeviceID='\\\\\\.\\PHYSICALDRIVE0'", "get", "Model,Size,MediaType"],
                              capture_output=True, text=True, timeout=10)
            lines = r.stdout.strip().split("\n")
            if len(lines) > 1:
                parts = lines[1].strip().split()
                info["model"] = parts[0] if parts else ""
                info["is_ssd"] = "SSD" in r.stdout or "Solid State" in r.stdout
        except:
            pass
        return info
