import os
import subprocess
import re
import platform
from typing import Dict, List, Optional, Any
from ..config import CONFIG
from ..logger import get_logger


class SystemTools:
    TOOLS = {
        "services": "services.msc",
        "task_scheduler": "taskschd.msc",
        "event_viewer": "eventvwr.msc",
        "registry_editor": "regedit.exe",
        "device_manager": "devmgmt.msc",
        "disk_management": "diskmgmt.msc",
        "windows_features": "optionalfeatures.exe",
        "system_properties": "sysdm.cpl",
        "network_connections": "ncpa.cpl",
        "power_options": "powercfg.cpl",
        "performance_monitor": "perfmon.msc",
        "resource_monitor": "resmon.exe",
        "system_configuration": "msconfig.exe",
        "computer_management": "compmgmt.msc",
        "defender_firewall": "wf.msc",
        "local_security_policy": "secpol.msc",
        "print_management": "printmanagement.msc",
        "disk_cleanup": "cleanmgr.exe",
        "directx_diagnostic": "dxdiag.exe",
        "system_information": "msinfo32.exe",
    }

    HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts"
    _HOSTS_LINE_RE = re.compile(r'^\s*(#)?\s*(\S+)\s+(.+?)(?:\s*#\s*(.*))?\s*$')

    def __init__(self):
        self.logger = get_logger("system_tools")
        self._admin_cache: Optional[bool] = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_admin(self) -> bool:
        if self._admin_cache is not None:
            return self._admin_cache
        try:
            import ctypes
            self._admin_cache = ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            self._admin_cache = False
        return self._admin_cache

    def _run_powershell(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
                capture_output=True, text=True, timeout=timeout
            )
            return {"success": r.returncode == 0, "stdout": r.stdout.strip(), "stderr": r.stderr.strip()}
        except subprocess.TimeoutExpired:
            return {"success": False, "stdout": "", "stderr": "Command timed out"}
        except Exception as e:
            self.logger.error(f"PowerShell error: {e}")
            return {"success": False, "stdout": "", "stderr": str(e)}

    def _run_cmd(self, command: List[str], timeout: int = 30) -> Dict[str, Any]:
        try:
            flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            r = subprocess.run(
                command, capture_output=True, text=True, timeout=timeout, creationflags=flags
            )
            return {"success": r.returncode == 0, "stdout": r.stdout.strip(), "stderr": r.stderr.strip()}
        except subprocess.TimeoutExpired:
            return {"success": False, "stdout": "", "stderr": "Command timed out"}
        except Exception as e:
            self.logger.error(f"Command error: {e}")
            return {"success": False, "stdout": "", "stderr": str(e)}

    def _ensure_admin(self, action: str = "perform this action") -> None:
        if not self._is_admin():
            raise PermissionError(f"Administrator privileges required to {action}")

    # ------------------------------------------------------------------
    # Environment Variables
    # ------------------------------------------------------------------

    def list_environment_variables(self, scope: str = "both") -> Dict:
        try:
            result: Dict[str, Any] = {"success": True, "message": "Environment variables retrieved", "data": {}}

            if scope in ("user", "both"):
                ps_cmd = (
                    "$vars = [Environment]::GetEnvironmentVariables('User'); "
                    "$vars.Keys | ForEach-Object { [PSCustomObject]@{Name=$_; Value=$vars[$_]} } | ConvertTo-Json"
                )
                r = self._run_powershell(ps_cmd)
                if r["success"] and r["stdout"]:
                    import json
                    items = json.loads(r["stdout"])
                    if isinstance(items, dict):
                        items = [items]
                    result["data"]["user"] = {item["Name"]: item["Value"] for item in items}
                else:
                    result["data"]["user"] = {}

            if scope in ("system", "both"):
                ps_cmd = (
                    "$vars = [Environment]::GetEnvironmentVariables('Machine'); "
                    "$vars.Keys | ForEach-Object { [PSCustomObject]@{Name=$_; Value=$vars[$_]} } | ConvertTo-Json"
                )
                r = self._run_powershell(ps_cmd)
                if r["success"] and r["stdout"]:
                    import json
                    items = json.loads(r["stdout"])
                    if isinstance(items, dict):
                        items = [items]
                    result["data"]["system"] = {item["Name"]: item["Value"] for item in items}
                else:
                    result["data"]["system"] = {}

            return result
        except Exception as e:
            self.logger.error(f"list_environment_variables failed: {e}")
            return {"success": False, "message": str(e), "data": {}}

    def get_environment_variable(self, name: str, scope: str = "user") -> Dict:
        try:
            ps_scope = "User" if scope == "user" else "Machine"
            ps_cmd = f"[Environment]::GetEnvironmentVariable('{name}', '{ps_scope}')"
            r = self._run_powershell(ps_cmd)
            if r["success"]:
                value = r["stdout"] if r["stdout"] else ""
                return {"success": True, "message": f"Variable '{name}' retrieved", "data": {"name": name, "value": value, "scope": scope}}
            return {"success": False, "message": f"Failed to get variable '{name}'", "data": {}}
        except Exception as e:
            self.logger.error(f"get_environment_variable failed: {e}")
            return {"success": False, "message": str(e), "data": {}}

    def set_environment_variable(self, name: str, value: str, scope: str = "user") -> Dict:
        try:
            if scope == "system":
                self._ensure_admin("set system environment variables")

            ps_scope = "User" if scope == "user" else "Machine"
            safe_value = value.replace("'", "''")
            ps_cmd = f"[Environment]::SetEnvironmentVariable('{name}', '{safe_value}', '{ps_scope}')"
            r = self._run_powershell(ps_cmd)
            if r["success"]:
                if scope == "user":
                    os.environ[name] = value
                return {"success": True, "message": f"Variable '{name}' set successfully", "data": {"name": name, "value": value, "scope": scope}}
            return {"success": False, "message": f"Failed to set variable '{name}'", "data": {}}
        except PermissionError as e:
            return {"success": False, "message": str(e), "data": {}}
        except Exception as e:
            self.logger.error(f"set_environment_variable failed: {e}")
            return {"success": False, "message": str(e), "data": {}}

    def delete_environment_variable(self, name: str, scope: str = "user") -> Dict:
        try:
            if scope == "system":
                self._ensure_admin("delete system environment variables")

            ps_scope = "User" if scope == "user" else "Machine"
            ps_cmd = f"[Environment]::SetEnvironmentVariable('{name}', $null, '{ps_scope}')"
            r = self._run_powershell(ps_cmd)
            if r["success"]:
                os.environ.pop(name, None)
                return {"success": True, "message": f"Variable '{name}' deleted", "data": {"name": name, "scope": scope}}
            return {"success": False, "message": f"Failed to delete variable '{name}'", "data": {}}
        except PermissionError as e:
            return {"success": False, "message": str(e), "data": {}}
        except Exception as e:
            self.logger.error(f"delete_environment_variable failed: {e}")
            return {"success": False, "message": str(e), "data": {}}

    # ------------------------------------------------------------------
    # Hosts File Editor
    # ------------------------------------------------------------------

    def get_hosts_file(self) -> Dict:
        try:
            if not os.path.exists(self.HOSTS_PATH):
                return {"success": False, "message": "Hosts file not found", "data": {"entries": [], "raw": ""}}

            with open(self.HOSTS_PATH, "r") as f:
                raw = f.read()

            entries = []
            for i, line in enumerate(raw.splitlines(), start=1):
                stripped = line.strip()
                if not stripped:
                    continue

                m = self._HOSTS_LINE_RE.match(line)
                if m:
                    is_commented = bool(m.group(1))
                    ip = m.group(2)
                    hostnames = m.group(3).strip().split()
                    comment = (m.group(4) or "").strip()

                    entries.append({
                        "ip": ip,
                        "hostnames": hostnames,
                        "comment": comment,
                        "enabled": not is_commented,
                        "line_number": i,
                    })
                else:
                    entries.append({
                        "ip": "",
                        "hostnames": [],
                        "comment": stripped.lstrip("#").strip(),
                        "enabled": False,
                        "line_number": i,
                    })

            return {"success": True, "message": "Hosts file read successfully", "data": {"entries": entries, "raw": raw}}
        except Exception as e:
            self.logger.error(f"get_hosts_file failed: {e}")
            return {"success": False, "message": str(e), "data": {"entries": [], "raw": ""}}

    def add_hosts_entry(self, ip: str, hostname: str, comment: str = "") -> Dict:
        try:
            self._ensure_admin("edit the hosts file")

            if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
                return {"success": False, "message": f"Invalid IP address: {ip}", "data": {}}
            if not hostname or not re.match(r'^[\w\.\-]+$', hostname):
                return {"success": False, "message": f"Invalid hostname: {hostname}", "data": {}}

            comment_part = f" # {comment}" if comment else ""
            entry_line = f"{ip} {hostname}{comment_part}\n"

            with open(self.HOSTS_PATH, "a") as f:
                f.write(entry_line)

            return {"success": True, "message": f"Hosts entry added: {ip} {hostname}", "data": {"ip": ip, "hostname": hostname}}
        except PermissionError as e:
            return {"success": False, "message": str(e), "data": {}}
        except Exception as e:
            self.logger.error(f"add_hosts_entry failed: {e}")
            return {"success": False, "message": str(e), "data": {}}

    def remove_hosts_entry(self, line_number: int) -> Dict:
        try:
            self._ensure_admin("edit the hosts file")

            if not os.path.exists(self.HOSTS_PATH):
                return {"success": False, "message": "Hosts file not found", "data": {}}

            with open(self.HOSTS_PATH, "r") as f:
                lines = f.readlines()

            if line_number < 1 or line_number > len(lines):
                return {"success": False, "message": f"Line {line_number} out of range (1-{len(lines)})", "data": {}}

            removed = lines[line_number - 1].strip()
            lines.pop(line_number - 1)

            with open(self.HOSTS_PATH, "w") as f:
                f.writelines(lines)

            return {"success": True, "message": f"Line {line_number} removed", "data": {"line_number": line_number, "content": removed}}
        except PermissionError as e:
            return {"success": False, "message": str(e), "data": {}}
        except Exception as e:
            self.logger.error(f"remove_hosts_entry failed: {e}")
            return {"success": False, "message": str(e), "data": {}}

    def toggle_hosts_entry(self, line_number: int) -> Dict:
        try:
            self._ensure_admin("edit the hosts file")

            if not os.path.exists(self.HOSTS_PATH):
                return {"success": False, "message": "Hosts file not found", "data": {}}

            with open(self.HOSTS_PATH, "r") as f:
                lines = f.readlines()

            if line_number < 1 or line_number > len(lines):
                return {"success": False, "message": f"Line {line_number} out of range (1-{len(lines)})", "data": {}}

            line = lines[line_number - 1]
            stripped = line.lstrip()

            if stripped.startswith("#"):
                new_line = line.replace("#", "", 1)
                action = "uncommented"
            else:
                new_line = "#" + line
                action = "commented"

            lines[line_number - 1] = new_line

            with open(self.HOSTS_PATH, "w") as f:
                f.writelines(lines)

            return {"success": True, "message": f"Line {line_number} {action}", "data": {"line_number": line_number, "enabled": action == "uncommented"}}
        except PermissionError as e:
            return {"success": False, "message": str(e), "data": {}}
        except Exception as e:
            self.logger.error(f"toggle_hosts_entry failed: {e}")
            return {"success": False, "message": str(e), "data": {}}

    # ------------------------------------------------------------------
    # Launch System Tools
    # ------------------------------------------------------------------

    def launch_tool(self, tool_name: str) -> Dict:
        try:
            if tool_name not in self.TOOLS:
                available = ", ".join(sorted(self.TOOLS.keys()))
                return {"success": False, "message": f"Unknown tool '{tool_name}'. Available: {available}", "data": {}}

            tool_file = self.TOOLS[tool_name]
            system32 = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "System32")
            full_path = os.path.join(system32, tool_file)

            flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0

            if os.path.exists(full_path):
                cmd = [full_path]
            else:
                cmd = [tool_file]

            ext = os.path.splitext(tool_file)[1].lower() if "." in tool_file else ""
            if ext == ".msc":
                mmc_path = os.path.join(system32, "mmc.exe")
                if os.path.exists(mmc_path):
                    cmd = [mmc_path, cmd[0]]

            subprocess.Popen(cmd, creationflags=flags, shell=False)

            return {"success": True, "message": f"Launched {tool_name} ({tool_file})", "data": {"tool": tool_name, "command": tool_file}}
        except Exception as e:
            self.logger.error(f"launch_tool failed: {e}")
            return {"success": False, "message": str(e), "data": {}}

    # ------------------------------------------------------------------
    # Group Policy
    # ------------------------------------------------------------------

    def open_group_policy_editor(self) -> Dict:
        try:
            gpedit_path = os.path.join(
                os.environ.get("SystemRoot", "C:\\Windows"), "System32", "gpedit.msc"
            )
            if not os.path.exists(gpedit_path):
                return {"success": False, "message": "Group Policy Editor is not available on this edition of Windows (requires Pro/Enterprise)", "data": {}}

            flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            subprocess.Popen(["mmc.exe", gpedit_path], creationflags=flags)

            return {"success": True, "message": "Group Policy Editor launched", "data": {}}
        except Exception as e:
            self.logger.error(f"open_group_policy_editor failed: {e}")
            return {"success": False, "message": str(e), "data": {}}

    def check_group_policy_available(self) -> bool:
        try:
            gpedit_path = os.path.join(
                os.environ.get("SystemRoot", "C:\\Windows"), "System32", "gpedit.msc"
            )
            return os.path.exists(gpedit_path)
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Active Processes
    # ------------------------------------------------------------------

    def list_processes(self, sort_by: str = "memory", limit: int = 50) -> Dict:
        try:
            import psutil

            processes = []
            for proc in psutil.process_iter(["pid", "name", "memory_info", "cpu_percent", "status", "create_time", "username", "exe"]):
                try:
                    info = proc.info
                    processes.append({
                        "pid": info["pid"],
                        "name": info["name"] or "Unknown",
                        "memory_mb": round(info["memory_info"].rss / (1024 * 1024), 2) if info["memory_info"] else 0,
                        "cpu_percent": info["cpu_percent"] or 0.0,
                        "status": info["status"] or "unknown",
                        "created": info["create_time"],
                        "username": info["username"] or "",
                        "exe": info["exe"] or "",
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            sort_key = "memory_mb" if sort_by == "memory" else "cpu_percent" if sort_by == "cpu" else "name"
            reverse = sort_key != "name"
            processes.sort(key=lambda p: p.get(sort_key, 0) if isinstance(p.get(sort_key, 0), (int, float)) else str(p.get(sort_key, "")), reverse=reverse)

            if limit is None:
                limit = 50
            if limit > 0:
                processes = processes[:limit]

            return {"success": True, "message": f"{len(processes)} processes listed", "data": {"processes": processes, "total": len(processes), "sort_by": sort_by, "limit": limit}}
        except ImportError:
            return {"success": False, "message": "psutil is required for process management", "data": {"processes": []}}
        except Exception as e:
            self.logger.error(f"list_processes failed: {e}")
            return {"success": False, "message": str(e), "data": {"processes": []}}

    def kill_process(self, pid: int) -> Dict:
        try:
            import psutil
            proc = psutil.Process(pid)
            proc.terminate()
            proc.wait(timeout=10)
            return {"success": True, "message": f"Process {pid} terminated", "data": {"pid": pid, "name": proc.name()}}
        except psutil.NoSuchProcess:
            return {"success": False, "message": f"Process {pid} not found", "data": {}}
        except psutil.AccessDenied:
            return {"success": False, "message": f"Access denied to terminate process {pid}", "data": {}}
        except psutil.TimeoutExpired:
            try:
                proc.kill()
                return {"success": True, "message": f"Process {pid} forcefully killed", "data": {"pid": pid}}
            except Exception:
                return {"success": False, "message": f"Process {pid} did not terminate in time", "data": {}}
        except ImportError:
            return {"success": False, "message": "psutil is required for process management", "data": {}}
        except Exception as e:
            self.logger.error(f"kill_process failed: {e}")
            return {"success": False, "message": str(e), "data": {}}

    def get_process_details(self, pid: int) -> Dict:
        try:
            import psutil
            proc = psutil.Process(pid)
            with proc.oneshot():
                mem = proc.memory_info()
                details = {
                    "pid": pid,
                    "name": proc.name(),
                    "exe": proc.exe(),
                    "cwd": proc.cwd(),
                    "status": proc.status(),
                    "username": proc.username(),
                    "created": proc.create_time(),
                    "cpu_percent": proc.cpu_percent(interval=0.1),
                    "memory_rss_mb": round(mem.rss / (1024 * 1024), 2),
                    "memory_vms_mb": round(mem.vms / (1024 * 1024), 2),
                    "num_threads": proc.num_threads(),
                    "priority": proc.nice(),
                    "cmdline": " ".join(proc.cmdline()) if proc.cmdline() else "",
                }
            return {"success": True, "message": f"Details for PID {pid}", "data": details}
        except psutil.NoSuchProcess:
            return {"success": False, "message": f"Process {pid} not found", "data": {}}
        except psutil.AccessDenied:
            return {"success": False, "message": f"Access denied to process {pid}", "data": {}}
        except ImportError:
            return {"success": False, "message": "psutil is required for process management", "data": {}}
        except Exception as e:
            self.logger.error(f"get_process_details failed: {e}")
            return {"success": False, "message": str(e), "data": {}}

    # ------------------------------------------------------------------
    # Startup Manager
    # ------------------------------------------------------------------

    def list_startup_programs(self) -> Dict:
        try:
            ps_cmd = (
                "Get-CimInstance Win32_StartupCommand | "
                "Select-Object Name, Command, Location, User | ConvertTo-Json"
            )
            r = self._run_powershell(ps_cmd)
            programs = []
            if r["success"] and r["stdout"]:
                import json
                items = json.loads(r["stdout"])
                if isinstance(items, dict):
                    items = [items]
                for item in items:
                    programs.append({
                        "name": item.get("Name", "Unknown"),
                        "command": item.get("Command", ""),
                        "location": item.get("Location", ""),
                        "user": item.get("User", ""),
                    })

            reg_locations = [
                r"HKCU:\Software\Microsoft\Windows\CurrentVersion\Run",
                r"HKLM:\Software\Microsoft\Windows\CurrentVersion\Run",
                r"HKCU:\Software\Microsoft\Windows\CurrentVersion\RunOnce",
                r"HKLM:\Software\Microsoft\Windows\CurrentVersion\RunOnce",
            ]
            for reg_path in reg_locations:
                ps_cmd = f"Get-ItemProperty -Path '{reg_path}' -ErrorAction SilentlyContinue | Select-Object -ExcludeProperty PS* | ConvertTo-Json"
                r2 = self._run_powershell(ps_cmd)
                if r2["success"] and r2["stdout"] and r2["stdout"] != "null":
                    try:
                        import json
                        items = json.loads(r2["stdout"])
                        if isinstance(items, dict):
                            items = [items]
                        existing = {p["name"] for p in programs}
                        for item in items:
                            for key, val in item.items():
                                if key not in ("PSPath", "PSParentPath") and key not in existing:
                                    programs.append({
                                        "name": key,
                                        "command": str(val),
                                        "location": reg_path,
                                        "user": "System" if "HKLM" in reg_path else "Current User",
                                    })
                                    existing.add(key)
                    except json.JSONDecodeError:
                        pass

            return {"success": True, "message": f"{len(programs)} startup programs found", "data": {"programs": programs, "total": len(programs)}}
        except Exception as e:
            self.logger.error(f"list_startup_programs failed: {e}")
            return {"success": False, "message": str(e), "data": {"programs": []}}

    # ------------------------------------------------------------------
    # Windows Features (DISM)
    # ------------------------------------------------------------------

    def list_windows_features(self) -> Dict:
        try:
            self._ensure_admin("list Windows features")
            ps_cmd = "Get-WindowsOptionalFeature -Online | Select-Object FeatureName,State | ConvertTo-Json"
            r = self._run_powershell(ps_cmd, timeout=60)
            features = []
            if r["success"] and r["stdout"]:
                import json
                items = json.loads(r["stdout"])
                if isinstance(items, dict):
                    items = [items]
                for item in items:
                    features.append({
                        "name": item.get("FeatureName", ""),
                        "state": item.get("State", "Unknown"),
                    })
            return {"success": True, "message": f"{len(features)} Windows features found", "data": {"features": features, "total": len(features)}}
        except PermissionError as e:
            return {"success": False, "message": str(e), "data": {"features": []}}
        except Exception as e:
            self.logger.error(f"list_windows_features failed: {e}")
            return {"success": False, "message": str(e), "data": {"features": []}}

    def enable_windows_feature(self, name: str) -> Dict:
        try:
            self._ensure_admin("enable Windows features")
            ps_cmd = f"Enable-WindowsOptionalFeature -Online -FeatureName '{name}' -All -NoRestart -ErrorAction Stop"
            r = self._run_powershell(ps_cmd, timeout=300)
            if r["success"]:
                return {"success": True, "message": f"Feature '{name}' enabled (may require restart)", "data": {"feature": name, "action": "enabled"}}
            return {"success": False, "message": f"Failed to enable '{name}': {r['stderr']}", "data": {}}
        except PermissionError as e:
            return {"success": False, "message": str(e), "data": {}}
        except Exception as e:
            self.logger.error(f"enable_windows_feature failed: {e}")
            return {"success": False, "message": str(e), "data": {}}

    def disable_windows_feature(self, name: str) -> Dict:
        try:
            self._ensure_admin("disable Windows features")
            ps_cmd = f"Disable-WindowsOptionalFeature -Online -FeatureName '{name}' -NoRestart -ErrorAction Stop"
            r = self._run_powershell(ps_cmd, timeout=300)
            if r["success"]:
                return {"success": True, "message": f"Feature '{name}' disabled (may require restart)", "data": {"feature": name, "action": "disabled"}}
            return {"success": False, "message": f"Failed to disable '{name}': {r['stderr']}", "data": {}}
        except PermissionError as e:
            return {"success": False, "message": str(e), "data": {}}
        except Exception as e:
            self.logger.error(f"disable_windows_feature failed: {e}")
            return {"success": False, "message": str(e), "data": {}}

    # ------------------------------------------------------------------
    # Network Utilities
    # ------------------------------------------------------------------

    def flush_dns(self) -> Dict:
        try:
            r = self._run_cmd(["ipconfig", "/flushdns"])
            if r["success"]:
                return {"success": True, "message": "DNS cache flushed", "data": {}}
            return {"success": False, "message": f"DNS flush failed: {r['stderr']}", "data": {}}
        except Exception as e:
            self.logger.error(f"flush_dns failed: {e}")
            return {"success": False, "message": str(e), "data": {}}

    def renew_ip(self, adapter: str = None) -> Dict:
        try:
            self._ensure_admin("renew IP address")
            if adapter:
                r = self._run_cmd(["ipconfig", "/renew", adapter], timeout=120)
            else:
                r = self._run_cmd(["ipconfig", "/renew"], timeout=120)
            if r["success"]:
                return {"success": True, "message": "IP address renewed", "data": {"adapter": adapter or "all"}}
            return {"success": False, "message": f"IP renew failed: {r['stderr']}", "data": {}}
        except PermissionError as e:
            return {"success": False, "message": str(e), "data": {}}
        except Exception as e:
            self.logger.error(f"renew_ip failed: {e}")
            return {"success": False, "message": str(e), "data": {}}

    def release_ip(self, adapter: str = None) -> Dict:
        try:
            self._ensure_admin("release IP address")
            if adapter:
                r = self._run_cmd(["ipconfig", "/release", adapter], timeout=60)
            else:
                r = self._run_cmd(["ipconfig", "/release"], timeout=60)
            if r["success"]:
                return {"success": True, "message": "IP address released", "data": {"adapter": adapter or "all"}}
            return {"success": False, "message": f"IP release failed: {r['stderr']}", "data": {}}
        except PermissionError as e:
            return {"success": False, "message": str(e), "data": {}}
        except Exception as e:
            self.logger.error(f"release_ip failed: {e}")
            return {"success": False, "message": str(e), "data": {}}

    def reset_winsock(self) -> Dict:
        try:
            self._ensure_admin("reset Winsock")
            r = self._run_cmd(["netsh", "winsock", "reset"], timeout=30)
            if r["success"]:
                return {"success": True, "message": "Winsock reset successfully (restart may be required)", "data": {}}
            return {"success": False, "message": f"Winsock reset failed: {r['stderr']}", "data": {}}
        except PermissionError as e:
            return {"success": False, "message": str(e), "data": {}}
        except Exception as e:
            self.logger.error(f"reset_winsock failed: {e}")
            return {"success": False, "message": str(e), "data": {}}

    def reset_windows_firewall(self) -> Dict:
        try:
            self._ensure_admin("reset Windows Firewall")
            r = self._run_cmd(["netsh", "advfirewall", "reset"], timeout=30)
            if r["success"]:
                return {"success": True, "message": "Windows Firewall reset to defaults", "data": {}}
            return {"success": False, "message": f"Firewall reset failed: {r['stderr']}", "data": {}}
        except PermissionError as e:
            return {"success": False, "message": str(e), "data": {}}
        except Exception as e:
            self.logger.error(f"reset_windows_firewall failed: {e}")
            return {"success": False, "message": str(e), "data": {}}

    # ------------------------------------------------------------------
    # Shortcuts
    # ------------------------------------------------------------------

    def get_shortcut_info(self, path: str) -> Dict:
        try:
            if not os.path.exists(path):
                return {"success": False, "message": f"File not found: {path}", "data": {}}
            if not path.lower().endswith(".lnk"):
                return {"success": False, "message": "Not a .lnk shortcut file", "data": {}}

            safe_path = path.replace("'", "''")
            ps_cmd = (
                f"$ws = New-Object -ComObject WScript.Shell; "
                f"$sc = $ws.CreateShortcut('{safe_path}'); "
                f"@{'{'}"
                f"TargetPath = $sc.TargetPath; "
                f"Arguments = $sc.Arguments; "
                f"WorkingDirectory = $sc.WorkingDirectory; "
                f"IconLocation = $sc.IconLocation; "
                f"Hotkey = $sc.Hotkey; "
                f"WindowStyle = $sc.WindowStyle; "
                f"Description = $sc.Description"
                f"@{'}'} | ConvertTo-Json"
            )
            r = self._run_powershell(ps_cmd)
            if r["success"] and r["stdout"]:
                import json
                info = json.loads(r["stdout"])
                return {"success": True, "message": "Shortcut info retrieved", "data": {
                    "path": path,
                    "target_path": info.get("TargetPath", ""),
                    "arguments": info.get("Arguments", ""),
                    "working_directory": info.get("WorkingDirectory", ""),
                    "icon_location": info.get("IconLocation", ""),
                    "hotkey": info.get("Hotkey", ""),
                    "window_style": info.get("WindowStyle", 1),
                    "description": info.get("Description", ""),
                }}
            return {"success": False, "message": "Failed to read shortcut", "data": {}}
        except Exception as e:
            self.logger.error(f"get_shortcut_info failed: {e}")
            return {"success": False, "message": str(e), "data": {}}

    def create_shortcut(self, target: str, shortcut_path: str, args: str = "", working_dir: str = "", icon: str = "") -> Dict:
        try:
            if not shortcut_path.lower().endswith(".lnk"):
                shortcut_path += ".lnk"
            try:
                os.makedirs(os.path.dirname(os.path.abspath(shortcut_path)), exist_ok=True)
            except Exception:
                pass

            safe_target = target.replace("'", "''")
            safe_path = shortcut_path.replace("'", "''")
            safe_args = args.replace("'", "''")
            safe_wd = (working_dir or os.path.dirname(target)).replace("'", "''")
            safe_icon = (icon or target).replace("'", "''")

            ps_cmd = (
                f"$ws = New-Object -ComObject WScript.Shell; "
                f"$sc = $ws.CreateShortcut('{safe_path}'); "
                f"$sc.TargetPath = '{safe_target}'; "
                f"$sc.Arguments = '{safe_args}'; "
                f"$sc.WorkingDirectory = '{safe_wd}'; "
                f"$sc.IconLocation = '{safe_icon}'; "
                f"$sc.Save()"
            )
            r = self._run_powershell(ps_cmd)
            if r["success"]:
                return {"success": True, "message": f"Shortcut created at {shortcut_path}", "data": {"shortcut_path": shortcut_path, "target": target}}
            return {"success": False, "message": f"Failed to create shortcut: {r['stderr']}", "data": {}}
        except Exception as e:
            self.logger.error(f"create_shortcut failed: {e}")
            return {"success": False, "message": str(e), "data": {}}
