import subprocess
import json


class ServicesManager:
    BLOATWARE_SERVICES = {
        "windows": [
            {"name": "DiagTrack", "desc": "Connected User Experiences and Telemetry", "safe": True},
            {"name": "SysMain", "desc": "Superfetch / SysMain (memory prefetcher)", "safe": True},
            {"name": "WSearch", "desc": "Windows Search Indexer", "safe": True},
            {"name": "TabletInputService", "desc": "Touch Keyboard and Handwriting", "safe": True},
            {"name": "RetailDemo", "desc": "Retail Demo Service", "safe": True},
            {"name": "MapsBroker", "desc": "Downloaded Maps Manager", "safe": True},
            {"name": "lfsvc", "desc": "Geolocation Service", "safe": True},
            {"name": "SharedAccess", "desc": "Internet Connection Sharing", "safe": True},
            {"name": "RemoteRegistry", "desc": "Remote Registry", "safe": True},
            {"name": "wisvc", "desc": "Windows Insider Service", "safe": True},
            {"name": "WpcMonSvc", "desc": "Parental Controls", "safe": True},
            {"name": "PhoneSvc", "desc": "Phone Service", "safe": True},
            {"name": "TapiSv", "desc": "Telephony", "safe": True},
            {"name": "XblAuthManager", "desc": "Xbox Live Auth Manager", "safe": True},
            {"name": "XblGameSave", "desc": "Xbox Live Game Save", "safe": True},
            {"name": "XboxNetApiSvc", "desc": "Xbox Live Networking", "safe": True},
            {"name": "XboxGipSvc", "desc": "Xbox Accessory Management", "safe": True},
            {"name": "dmwappushservice", "desc": "WAP Push Message Routing", "safe": True},
            {"name": "AJRouter", "desc": "AllJoyn Router Service", "safe": True},
            {"name": "BDESVC", "desc": "BitLocker Drive Encryption", "safe": True},
            {"name": "cbdhsvc", "desc": "Clipboard Service", "safe": True},
            {"name": "edgeupdate", "desc": "Microsoft Edge Update", "safe": True},
            {"name": "edgeupdatem", "desc": "Microsoft Edge Update (machine)", "safe": True},
            {"name": "MicrosoftEdgeElevationService", "desc": "Edge Elevation Service", "safe": True},
            {"name": "WerSvc", "desc": "Windows Error Reporting", "safe": True},
            {"name": "PcaSvc", "desc": "Program Compatibility Assistant", "safe": True},
            {"name": "TrkWks", "desc": "Distributed Link Tracking Client", "safe": True},
            {"name": "DPS", "desc": "Diagnostic Policy Service", "safe": True},
            {"name": "WbioSrvc", "desc": "Windows Biometric Service", "safe": False},
            {"name": "Spooler", "desc": "Print Spooler", "safe": False},
            {"name": "wuauserv", "desc": "Windows Update", "safe": False},
            {"name": "WinDefend", "desc": "Windows Defender", "safe": False},
            {"name": "Schedule", "desc": "Task Scheduler", "safe": False},
            {"name": "Dnscache", "desc": "DNS Client", "safe": False},
            {"name": "EventLog", "desc": "Windows Event Log", "safe": False},
            {"name": "Themes", "desc": "Themes", "safe": False},
            {"name": "AudioSrv", "desc": "Windows Audio", "safe": False},
            {"name": "plugplay", "desc": "Plug and Play", "safe": False},
            {"name": "ProfSvc", "desc": "User Profile Service", "safe": False},
        ],
        "linux": [
            {"name": "cups", "desc": "Printing Service", "safe": True},
            {"name": "bluetooth", "desc": "Bluetooth Service", "safe": True},
            {"name": "avahi-daemon", "desc": "mDNS/Bonjour", "safe": True},
            {"name": "ModemManager", "desc": "Modem Manager", "safe": True},
            {"name": "whoopsie", "desc": "Ubuntu Crash Reporting", "safe": True},
            {"name": "apport", "desc": "Crash Reports", "safe": True},
            {"name": "snapd", "desc": "Snap Package Manager", "safe": True},
            {"name": "accounts-daemon", "desc": "Accounts Service", "safe": False},
            {"name": "networkd-dispatcher", "desc": "Network Dispatcher", "safe": False},
        ],
        "macos": [
            {"name": "com.apple.spotlight", "desc": "Spotlight Search", "safe": True},
            {"name": "com.apple.Safari.SafeBrowsing", "desc": "Safari Safe Browsing", "safe": True},
            {"name": "com.apple.icloud.fmfd", "desc": "Find My Mac", "safe": True},
            {"name": "com.apple.locationd", "desc": "Location Services", "safe": True},
        ]
    }

    def __init__(self, os_type):
        self.os_type = os_type

    def list_services(self):
        services = self.BLOATWARE_SERVICES.get(self.os_type, [])

        if self.os_type == "windows":
            running = self._get_running_services()
            for svc in services:
                svc["running"] = svc["name"] in running
        elif self.os_type == "linux":
            running = self._get_linux_services()
            for svc in services:
                svc["running"] = svc["name"] in running

        return services

    def toggle_service(self, name, enable):
        try:
            if self.os_type == "windows":
                state = "Running" if enable else "Stopped"
                start = "Automatic" if enable else "Disabled"
                subprocess.run(
                    ["powershell", "-Command",
                     f"{'Start' if enable else 'Stop'}-Service -Name '{name}' -Force -ErrorAction SilentlyContinue; "
                     f"Set-Service -Name '{name}' -StartupType {start} -ErrorAction SilentlyContinue"],
                    capture_output=True, timeout=15
                )
            elif self.os_type == "linux":
                action = "start" if enable else "stop"
                subprocess.run(["sudo", "systemctl", action, name], capture_output=True, timeout=10)
                en_action = "enable" if enable else "disable"
                subprocess.run(["sudo", "systemctl", en_action, name], capture_output=True, timeout=10)

            return {"success": True, "message": f"{name} {'enabled' if enable else 'disabled'}"}
        except Exception as e:
            return {"success": False, "message": f"Failed: {e}"}

    def _get_running_services(self):
        try:
            r = subprocess.run(
                ["powershell", "-Command",
                 "Get-Service | Where-Object {$_.Status -eq 'Running'} | Select-Object -ExpandProperty Name"],
                capture_output=True, text=True, timeout=15
            )
            return set(r.stdout.strip().split("\n"))
        except Exception:
            return set()

    def _get_linux_services(self):
        try:
            r = subprocess.run(
                ["systemctl", "list-units", "--type=service", "--state=running", "--no-pager", "--no-legend"],
                capture_output=True, text=True, timeout=10
            )
            services = set()
            for line in r.stdout.strip().split("\n"):
                if line.strip():
                    services.add(line.split()[0].replace(".service", ""))
            return services
        except Exception:
            return set()
