import subprocess
import json
import socket


class Toolbox:
    def __init__(self, os_type):
        self.os_type = os_type

    # === DNS CHANGER ===
    def set_dns(self, provider="cloudflare"):
        dns_map = {
            "cloudflare": ["1.1.1.1", "1.0.0.1"],
            "google": ["8.8.8.8", "8.8.4.4"],
            "opendns": ["208.67.222.222", "208.67.220.220"],
            "quad9": ["9.9.9.9", "149.112.112.112"],
            "adguard": ["94.140.14.14", "94.140.15.15"],
            "nextdns": ["45.90.28.0", "45.90.30.0"],
        }
        servers = dns_map.get(provider, dns_map["cloudflare"])
        try:
            if self.os_type == "windows":
                r = subprocess.run(
                    ["netsh", "interface", "show", "interface"],
                    capture_output=True, text=True, timeout=10
                )
                for line in r.stdout.split("\n"):
                    if "Connected" in line:
                        parts = line.split()
                        if len(parts) >= 4:
                            adapter = parts[3]
                            subprocess.run(
                                ["netsh", "interface", "ip", "set", "dns",
                                 f"name={adapter}", "static", servers[0]],
                                capture_output=True, timeout=10
                            )
                            subprocess.run(
                                ["netsh", "interface", "ip", "add", "dns",
                                 f"name={adapter}", servers[1], "index=2"],
                                capture_output=True, timeout=10
                            )
            elif self.os_type == "linux":
                with open("/etc/resolv.conf", "w") as f:
                    f.write(f"# Optimized DNS - {provider}\n")
                    for s in servers:
                        f.write(f"nameserver {s}\n")
            elif self.os_type == "macos":
                result = subprocess.run(
                    ["/usr/sbin/networksetup", "-listallnetworkservices"],
                    capture_output=True, text=True, timeout=10
                )
                for service in result.stdout.strip().split("\n")[1:]:
                    subprocess.run(
                        ["/usr/sbin/networksetup", "-setdnsservers", service] + servers,
                        capture_output=True, timeout=10
                    )
            return {"success": True, "message": f"DNS set to {provider} ({' / '.join(servers)})"}
        except Exception as e:
            return {"success": False, "message": f"DNS change failed: {e}"}

    # === PING TEST ===
    def ping_host(self, host="8.8.8.8", count=4):
        try:
            if self.os_type == "windows":
                r = subprocess.run(
                    ["ping", "-n", str(count), host],
                    capture_output=True, text=True, timeout=30
                )
            else:
                r = subprocess.run(
                    ["ping", "-c", str(count), host],
                    capture_output=True, text=True, timeout=30
                )
            lines = r.stdout.strip().split("\n")
            avg_line = [l for l in lines if "avg" in l.lower() or "mean" in l.lower() or "time=" in l.lower()]
            return {"success": True, "output": r.stdout, "avg": avg_line[0] if avg_line else "N/A"}
        except Exception as e:
            return {"success": False, "message": f"Ping failed: {e}"}

    # === DNS FLUSH ===
    def flush_dns(self):
        try:
            if self.os_type == "windows":
                subprocess.run(["ipconfig", "/flushdns"], capture_output=True, timeout=10)
            elif self.os_type == "macos":
                subprocess.run(["sudo", "dscacheutil", "-flushcache"], capture_output=True, timeout=10)
                subprocess.run(["sudo", "killall", "-HUP", "mDNSResponder"], capture_output=True, timeout=10)
            elif self.os_type == "linux":
                subprocess.run(["sudo", "systemd-resolve", "--flush-caches"], capture_output=True, timeout=10)
            return {"success": True, "message": "DNS cache flushed"}
        except Exception as e:
            return {"success": False, "message": f"DNS flush failed: {e}"}

    # === WINDOWS UPDATE CONTROL ===
    def toggle_windows_update(self, enable=False):
        try:
            if self.os_type != "windows":
                return {"success": True, "message": "Only applies to Windows"}
            state = "Running" if enable else "Stopped"
            startup = "Automatic" if enable else "Disabled"
            subprocess.run(
                ["powershell", "-Command",
                 f"Stop-Service -Name 'wuauserv' -Force -EA SilentlyContinue; "
                 f"Set-Service -Name 'wuauserv' -StartupType {startup} -EA SilentlyContinue"],
                capture_output=True, timeout=15
            )
            subprocess.run(
                ["reg", "add",
                 "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate\\AU",
                 "/v", "NoAutoUpdate", "/t", "REG_DWORD", "/d", "0" if enable else "1", "/f"],
                capture_output=True, timeout=10
            )
            msg = "Windows Update enabled" if enable else "Windows Update disabled"
            return {"success": True, "message": msg}
        except Exception as e:
            return {"success": False, "message": f"Update toggle failed: {e}"}

    # === DEFENDER CONTROL ===
    def toggle_defender(self, enable=False):
        try:
            if self.os_type != "windows":
                return {"success": True, "message": "Only applies to Windows"}
            if enable:
                subprocess.run(
                    ["powershell", "-Command",
                     "Set-MpPreference -DisableRealtimeMonitoring $false -EA SilentlyContinue"],
                    capture_output=True, timeout=15
                )
            else:
                subprocess.run(
                    ["powershell", "-Command",
                     "Set-MpPreference -DisableRealtimeMonitoring $true -EA SilentlyContinue"],
                    capture_output=True, timeout=15
                )
            msg = "Defender enabled" if enable else "Defender realtime protection disabled"
            return {"success": True, "message": msg}
        except Exception as e:
            return {"success": False, "message": f"Defender toggle failed: {e}"}

    # === HOSTS FILE ===
    def get_hosts(self):
        try:
            if self.os_type == "windows":
                hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
            else:
                hosts_path = "/etc/hosts"
            with open(hosts_path, "r") as f:
                return {"success": True, "content": f.read()}
        except Exception as e:
            return {"success": False, "message": f"Cannot read hosts: {e}"}

    def add_hosts_entry(self, ip, domain):
        try:
            if self.os_type == "windows":
                hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
            else:
                hosts_path = "/etc/hosts"
            with open(hosts_path, "a") as f:
                f.write(f"\n{ip} {domain}")
            subprocess.run(["ipconfig", "/flushdns"], capture_output=True, timeout=10)
            return {"success": True, "message": f"Added {domain} -> {ip} to hosts"}
        except Exception as e:
            return {"success": False, "message": f"Hosts edit failed: {e}"}

    # === RIGHT-CLICK MENU (Classic) ===
    def set_classic_context_menu(self, enable=True):
        try:
            if self.os_type != "windows":
                return {"success": True, "message": "Only applies to Windows 11"}
            if enable:
                subprocess.run(
                    ['reg', 'add',
                     'HKCU\\Software\\Classes\\CLSID\\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}',
                     '/v', 'InprocServer32', '/t', 'REG_SZ', '/d', '', '/f'],
                    capture_output=True, timeout=10
                )
                msg = "Classic right-click menu enabled"
            else:
                subprocess.run(
                    ['reg', 'delete',
                     'HKCU\\Software\\Classes\\CLSID\\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}',
                     '/f'],
                    capture_output=True, timeout=10
                )
                msg = "Windows 11 right-click menu restored"
            return {"success": True, "message": msg}
        except Exception as e:
            return {"success": False, "message": f"Context menu failed: {e}"}

    # === POWER PLAN ===
    def set_power_plan(self, plan="high"):
        plans = {
            "high": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
            "ultimate": "e9a42b02-d5df-448d-aa00-03f14749eb61",
            "balanced": "381b4222-f694-41f0-9685-ff5bb260df2e",
            "power_saver": "a1841308-3541-4fab-bc81-f71556f20b4a"
        }
        try:
            if self.os_type == "windows":
                subprocess.run(
                    ["powercfg", "/setactive", plans.get(plan, plans["high"])],
                    capture_output=True, timeout=10
                )
            elif self.os_type == "linux":
                subprocess.run(
                    ["sudo", "cpupower", "frequency-set", "-g",
                     "performance" if plan in ["high", "ultimate"] else "powersave"],
                    capture_output=True, timeout=10
                )
            return {"success": True, "message": f"Power plan set to {plan}"}
        except Exception as e:
            return {"success": False, "message": f"Power plan failed: {e}"}

    # === OFFICE TELEMETRY ===
    def disable_office_telemetry(self):
        try:
            if self.os_type != "windows":
                return {"success": True, "message": "Only applies to Windows"}
            cmds = [
                'reg add "HKCU\\Software\\Microsoft\\Office\\16.0\\Common\\ClientTelemetry" /v DisableTelemetry /t REG_DWORD /d 1 /f',
                'reg add "HKCU\\Software\\Microsoft\\Office\\16.0\\Common\\Feedback" /v DisableFeedbackSignin /t REG_DWORD /d 1 /f',
                'reg add "HKCU\\Software\\Microsoft\\Office\\16.0\\Common\\General" /v TurnOffDataCollectionForTeams /t REG_DWORD /d 1 /f',
                'reg add "HKCU\\Software\\Microsoft\\Office\\16.0\\Outlook\\Options\\Mail" /v EnableLogging /t REG_DWORD /d 0 /f',
            ]
            for cmd in cmds:
                subprocess.run(cmd.split(), capture_output=True, timeout=10)
            return {"success": True, "message": "Office telemetry disabled"}
        except Exception as e:
            return {"success": False, "message": f"Office telemetry failed: {e}"}

    # === HPET DISABLE ===
    def disable_hpet(self):
        try:
            if self.os_type != "windows":
                return {"success": True, "message": "Only applies to Windows"}
            subprocess.run(
                ["bcdedit", "/set", "useplatformclock", "false"],
                capture_output=True, timeout=10
            )
            subprocess.run(
                ["bcdedit", "/set", "useplatformtick", "yes"],
                capture_output=True, timeout=10
            )
            subprocess.run(
                ["bcdedit", "/set", "disabledynamictick", "yes"],
                capture_output=True, timeout=10
            )
            return {"success": True, "message": "HPET disabled, platform tick enabled"}
        except Exception as e:
            return {"success": False, "message": f"HPET disable failed: {e}"}

    # === SYSTEM INFO ===
    def get_hardware_info(self):
        try:
            import psutil
            import platform
            info = {
                "os": platform.system() + " " + platform.release(),
                "processor": platform.processor(),
                "cores_physical": psutil.cpu_count(logical=False),
                "cores_logical": psutil.cpu_count(logical=True),
                "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 1),
                "ram_used_gb": round(psutil.virtual_memory().used / (1024**3), 1),
                "ram_percent": psutil.virtual_memory().percent,
            }
            if self.os_type == "windows":
                try:
                    r = subprocess.run(
                        ["wmic", "path", "win32_videocontroller", "get", "name,adapterram,driverversion"],
                        capture_output=True, text=True, timeout=10
                    )
                    info["gpu"] = r.stdout.strip()
                except Exception:
                    info["gpu"] = "N/A"
            return {"success": True, "info": info}
        except Exception as e:
            return {"success": False, "message": f"Hardware info failed: {e}"}
