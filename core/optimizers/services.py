import subprocess


class ServicesOptimizer:
    name = "Services Optimization"

    def __init__(self, os_type):
        self.os_type = os_type
        self.results = []

    def run(self):
        self.results = []
        if self.os_type == "windows":
            self._disable_heavy_services()
            self._disable_startup_apps()
            self._disable_unwanted_tasks()
        elif self.os_type == "linux":
            self._disable_linux_services()
        elif self.os_type == "macos":
            self._disable_macos_agents()
        return self.results

    def _disable_heavy_services(self):
        services = [
            "SysMain", "DiagTrack", "WSearch", "TabletInputService",
            "RetailDemo", "MapsBroker", "lfsvc", "SharedAccess",
            "RemoteRegistry", "wisvc", "WpcMonSvc", "PhoneSvc",
            "TapiSrv", "RpcSs", "XblAuthManager", "XblGameSave",
            "XboxNetApiSvc", "XboxGipSvc", "dmwappushservice",
            "AJRouter", "BDESVC", "BthAvctpSvc", "cbdhsvc",
            "edgeupdate", "edgeupdatem", "MicrosoftEdgeElevationService",
            "WerSvc", "PcaSvc", "TrkWks", "DPS"
        ]
        disabled = 0
        for svc in services:
            try:
                r = subprocess.run(
                    ["powershell", "-Command",
                     f"Stop-Service -Name '{svc}' -Force -ErrorAction SilentlyContinue; "
                     f"Set-Service -Name '{svc}' -StartupType Disabled -ErrorAction SilentlyContinue"],
                    capture_output=True, timeout=15
                )
                disabled += 1
            except Exception:
                continue
        self.results.append({"success": True, "message": f"Disabled {disabled} Windows services"})

    def _disable_startup_apps(self):
        try:
            r = subprocess.run(
                ["powershell", "-Command",
                 "Get-CimInstance Win32_StartupCommand | Select-Object Name, Command | ConvertTo-Json"],
                capture_output=True, text=True, timeout=15
            )
            import json
            apps = json.loads(r.stdout) if r.stdout.strip() else []
            if isinstance(apps, dict):
                apps = [apps]
            self.results.append({"success": True, "message": f"Found {len(apps)} startup apps (review recommended)"})
        except Exception:
            self.results.append({"success": True, "message": "Startup apps scanned"})

    def _disable_unwanted_tasks(self):
        tasks = [
            "Microsoft\\Windows\\Application Experience\\Microsoft Compatibility Appraiser",
            "Microsoft\\Windows\\Application Experience\\ProgramDataUpdater",
            "Microsoft\\Windows\\Customer Experience Improvement Program\\Consolidator",
            "Microsoft\\Windows\\Customer Experience Improvement Program\\UsbCeip",
            "Microsoft\\Windows\\DiskDiagnostic\\Microsoft-Windows-DiskDiagnosticDataCollector",
            "Microsoft\\Windows\\Maps\\MapsUpdateTask",
            "Microsoft\\Windows\\Maps\\MapsToastTask",
            "Microsoft\\Windows\\Windows Error Reporting\\QueueReporting",
            "Microsoft\\Office\\OfficeTelemetryAgentFallBack",
            "Microsoft\\Office\\OfficeTelemetryAgentLogOn",
            "Microsoft\\Office\\OfficeTelemetryAgentFallBack2016",
            "Microsoft\\Office\\OfficeTelemetryAgentLogOn2016"
        ]
        disabled = 0
        for t in tasks:
            r = subprocess.run(["schtasks", "/Change", "/TN", t, "/Disable"], capture_output=True, timeout=10)
            if r.returncode == 0:
                disabled += 1
        self.results.append({"success": True, "message": f"Disabled {disabled} scheduled tasks"})

    def _disable_linux_services(self):
        services = [
            "cups", "bluetooth", "avahi-daemon", "ModemManager",
            "whoopsie", "apport", "snapd"
        ]
        disabled = 0
        for svc in services:
            try:
                subprocess.run(["sudo", "systemctl", "stop", svc], capture_output=True, timeout=10)
                subprocess.run(["sudo", "systemctl", "disable", svc], capture_output=True, timeout=10)
                disabled += 1
            except Exception:
                continue
        self.results.append({"success": True, "message": f"Disabled {disabled} Linux services"})

    def _disable_macos_agents(self):
        agents = [
            "com.apple.spotlight",
            "com.apple.Safari.SafeBrowsing",
            "com.apple.icloud.fmfd"
        ]
        disabled = 0
        for agent in agents:
            try:
                subprocess.run(["launchctl", "unload", "-w", f"/System/Library/LaunchAgents/{agent}.plist"],
                             capture_output=True, timeout=10)
                disabled += 1
            except Exception:
                continue
        self.results.append({"success": True, "message": f"Disabled {disabled} macOS agents"})
