import subprocess
import json
import os


class StartupManager:
    HEAVY_STARTUP = {
        "windows": [
            {"name": "Spotify", "desc": "Spotify Music", "safe": True},
            {"name": "Discord", "desc": "Discord Chat", "safe": True},
            {"name": "Steam", "desc": "Steam Client", "safe": True},
            {"name": "EpicGamesLauncher", "desc": "Epic Games Launcher", "safe": True},
            {"name": "OneDrive", "desc": "Microsoft OneDrive", "safe": True},
            {"name": "Teams", "desc": "Microsoft Teams", "safe": True},
            {"name": "Skype", "desc": "Skype", "safe": True},
            {"name": "Slack", "desc": "Slack Messenger", "safe": True},
            {"name": "Zoom", "desc": "Zoom Meeting", "safe": True},
            {"name": "AdobeGCClient", "desc": "Adobe Genuine Software", "safe": True},
            {"name": "CCXProcess", "desc": "Adobe CCX Process", "safe": True},
            {"name": "SteamWebHelper", "desc": "Steam Web Helper", "safe": True},
            {"name": "EADesktop", "desc": "EA Desktop", "safe": True},
            {"name": "RtkAuduService", "desc": "Realtek Audio", "safe": True},
            {"name": "NvBackend", "desc": "NVIDIA Backend", "safe": True},
            {"name": "Cortana", "desc": "Cortana", "safe": True},
            {"name": "WindowsSecurity", "desc": "Windows Security", "safe": False},
        ],
        "linux": [
            {"name": "snap-store", "desc": "Snap Store", "safe": True},
            {"name": "update-notifier", "desc": "Update Notifier", "safe": True},
        ],
        "macos": [
            {"name": "Spotify", "desc": "Spotify Music", "safe": True},
            {"name": "Discord", "desc": "Discord Chat", "safe": True},
            {"name": "Slack", "desc": "Slack Messenger", "safe": True},
        ]
    }

    def __init__(self, os_type):
        self.os_type = os_type

    def list_startup_apps(self):
        apps = list(self.HEAVY_STARTUP.get(self.os_type, []))

        if self.os_type == "windows":
            detected = self._detect_windows_startup()
            existing_names = {a["name"].lower() for a in apps}
            for d in detected:
                if d["name"].lower() not in existing_names:
                    apps.append(d)
        elif self.os_type == "linux":
            detected = self._detect_linux_startup()
            existing_names = {a["name"].lower() for a in apps}
            for d in detected:
                if d["name"].lower() not in existing_names:
                    apps.append(d)

        return apps

    def toggle_startup(self, name, enable):
        try:
            if self.os_type == "windows":
                if enable:
                    subprocess.run(
                        ["powershell", "-Command",
                         f"Get-ScheduledTask -TaskName '*{name}*' -ErrorAction SilentlyContinue | "
                         f"Enable-ScheduledTask -ErrorAction SilentlyContinue"],
                        capture_output=True, timeout=15
                    )
                else:
                    subprocess.run(
                        ["powershell", "-Command",
                         f"Get-ScheduledTask -TaskName '*{name}*' -ErrorAction SilentlyContinue | "
                         f"Disable-ScheduledTask -ErrorAction SilentlyContinue"],
                        capture_output=True, timeout=15
                    )
                    subprocess.run(
                        ["reg", "delete",
                         f"HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run",
                         "/v", name, "/f"],
                        capture_output=True, timeout=10
                    )
            elif self.os_type == "linux":
                if enable:
                    subprocess.run(["sudo", "systemctl", "enable", name], capture_output=True, timeout=10)
                else:
                    subprocess.run(["sudo", "systemctl", "disable", name], capture_output=True, timeout=10)

            return {"success": True, "message": f"{name} startup {'enabled' if enable else 'disabled'}"}
        except Exception as e:
            return {"success": False, "message": f"Failed: {e}"}

    def _detect_windows_startup(self):
        apps = []
        try:
            r = subprocess.run(
                ["powershell", "-Command",
                 "Get-CimInstance Win32_StartupCommand | Select-Object Name, Command, Location | ConvertTo-Json"],
                capture_output=True, text=True, timeout=15
            )
            if r.stdout.strip():
                data = json.loads(r.stdout)
                if isinstance(data, dict):
                    data = [data]
                for item in data:
                    apps.append({
                        "name": item.get("Name", "Unknown"),
                        "desc": item.get("Command", ""),
                        "location": item.get("Location", ""),
                        "safe": True
                    })
        except Exception:
            pass
        return apps

    def _detect_linux_startup(self):
        apps = []
        try:
            home = os.path.expanduser("~")
            autostart_dir = os.path.join(home, ".config", "autostart")
            if os.path.exists(autostart_dir):
                for f in os.listdir(autostart_dir):
                    if f.endswith(".desktop"):
                        apps.append({
                            "name": f.replace(".desktop", ""),
                            "desc": f"Autostart: {f}",
                            "safe": True
                        })
        except Exception:
            pass
        return apps
