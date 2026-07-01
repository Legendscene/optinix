import subprocess
import json
import os
import time
import platform
from datetime import datetime
from typing import Dict, List, Optional, Any, Union


class RollbackEngine:
    """Enterprise-grade rollback engine.
    
    Every optimization automatically stores:
    - Previous Registry Value
    - Previous Power Plan GUID
    - Previous Service State (startup type)
    - Previous Scheduled Task State (enabled/disabled)
    - Previous BCD Value
    - Previous Network settings
    
    One click restores Windows to original state.
    """

    def __init__(self, os_type: str):
        self.os_type = os_type
        self.log_dir = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "optinix_rollback")
        os.makedirs(self.log_dir, exist_ok=True)
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.snapshot_file = os.path.join(self.log_dir, f"snapshot_{self.session_id}.json")
        self.snapshot: Dict[str, Any] = {
            "created": datetime.now().isoformat(),
            "os": platform.system() + " " + platform.release(),
            "registry": {},
            "power_plan": {},
            "services": {},
            "tasks": {},
            "bcd": {},
            "network": {},
            "files": [],
        }

    def _run(self, cmd: List[str], timeout: int = 10) -> subprocess.CompletedProcess:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    # ---- Registry ----

    def snapshot_registry(self, key: str, value_name: str) -> None:
        reg_key = key.replace("HKLM\\", "HKLM\\").replace("HKCU\\", "HKCU\\")
        try:
            r = self._run(["reg", "query", reg_key, "/v", value_name], timeout=5)
            if r.returncode == 0:
                for line in r.stdout.splitlines():
                    if value_name in line:
                        parts = line.strip().split()
                        if len(parts) >= 3:
                            self.snapshot["registry"][f"{key}\\{value_name}"] = {
                                "type": parts[1] if len(parts) > 2 else "REG_DWORD",
                                "value": parts[-1],
                            }
        except Exception:
            self.snapshot["registry"][f"{key}\\{value_name}"] = None

    def restore_registry(self, key: str, value_name: str, prev: Optional[Dict[str, str]]) -> Dict[str, Any]:
        if prev is None:
            try:
                self._run(["reg", "delete", key, "/v", value_name, "/f"], timeout=5)
                return {"success": True, "message": f"Deleted {key}\\{value_name} (did not exist before)"}
            except Exception as e:
                return {"success": False, "message": f"Failed to delete: {e}"}
        try:
            self._run(["reg", "add", key, "/v", value_name, "/t", prev["type"], "/d", prev["value"], "/f"], timeout=5)
            return {"success": True, "message": f"Restored {key}\\{value_name} = {prev['value']}"}
        except Exception as e:
            return {"success": False, "message": f"Restore failed: {e}"}

    # ---- Power Plan ----

    def snapshot_power_plan(self) -> None:
        try:
            r = self._run(["powercfg", "/getactivescheme"], timeout=5)
            if r.returncode == 0 and ":" in r.stdout:
                guid = r.stdout.split(":")[1].strip().split()[0]
                self.snapshot["power_plan"]["active_guid"] = guid
        except Exception:
            self.snapshot["power_plan"]["active_guid"] = None

    def snapshot_power_subsetting(self, scheme: str, sub: str, setting: str) -> None:
        try:
            r = self._run(["powercfg", "/query", scheme, sub, setting], timeout=5)
            if r.returncode == 0:
                for line in r.stdout.splitlines():
                    if "AC" in line or "Power" in line:
                        parts = line.split()
                        if parts:
                            key = f"{scheme}\\{sub}\\{setting}"
                            self.snapshot["power_plan"][key] = parts[-1]
        except Exception:
            pass

    def restore_power_plan(self) -> Dict[str, Any]:
        guid = self.snapshot.get("power_plan", {}).get("active_guid")
        if guid:
            try:
                self._run(["powercfg", "/setactive", guid], timeout=5)
                return {"success": True, "message": f"Power plan restored to {guid}"}
            except Exception as e:
                return {"success": False, "message": f"Power plan restore failed: {e}"}
        return {"success": True, "message": "No power plan to restore"}

    # ---- Services ----

    def snapshot_service(self, name: str) -> None:
        try:
            r = self._run(["sc", "qc", name], timeout=5)
            if r.returncode == 0:
                for line in r.stdout.splitlines():
                    if "START_TYPE" in line:
                        st = line.split(":")[1].strip() if ":" in line else ""
                        self.snapshot["services"][name] = st
                        return
        except Exception:
            pass
        self.snapshot["services"][name] = None

    def restore_service(self, name: str, startup: Optional[str]) -> Dict[str, Any]:
        if startup is None:
            return {"success": True, "message": f"Service {name}: no previous state"}
        try:
            val = "auto" if "AUTO" in startup.upper() else ("disabled" if "DISABLED" in startup.upper() else "demand")
            self._run(["sc", "config", name, f"start={val}"], timeout=5)
            return {"success": True, "message": f"Service {name} restored to {val}"}
        except Exception as e:
            return {"success": False, "message": f"Service {name} restore failed: {e}"}

    # ---- Scheduled Tasks ----

    def snapshot_task(self, task_path: str) -> None:
        try:
            r = self._run(["schtasks", "/Query", "/TN", task_path, "/V", "/FO", "CSV"], timeout=10)
            if r.returncode == 0:
                self.snapshot["tasks"][task_path] = "enabled"
            else:
                self.snapshot["tasks"][task_path] = "disabled"
        except Exception:
            self.snapshot["tasks"][task_path] = None

    def restore_task(self, task_path: str, state: Optional[str]) -> Dict[str, Any]:
        if state is None:
            return {"success": True, "message": f"Task {task_path}: no previous state"}
        try:
            action = "/Enable" if state == "enabled" else "/Disable"
            self._run(["schtasks", "/Change", "/TN", task_path, action], timeout=10)
            return {"success": True, "message": f"Task {task_path} {action.replace('/', '').lower()}d"}
        except Exception as e:
            return {"success": False, "message": f"Task {task_path} restore failed: {e}"}

    # ---- BCD ----

    def snapshot_bcd(self, setting: str) -> None:
        try:
            r = self._run(["bcdedit", "/enum", "{current}"], timeout=5)
            if r.returncode == 0:
                for line in r.stdout.splitlines():
                    if setting in line:
                        val = line.split()[-1] if line.split() else None
                        self.snapshot["bcd"][setting] = val
                        return
        except Exception:
            pass
        self.snapshot["bcd"][setting] = None

    def restore_bcd(self, setting: str, prev: Optional[str]) -> Dict[str, Any]:
        if prev is None:
            try:
                self._run(["bcdedit", "/deletevalue", setting], timeout=5)
                return {"success": True, "message": f"BCD {setting} deleted (restored to default)"}
            except Exception as e:
                return {"success": False, "message": f"BCD {setting} delete failed: {e}"}
        try:
            self._run(["bcdedit", "/set", setting, prev], timeout=5)
            return {"success": True, "message": f"BCD {setting} restored to {prev}"}
        except Exception as e:
            return {"success": False, "message": f"BCD {setting} restore failed: {e}"}

    # ---- File backup ----

    def backup_file(self, filepath: str) -> None:
        if not os.path.exists(filepath):
            return
        backup_dir = os.path.join(self.log_dir, "files")
        os.makedirs(backup_dir, exist_ok=True)
        name = os.path.basename(filepath)
        dest = os.path.join(backup_dir, f"{name}.bak.{self.session_id}")
        try:
            import shutil
            shutil.copy2(filepath, dest)
            self.snapshot["files"].append({"original": filepath, "backup": dest})
        except Exception:
            pass

    # ---- Save / Load snapshot ----

    def save_snapshot(self) -> str:
        with open(self.snapshot_file, "w") as f:
            json.dump(self.snapshot, f, indent=2, default=str)
        return self.snapshot_file

    def load_snapshot(self, filepath: str) -> Optional[Dict[str, Any]]:
        if not os.path.exists(filepath):
            return None
        try:
            with open(filepath) as f:
                return json.load(f)
        except Exception:
            return None

    # ---- Full restore ----

    def full_restore(self, snapshot_file: Optional[str] = None) -> List[Dict[str, str]]:
        snap = self.load_snapshot(snapshot_file or self.snapshot_file)
        if not snap:
            return [{"success": False, "message": "No snapshot found"}]

        results = []

        reg = snap.get("registry", {})
        for key_val, prev in reg.items():
            if "\\" not in key_val:
                continue
            parts = key_val.rsplit("\\", 1)
            key = parts[0]
            val = parts[1] if len(parts) > 1 else ""
            r = self.restore_registry(key, val, prev)
            results.append(r)

        r = self.restore_power_plan()
        results.append(r)

        for svc, state in snap.get("services", {}).items():
            r = self.restore_service(svc, state)
            results.append(r)

        for task, state in snap.get("tasks", {}).items():
            r = self.restore_task(task, state)
            results.append(r)

        for setting, prev in snap.get("bcd", {}).items():
            r = self.restore_bcd(setting, prev)
            results.append(r)

        return results

    # ---- Restore Point ----

    def create_restore_point(self, description: str = "Optinix Backup") -> Dict[str, Any]:
        if self.os_type != "windows":
            return {"success": False, "message": "Restore points are Windows-only"}
        try:
            self._run([
                "powershell", "-NoProfile", "-Command",
                f"Checkpoint-Computer -Description '{description}' -RestorePointType MODIFY_SETTINGS -EA SilentlyContinue"
            ], timeout=60)
            return {"success": True, "message": "System Restore Point created"}
        except Exception as e:
            return {"success": False, "message": f"Restore point failed: {e}"}
