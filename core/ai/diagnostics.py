import os
import re
import time
import platform
import subprocess
from datetime import datetime, timedelta
from typing import Dict, Any, List


class SystemDiagnostics:
    def __init__(self):
        self._is_windows = platform.system() == "Windows"

    def run_diagnostics(self) -> Dict[str, Any]:
        results = {}

        results["boot_time"] = self._get_boot_time()
        results["startup_processes"] = self._get_startup_processes()
        results["running_services"] = self._get_running_services_count()
        results["disk_errors"] = self._get_disk_errors()
        results["memory_errors"] = self._get_memory_errors()
        results["driver_issues"] = self._get_driver_issues()
        results["windows_update_status"] = self._get_windows_update_status()
        results["last_scan_times"] = self._get_last_scan_times()
        results["timestamp"] = time.time()

        return results

    def _get_boot_time(self) -> Dict[str, Any]:
        try:
            import psutil
            bt = psutil.boot_time()
            bt_dt = datetime.fromtimestamp(bt)
            uptime = datetime.now() - bt_dt
            return {
                "last_boot": bt_dt.isoformat(),
                "uptime_seconds": int(uptime.total_seconds()),
                "uptime_days": round(uptime.total_seconds() / 86400, 2),
                "uptime_hours": round(uptime.total_seconds() / 3600, 1),
            }
        except:
            return {
                "last_boot": None,
                "uptime_seconds": -1,
                "uptime_days": -1,
                "uptime_hours": -1,
            }

    def _get_startup_processes(self) -> Dict[str, Any]:
        if not self._is_windows:
            return {"count": 0, "processes": []}
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-CimInstance Win32_StartupCommand | Select-Object Name, Command, Location, User | ConvertTo-Json -Compress"],
                capture_output=True, text=True, timeout=10,
            )
            import json
            items = []
            if r.stdout.strip():
                parsed = json.loads(r.stdout.strip())
                if isinstance(parsed, list):
                    items = parsed
                elif isinstance(parsed, dict):
                    items = [parsed]
            return {
                "count": len(items),
                "processes": [{"name": i.get("Name", "Unknown"), "command": i.get("Command", ""), "location": i.get("Location", ""), "user": i.get("User", "")} for i in items],
            }
        except:
            return {"count": -1, "processes": []}

    def _get_running_services_count(self) -> int:
        try:
            import psutil
            count = 0
            for p in psutil.process_iter(['pid', 'name']):
                try:
                    pinfo = p.info
                    if pinfo.get('name') and pinfo['name'].endswith('.exe'):
                        count += 1
                except:
                    pass
            return count
        except:
            return -1

    def _get_disk_errors(self) -> List[Dict[str, Any]]:
        if not self._is_windows:
            return []
        errors = []
        try:
            r = subprocess.run(
                ["wevtutil", "qe", "System", "/q:*[System[(EventID=7 or EventID=11 or EventID=15) and TimeCreated[timediff(@SystemTime) <= 604800000]]]", "/c:20", "/f:text"],
                capture_output=True, text=True, timeout=15,
            )
            lines = r.stdout.strip().split("\n")
            current = {}
            for line in lines:
                line = line.strip()
                if line.startswith("Event ID:"):
                    current["event_id"] = line.split(":", 1)[1].strip()
                elif line.startswith("Time Created:"):
                    current["time"] = line.split(":", 1)[1].strip()
                elif line.startswith("Message:"):
                    current["message"] = line.split(":", 1)[1].strip()[:200]
                    if current.get("event_id"):
                        errors.append(dict(current))
                    current = {}
            if not errors and r.stdout.strip():
                errors.append({"source": "wevtutil", "raw": r.stdout.strip()[:300]})
        except:
            try:
                r = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     "Get-WinEvent -FilterHashtable @{LogName='System'; ID=7,11,15} -MaxEvents 10 -ErrorAction SilentlyContinue | ForEach-Object { [PSCustomObject]@{Time=$_.TimeCreated; ID=$_.Id; Message=$_.Message} } | ConvertTo-Json -Compress"],
                    capture_output=True, text=True, timeout=15,
                )
                import json
                if r.stdout.strip():
                    parsed = json.loads(r.stdout.strip())
                    items = parsed if isinstance(parsed, list) else [parsed]
                    errors = [{"time": str(e.get("Time", "")), "event_id": e.get("ID", ""), "message": str(e.get("Message", ""))[:200]} for e in items if isinstance(e, dict)]
            except:
                pass
        return errors

    def _get_memory_errors(self) -> List[Dict[str, Any]]:
        if not self._is_windows:
            return []
        errors = []
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-WinEvent -FilterHashtable @{LogName='System'; ID=20,39,51,137} -MaxEvents 10 -ErrorAction SilentlyContinue | ForEach-Object { [PSCustomObject]@{Time=$_.TimeCreated; ID=$_.Id; Message=$_.Message} } | ConvertTo-Json -Compress"],
                capture_output=True, text=True, timeout=10,
            )
            import json
            if r.stdout.strip():
                parsed = json.loads(r.stdout.strip())
                items = parsed if isinstance(parsed, list) else [parsed]
                errors = [{"time": str(e.get("Time", "")), "event_id": e.get("ID", ""), "message": str(e.get("Message", ""))[:200]} for e in items if isinstance(e, dict)]
        except:
            pass
        return errors

    def _get_driver_issues(self) -> List[Dict[str, Any]]:
        if not self._is_windows:
            return []
        issues = []
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-WinEvent -FilterHashtable @{LogName='System'; ID=45,46,47} -MaxEvents 10 -ErrorAction SilentlyContinue | ForEach-Object { [PSCustomObject]@{Time=$_.TimeCreated; ID=$_.Id; Message=$_.Message} } | ConvertTo-Json -Compress"],
                capture_output=True, text=True, timeout=10,
            )
            import json
            if r.stdout.strip():
                parsed = json.loads(r.stdout.strip())
                items = parsed if isinstance(parsed, list) else [parsed]
                issues = [{"time": str(e.get("Time", "")), "event_id": e.get("ID", ""), "message": str(e.get("Message", ""))[:200]} for e in items if isinstance(e, dict)]
        except:
            pass

        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-CimInstance Win32_PnPEntity | Where-Object { $_.ConfigManagerErrorCode -ne 0 } | Select-Object Name, DeviceID, ConfigManagerErrorCode, Status | ConvertTo-Json -Compress"],
                capture_output=True, text=True, timeout=10,
            )
            import json
            if r.stdout.strip() and r.stdout.strip() != "null":
                parsed = json.loads(r.stdout.strip())
                items = parsed if isinstance(parsed, list) else [parsed]
                for item in items:
                    if isinstance(item, dict):
                        issues.append({
                            "type": "problem_device",
                            "device": item.get("Name", "Unknown"),
                            "device_id": item.get("DeviceID", ""),
                            "error_code": item.get("ConfigManagerErrorCode", -1),
                            "status": item.get("Status", "Unknown"),
                        })
        except:
            pass

        return issues

    def _get_windows_update_status(self) -> Dict[str, Any]:
        if not self._is_windows:
            return {"update_pending": False, "details": "Not applicable"}
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "$updates = Get-WUList -IsInstalled 0 -ErrorAction SilentlyContinue; if ($updates) { @{Pending=$true; Count=@($updates).Count; Titles=($updates | Select-Object -First 5 -ExpandProperty Title) -join '; '} } else { @{Pending=$false; Count=0} } | ConvertTo-Json -Compress"],
                capture_output=True, text=True, timeout=30,
            )
            import json
            if r.stdout.strip():
                parsed = json.loads(r.stdout.strip())
                return {
                    "update_pending": parsed.get("Pending", False),
                    "pending_count": parsed.get("Count", 0),
                    "titles": parsed.get("Titles", "").split("; ") if parsed.get("Titles") else [],
                }
        except:
            pass

        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "$s = New-Object -ComObject Microsoft.Update.Session; $s.CreateUpdateSearcher().Search('IsInstalled=0').Updates | Select-Object -ExpandProperty Title -First 5"],
                capture_output=True, text=True, timeout=30,
            )
            titles = [l.strip() for l in r.stdout.strip().split("\n") if l.strip()]
            return {
                "update_pending": len(titles) > 0,
                "pending_count": len(titles),
                "titles": titles,
            }
        except:
            return {"update_pending": None, "pending_count": -1, "titles": []}

    def _get_last_scan_times(self) -> Dict[str, Any]:
        sfc_result = self._get_last_sfc_time()
        dism_result = self._get_last_dism_time()
        return {
            "sfc": sfc_result,
            "dism": dism_result,
            "defender": self._get_last_defender_scan_time(),
        }

    def _get_last_sfc_time(self) -> Dict[str, Any]:
        if not self._is_windows:
            return {"last_scan": None, "found": False}
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Microsoft-Windows-Wininit'} -MaxEvents 1 -ErrorAction SilentlyContinue | Where-Object { $_.Message -like '*SFC*' } | Select-Object -First 1).TimeCreated.ToString('o')"],
                capture_output=True, text=True, timeout=10,
            )
            scan_time = r.stdout.strip()
            if scan_time:
                return {"last_scan": scan_time, "found": True}
        except:
            pass

        try:
            r = subprocess.run(
                ["wevtutil", "qe", "System", "/q:*[System[Provider[@Name='Microsoft-Windows-Wininit']]]", "/c:1", "/f:text"],
                capture_output=True, text=True, timeout=10,
            )
            for line in r.stdout.split("\n"):
                if "SFC" in line or "Time Created" in line:
                    pass
            return {"last_scan": None, "found": False}
        except:
            return {"last_scan": None, "found": False}

    def _get_last_dism_time(self) -> Dict[str, Any]:
        if not self._is_windows:
            return {"last_scan": None, "found": False}
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-WinEvent -FilterHashtable @{LogName='Windows PowerShell'; ProviderName='PowerShell'} -MaxEvents 10 -ErrorAction SilentlyContinue | Where-Object { $_.Message -like '*DISM*' -or $_.Message -like '*dism*' } | Select-Object -First 1).TimeCreated.ToString('o')"],
                capture_output=True, text=True, timeout=10,
            )
            scan_time = r.stdout.strip()
            if scan_time:
                return {"last_scan": scan_time, "found": True}
        except:
            pass

        try:
            log_path = os.environ.get("WINDIR", "C:\\Windows") + "\\Logs\\DISM\\dism.log"
            if os.path.exists(log_path):
                mtime = os.path.getmtime(log_path)
                return {"last_scan": datetime.fromtimestamp(mtime).isoformat(), "found": True}
        except:
            pass

        return {"last_scan": None, "found": False}

    def _get_last_defender_scan_time(self) -> Dict[str, Any]:
        if not self._is_windows:
            return {"last_scan": None, "found": False}
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "$m = Get-MpComputerStatus; $scan = $m.QuickScanEndTime; if ($scan) { $scan.ToString('o') } else { 'Never' }"],
                capture_output=True, text=True, timeout=10,
            )
            scan_time = r.stdout.strip()
            return {"last_scan": scan_time if scan_time and scan_time != "Never" else None, "found": scan_time is not None and scan_time != "Never"}
        except:
            return {"last_scan": None, "found": False}

    def check_driver_health(self) -> List[Dict[str, Any]]:
        if not self._is_windows:
            return [{"driver": "N/A", "status": "unknown", "message": "Driver health check only supported on Windows"}]

        results = []
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-WindowsDriver -Online -ErrorAction SilentlyContinue | Select-Object Driver, ProviderName, Version, ClassName, Date, BootCritical, OriginalFileName | ConvertTo-Json -Compress"],
                capture_output=True, text=True, timeout=60,
            )
            import json
            if r.stdout.strip():
                parsed = json.loads(r.stdout.strip())
                items = parsed if isinstance(parsed, list) else [parsed]
                for item in items[:30]:
                    try:
                        driver = item.get("Driver", "Unknown") if isinstance(item, dict) else "Unknown"
                        provider = item.get("ProviderName", "Unknown") if isinstance(item, dict) else "Unknown"
                        version = item.get("Version", "Unknown") if isinstance(item, dict) else "Unknown"
                        results.append({
                            "driver": driver,
                            "provider": provider,
                            "version": version,
                            "status": "online",
                        })
                    except:
                        pass
        except:
            pass

        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-CimInstance Win32_SystemDriver | Select-Object Name, State, Status, StartMode, PathName | ConvertTo-Json -Compress"],
                capture_output=True, text=True, timeout=15,
            )
            import json
            if r.stdout.strip():
                parsed = json.loads(r.stdout.strip())
                items = parsed if isinstance(parsed, list) else [parsed]
                for item in items:
                    try:
                        state = item.get("State", "Unknown") if isinstance(item, dict) else "Unknown"
                        status = item.get("Status", "Unknown") if isinstance(item, dict) else "Unknown"
                        if state != "Running" or status != "OK":
                            results.append({
                                "driver": item.get("Name", "Unknown") if isinstance(item, dict) else "Unknown",
                                "state": state,
                                "status": status,
                                "start_mode": item.get("StartMode", ""),
                                "issue": f"Driver in state '{state}' with status '{status}'",
                            })
                    except:
                        pass
        except:
            pass

        if not results:
            results.append({"driver": "No drivers found", "status": "unknown", "message": "Unable to query driver information"})

        return results

    def check_windows_integrity(self) -> Dict[str, Any]:
        if not self._is_windows:
            return {
                "healthy": None,
                "message": "Windows integrity check only supported on Windows",
                "dism_output": "",
                "component_store_clean": None,
            }

        try:
            r = subprocess.run(
                ["dism", "/online", "/cleanup-image", "/checkhealth"],
                capture_output=True, text=True, timeout=120,
            )
            output = r.stdout
            returncode = r.returncode

            healthy = "No component store corruption detected" in output
            repairable = "repairable" in output.lower()
            corrupted = "corruption" in output.lower() and not healthy

            return {
                "healthy": healthy,
                "repairable": repairable,
                "corrupted": corrupted,
                "return_code": returncode,
                "dism_output": output.strip()[:500],
                "message": "Component store is healthy" if healthy else "Component store corruption detected" if corrupted else "Component store has repairable issues" if repairable else "Unknown state",
                "component_store_clean": healthy,
            }
        except FileNotFoundError:
            return {
                "healthy": None,
                "message": "DISM not available on this system",
                "dism_output": "",
                "component_store_clean": None,
            }
        except Exception as e:
            return {
                "healthy": None,
                "message": f"Error running DISM: {str(e)}",
                "dism_output": "",
                "component_store_clean": None,
            }


DiagnosticsAnalyzer = SystemDiagnostics
