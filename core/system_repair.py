import os
import subprocess
import time
import json
from typing import List, Dict

class SystemRepair:
    """System repair utilities - SFC, DISM, startup timing."""
    
    def __init__(self, os_type: str = "windows"):
        self.os_type = os_type
    
    def sfc_scan(self) -> Dict:
        """Run System File Checker."""
        try:
            r = subprocess.run(["sfc", "/scannow"], capture_output=True, text=True, timeout=600)
            success = "did not find any integrity violations" in r.stdout or "Windows Resource Protection found corrupt files and successfully repaired them" in r.stdout
            return {"success": success, "message": "SFC completed", "output": r.stdout[-500:] if r.stdout else r.stderr[-500:]}
        except subprocess.TimeoutExpired:
            return {"success": False, "message": "SFC scan timed out (takes 10-15 min)"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def dism_restore(self) -> Dict:
        """Run DISM to restore system health."""
        try:
            r = subprocess.run(["dism", "/online", "/cleanup-image", "/restorehealth"],
                              capture_output=True, text=True, timeout=600)
            success = "restoration completed" in r.stdout.lower() or "no component store corruption detected" in r.stdout.lower()
            return {"success": success, "message": "DISM completed", "output": r.stdout[-500:] if r.stdout else r.stderr[-500:]}
        except subprocess.TimeoutExpired:
            return {"success": False, "message": "DISM timed out"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def check_disk(self, drive: str = "C:") -> Dict:
        """Run chkdsk on a drive."""
        try:
            r = subprocess.run(["chkdsk", drive, "/scan"], capture_output=True, text=True, timeout=120)
            return {"success": True, "message": "Disk check completed", "output": r.stdout[-300:]}
        except subprocess.TimeoutExpired:
            return {"success": False, "message": "Disk check timed out"}
        except Exception as e:
            return {"success": False, "message": str(e)}


class StartupTimer:
    """Measure boot times and startup impact."""
    
    def get_startup_times(self) -> Dict:
        """Get last boot time and startup impact from Windows."""
        try:
            r = subprocess.run(
                ["powershell", "-Command", 
                 "Get-Process -Name * | Sort-Object -Property StartTime | Select-Object -First 20 Name,Id,StartTime,CPU | ConvertTo-Json"],
                capture_output=True, text=True, timeout=10
            )
            processes = []
            if r.stdout.strip():
                data = json.loads(r.stdout)
                if isinstance(data, dict):
                    data = [data]
                for p in data[:20]:
                    if p.get("StartTime"):
                        processes.append({
                            "name": p.get("Name", ""),
                            "pid": p.get("Id", 0),
                            "start_time": p.get("StartTime", ""),
                            "cpu": p.get("CPU", 0)
                        })
            
            # Get boot time
            boot = subprocess.run(["wmic", "os", "get", "LastBootUpTime"], capture_output=True, text=True, timeout=5)
            boot_time = boot.stdout.strip().split("\n")[-1].strip() if boot.stdout.strip() else ""
            
            # Get system uptime
            import psutil
            uptime_seconds = time.time() - psutil.boot_time()
            
            return {
                "uptime_seconds": int(uptime_seconds),
                "uptime_formatted": f"{int(uptime_seconds//86400)}d {int((uptime_seconds%86400)//3600)}h {int((uptime_seconds%3600)//60)}m",
                "boot_time": boot_time,
                "startup_processes": processes[:10],
                "total_startup_processes": len(processes)
            }
        except Exception as e:
            return {"error": str(e)}


class ContextMenuManager:
    """Manage Windows context menu entries."""
    
    def get_items(self) -> List[Dict]:
        """List context menu items from registry."""
        items = []
        paths = [
            r"HKCR\*\shell",
            r"HKCR\Directory\shell",
            r"HKCR\Directory\Background\shell",
            r"HKCU\Software\Classes\*\shell",
        ]
        for reg_path in paths:
            try:
                r = subprocess.run(["reg", "query", reg_path, "/s", "/e"], capture_output=True, text=True, timeout=10)
                lines = r.stdout.split("\n")
                current = {}
                for line in lines:
                    line = line.strip()
                    if line.startswith("HKEY_"):
                        key_name = line.split("\\")[-1]
                        current = {"key": line, "name": key_name, "command": "", "location": reg_path}
                    elif "MUIVerb" in line and "REG_SZ" in line:
                        current["name"] = line.split("REG_SZ")[-1].strip()
                    elif "command" in line.lower() and "REG_SZ" in line:
                        current["command"] = line.split("REG_SZ")[-1].strip()
                    elif not line and current.get("name"):
                        items.append(current)
                        current = {}
            except:
                pass
        return items[:30]  # Limit
    
    def disable_item(self, key_path: str) -> Dict:
        """Disable a context menu item (add deny permission)."""
        try:
            subprocess.run(["reg", "add", key_path, "/v", "LegacyDisable", "/t", "REG_SZ", "/d", "1", "/f"],
                          capture_output=True, timeout=5)
            return {"success": True, "message": "Context menu item disabled"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def enable_item(self, key_path: str) -> Dict:
        """Re-enable a context menu item."""
        try:
            subprocess.run(["reg", "delete", key_path, "/v", "LegacyDisable", "/f"],
                          capture_output=True, timeout=5)
            return {"success": True, "message": "Context menu item enabled"}
        except Exception as e:
            return {"success": False, "message": str(e)}
