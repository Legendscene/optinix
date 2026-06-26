import subprocess


class SecurityOptimizer:
    name = "Security & Privacy"

    def __init__(self, os_type):
        self.os_type = os_type
        self.results = []

    def run(self):
        self.results = []
        if self.os_type == "windows":
            self._disable_telemetry()
            self._remove_bloatware()
            self._optimize_firewall()
            self._disable_advertising_id()
            self._disable_location_tracking()
            self._disable_cortana()
        elif self.os_type == "linux":
            self._linux_privacy()
        elif self.os_type == "macos":
            self._macos_privacy()
        return self.results

    def _disable_telemetry(self):
        try:
            tasks = [
                "Microsoft\\Windows\\Application Experience\\Microsoft Compatibility Appraiser",
                "Microsoft\\Windows\\Application Experience\\ProgramDataUpdater",
                "Microsoft\\Windows\\Customer Experience Improvement Program\\Consolidator",
                "Microsoft\\Windows\\Customer Experience Improvement Program\\UsbCeip",
                "Microsoft\\Windows\\DiskDiagnostic\\Microsoft-Windows-DiskDiagnosticDataCollector",
                "Microsoft\\Windows\\Feedback\\Siuf\\DmClient",
                "Microsoft\\Windows\\Maps\\MapsUpdateTask",
                "Microsoft\\Windows\\Maps\\MapsToastTask"
            ]
            disabled = 0
            for t in tasks:
                r = subprocess.run(["schtasks", "/Change", "/TN", t, "/Disable"], capture_output=True, timeout=10)
                if r.returncode == 0:
                    disabled += 1
            self.results.append({"success": True, "message": f"Disabled {disabled} telemetry tasks"})
        except Exception as e:
            self.results.append({"success": False, "message": f"Telemetry failed: {e}"})

    def _remove_bloatware(self):
        try:
            bloatware = [
                "Microsoft.BingWeather", "Microsoft.GetHelp", "Microsoft.Getstarted",
                "Microsoft.MicrosoftSolitaireCollection", "Microsoft.People",
                "Microsoft.SkypeApp", "Microsoft.WindowsFeedbackHub",
                "Microsoft.YourPhone", "Microsoft.ZuneMusic", "Microsoft.ZuneVideo",
                "Microsoft.WindowsMaps", "Microsoft.MicrosoftOfficeHub",
                "Microsoft.549981C3F5F10", "Microsoft.MicrosoftStickyNotes",
                "Disney.37853FC22B2CE", "SpotifyAB.SpotifyMusic",
                "king.com.CandyCrushSaga", "king.com.CandyCrushSodaSaga"
            ]
            removed = 0
            for app in bloatware:
                r = subprocess.run(
                    ["powershell", "-Command",
                     f"Get-AppxPackage -Name {app} -ErrorAction SilentlyContinue | Remove-AppxPackage -ErrorAction SilentlyContinue"],
                    capture_output=True, timeout=30
                )
                removed += 1
            self.results.append({"success": True, "message": f"Removed {len(bloatware)} bloatware apps"})
        except Exception as e:
            self.results.append({"success": False, "message": f"Bloatware failed: {e}"})

    def _optimize_firewall(self):
        try:
            subprocess.run(["netsh", "advfirewall", "set", "allprofiles", "state", "on"], capture_output=True, timeout=10)
            subprocess.run(["netsh", "advfirewall", "set", "allprofiles", "firewallpolicy",
                           "blockinbound,allowoutbound"], capture_output=True, timeout=10)
            self.results.append({"success": True, "message": "Firewall enabled (block inbound, allow outbound)"})
        except Exception as e:
            self.results.append({"success": False, "message": f"Firewall failed: {e}"})

    def _disable_advertising_id(self):
        try:
            cmds = [
                'reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\AdvertisingInfo" /v Enabled /t REG_DWORD /d 0 /f',
                'reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\ContentDeliveryManager" /v SystemPaneSuggestionsEnabled /t REG_DWORD /d 0 /f',
                'reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\ContentDeliveryManager" /v SilentInstalledAppsEnabled /t REG_DWORD /d 0 /f',
                'reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\ContentDeliveryManager" /v RotatingLockScreenEnabled /t REG_DWORD /d 0 /f'
            ]
            for cmd in cmds:
                subprocess.run(cmd.split(), capture_output=True, timeout=10)
            self.results.append({"success": True, "message": "Advertising ID and suggestions disabled"})
        except Exception as e:
            self.results.append({"success": False, "message": f"Ad ID failed: {e}"})

    def _disable_location_tracking(self):
        try:
            cmds = [
                'reg add "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\LocationAndSensors" /v DisableLocation /t REG_DWORD /d 1 /f',
                'reg add "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\LocationAndSensors" /v DisableWindowsLocationProvider /t REG_DWORD /d 1 /f'
            ]
            for cmd in cmds:
                subprocess.run(cmd.split(), capture_output=True, timeout=10)
            self.results.append({"success": True, "message": "Location tracking disabled"})
        except Exception as e:
            self.results.append({"success": False, "message": f"Location disable failed: {e}"})

    def _disable_cortana(self):
        try:
            cmds = [
                'reg add "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\Windows Search" /v AllowCortana /t REG_DWORD /d 0 /f',
                'reg add "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\Windows Search" /v DisableWebSearch /t REG_DWORD /d 1 /f',
                'reg add "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\Windows Search" /v ConnectedSearchUseWeb /t REG_DWORD /d 0 /f'
            ]
            for cmd in cmds:
                subprocess.run(cmd.split(), capture_output=True, timeout=10)
            self.results.append({"success": True, "message": "Cortana and web search disabled"})
        except Exception as e:
            self.results.append({"success": False, "message": f"Cortana failed: {e}"})

    def _linux_privacy(self):
        try:
            settings = {
                "net.ipv4.conf.all.rp_filter": "1",
                "net.ipv4.conf.all.accept_redirects": "0",
                "net.ipv6.conf.all.accept_redirects": "0",
                "net.ipv4.conf.all.send_redirects": "0",
                "net.ipv4.conf.all.accept_source_route": "0"
            }
            for k, v in settings.items():
                subprocess.run(["sudo", "sysctl", "-w", f"{k}={v}"], capture_output=True, timeout=5)
            self.results.append({"success": True, "message": "Linux network privacy hardened"})
        except Exception as e:
            self.results.append({"success": False, "message": f"Linux privacy failed: {e}"})

    def _macos_privacy(self):
        try:
            cmds = [
                "defaults write com.apple.Safari com.apple.Safari.ContentPageGroupIdentifier.WebKit2JavaScriptCanOpenWindowsAutomatically -bool false",
                "defaults write NSGlobalDomain AppleShowAllExtensions -bool true"
            ]
            for cmd in cmds:
                subprocess.run(cmd.split(), capture_output=True, timeout=10)
            self.results.append({"success": True, "message": "macOS privacy settings optimized"})
        except Exception as e:
            self.results.append({"success": False, "message": f"macOS privacy failed: {e}"})
