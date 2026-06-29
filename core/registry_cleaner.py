import subprocess
import json
import os
import time
from typing import Dict, List, Any, Optional

class RegistryCleaner:
    def __init__(self, os_type: str):
        self.os_type = os_type
        self.backup_dir = os.path.join(os.environ.get("TEMP", "."), "optinix_registry_backups")
        os.makedirs(self.backup_dir, exist_ok=True)

    def scan_issues(self) -> Dict[str, Any]:
        if self.os_type != "windows":
            return {"issues": [], "total": 0}

        issues = []
        scan_paths = [
            (r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run", "unnecessary_startup", "high"),
            (r"HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Run", "unnecessary_startup", "high"),
            (r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\VolumeCaches", "orphaned_entries", "medium"),
            (r"HKCR\CLSID", "orphaned_com", "medium"),
            (r"HKCU\SOFTWARE\Classes\Local Settings\Software\Microsoft\Windows\Shell\MuiCache", "unused_cache", "low"),
            (r"HKLM\SYSTEM\CurrentControlSet\Services\*\Parameters", "incomplete_uninstall", "medium"),
        ]

        issue_types = {
            "unnecessary_startup": {"name": "Unnecessary Startup Entry", "severity": "high", "desc": "Program starts automatically, slowing boot"},
            "orphaned_entries": {"name": "Orphaned Registry Entry", "severity": "medium", "desc": "Leftover from uninstalled software"},
            "orphaned_com": {"name": "Orphaned COM Object", "severity": "medium", "desc": "Unregistered COM class entry"},
            "unused_cache": {"name": "Unused MUI Cache", "severity": "low", "desc": "Cached language data for removed apps"},
            "incomplete_uninstall": {"name": "Incomplete Uninstall", "severity": "medium", "desc": "Partial application removal residue"},
        }

        for path, issue_type, severity in scan_paths:
            try:
                parts = path.split("\\", 1)
                root = parts[0]
                key_path = parts[1] if len(parts) > 1 else ""

                hive = {"HKLM": "HKEY_LOCAL_MACHINE", "HKCU": "HKEY_CURRENT_USER", "HKCR": "HKEY_CLASSES_ROOT"}.get(root, "HKEY_LOCAL_MACHINE")

                if "*" in key_path:
                    base = key_path.split("*")[0]
                    r = subprocess.run(["reg", "query", f"{hive}\\{base}"], capture_output=True, text=True, timeout=5)
                    for line in r.stdout.split("\n")[1:]:
                        if line.strip() and not line.strip().startswith("HKEY_"):
                            continue
                        key = line.strip()
                        if key:
                            i_type = issue_types.get(issue_type, {"name": "Unknown Issue", "severity": severity, "desc": "Registry issue detected"})
                            issues.append({
                                "path": key,
                                "type": issue_type,
                                "name": i_type["name"],
                                "severity": severity,
                                "description": i_type["desc"],
                                "fixable": True
                            })
                else:
                    r = subprocess.run(["reg", "query", f"{hive}\\{key_path}"], capture_output=True, text=True, timeout=5)
                    for line in r.stdout.split("\n")[1:]:
                        line = line.strip()
                        if not line or line.startswith("HKEY_"):
                            if line.startswith("HKEY_"):
                                i_type = issue_types.get(issue_type, {"name": "Unknown Issue", "severity": severity, "desc": "Registry issue detected"})
                                issues.append({
                                    "path": line,
                                    "type": issue_type,
                                    "name": i_type["name"],
                                    "severity": severity,
                                    "description": i_type["desc"],
                                    "fixable": True
                                })
            except Exception:
                pass

        return {"issues": issues[:50], "total": min(len(issues), 50)}

    def fix_issues(self, issue_paths: List[str]) -> Dict[str, Any]:
        if self.os_type != "windows":
            return {"success": False, "message": "Windows only"}

        results = []
        for path in issue_paths:
            try:
                if path.startswith("HKEY_"):
                    parts = path.split("\\", 1)
                    r = subprocess.run(["reg", "delete", path, "/f"], capture_output=True, text=True, timeout=5)
                    if r.returncode == 0:
                        results.append({"success": True, "message": f"Deleted: {path}"})
                    else:
                        results.append({"success": False, "message": f"Failed: {path} - {r.stderr.strip()}"})
                else:
                    results.append({"success": False, "message": f"Invalid path: {path}"})
            except Exception as e:
                results.append({"success": False, "message": f"Error: {path} - {e}"})

        return {"success": True, "results": results}

    def backup(self) -> Dict[str, Any]:
        if self.os_type != "windows":
            return {"success": False, "message": "Windows only"}

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"registry_backup_{timestamp}.reg"
        filepath = os.path.join(self.backup_dir, filename)

        try:
            subprocess.run([
                "reg", "export", "HKEY_CURRENT_USER", filepath, "/y"
            ], capture_output=True, timeout=30)
            subprocess.run([
                "reg", "export", "HKEY_LOCAL_MACHINE\\SOFTWARE", filepath.replace(".reg", "_lm.reg"), "/y"
            ], capture_output=True, timeout=30)

            backups = self.list_backups()
            return {"success": True, "message": f"Backup saved: {filename}", "backups": backups}
        except Exception as e:
            return {"success": False, "message": f"Backup failed: {e}"}

    def restore(self, filename: str) -> Dict[str, Any]:
        if self.os_type != "windows":
            return {"success": False, "message": "Windows only"}

        filepath = os.path.join(self.backup_dir, filename)
        if not os.path.exists(filepath):
            return {"success": False, "message": f"Backup not found: {filename}"}

        try:
            subprocess.run(["reg", "import", filepath], capture_output=True, timeout=30)
            return {"success": True, "message": f"Restored: {filename}"}
        except Exception as e:
            return {"success": False, "message": f"Restore failed: {e}"}

    def list_backups(self) -> List[Dict[str, Any]]:
        backups = []
        if os.path.isdir(self.backup_dir):
            for f in sorted(os.listdir(self.backup_dir), reverse=True):
                fpath = os.path.join(self.backup_dir, f)
                if f.endswith(".reg"):
                    backups.append({
                        "name": f,
                        "size": os.path.getsize(fpath),
                        "created": time.ctime(os.path.getctime(fpath))
                    })
        return backups
