import subprocess
from core.rollback_engine import RollbackEngine


class UltimateTweaks:
    """Ultimate Tweaks — SAFE version.
    
    Removed (dangerous/placebo):
    - PROCTHROTTLEMIN 100 → NEVER set min processor to 100%
    - CPMINCORES 100 → lets Windows manage core parking
    - IDLEDISABLE 1 → lets CPU enter C-states
    - DisablePagingExecutive → modern Windows manages this
    - IoPageLockLimit → no effect on Win 10+
    - NetworkThrottlingIndex → outdated, modern Windows handles QoS
    - TcpAckFrequency / TCPNoDelay → no effect on Win 10+ TCP stack
    - IRQ8Priority → hasn't worked since Win XP
    - EnablePrefetcher/Superfetch=0 → harms performance on SSDs
    - Win32PrioritySeparation → use default (balanced)
    - GlobalTimerResolutionRequests → Windows manages this
    - bcdedit useplatformtick/disabledynamictick → uses TSC (better)
    - LargeSystemCache=0 → Windows manages dynamically
    """

    def __init__(self, os_type):
        self.os_type = os_type
        self.rollback = RollbackEngine(os_type) if os_type == "windows" else None

    def get_all_registry_tweaks(self):
        """Safe tweaks only. Privacy, UX, and UI customization.
        
        Cat: 🟢 Safe — Privacy, UX, visual preferences
        Cat: 🟡 Advanced — Service disabling
        Cat: 🔴 Experimental — NONE (all removed)
        """
        return self._safe_privacy_tweaks() + self._safe_ux_tweaks()

    def _safe_privacy_tweaks(self):
        """🟢 Safe privacy tweaks — no stability impact."""
        return [
            # Telemetry opt-out (Group Policy respected values)
            {"path": "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\DataCollection", "name": "AllowTelemetry", "value": "0", "type": "REG_DWORD",
             "explanation": "Sets telemetry to Security-only (lowest)",
             "benefit": "Reduces data sent to Microsoft",
             "risks": "Some diagnostic features may not work. Microsoft recommends '1' (Basic) for security updates.",
             "rollback": "reg add \"HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\DataCollection\" /v AllowTelemetry /t REG_DWORD /d 1 /f"},
            {"path": "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\AdvertisingInfo", "name": "Enabled", "value": "0", "type": "REG_DWORD",
             "explanation": "Disables Advertising ID for app personalization",
             "benefit": "Reduces targeted ads",
             "risks": "None",
             "rollback": "reg add \"HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\AdvertisingInfo\" /v Enabled /t REG_DWORD /d 1 /f"},
            {"path": "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\Windows Search", "name": "AllowCortana", "value": "0", "type": "REG_DWORD",
             "explanation": "Disables Cortana assistant",
             "benefit": "Frees ~200MB RAM, reduces background activity",
             "risks": "Voice assistant features disabled",
             "rollback": "reg add \"HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\Windows Search\" /v AllowCortana /t REG_DWORD /d 1 /f"},
            {"path": "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\ContentDeliveryManager", "name": "ContentDeliveryAllowed", "value": "0", "type": "REG_DWORD",
             "explanation": "Prevents Windows from suggesting apps and content",
             "benefit": "Cleaner Start menu, less bloatware reinstallation",
             "risks": "None",
             "rollback": "reg add \"HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\ContentDeliveryManager\" /v ContentDeliveryAllowed /t REG_DWORD /d 1 /f"},
            {"path": "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\CloudContent", "name": "DisableWindowsConsumerFeatures", "value": "1", "type": "REG_DWORD",
             "explanation": "Disables Windows Spotlight and consumer features",
             "benefit": "Stops auto-installing suggested apps",
             "risks": "None",
             "rollback": "reg add \"HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\CloudContent\" /v DisableWindowsConsumerFeatures /t REG_DWORD /d 0 /f"},
        ]

    def _safe_ux_tweaks(self):
        """🟢 Safe UX tweaks — user preference, no stability impact."""
        return [
            {"path": "HKCU\\Control Panel\\Desktop", "name": "MenuShowDelay", "value": "200", "type": "REG_SZ",
             "explanation": "Sets menu show delay. Default is 400. 200 is faster but not instant.",
             "benefit": "Slightly snappier menu appearance",
             "risks": "None. Range 0-4000 is valid.",
             "rollback": "reg add \"HKCU\\Control Panel\\Desktop\" /v MenuShowDelay /t REG_SZ /d \"400\" /f"},
            {"path": "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced", "name": "LaunchTo", "value": "1", "type": "REG_DWORD",
             "explanation": "Opens File Explorer to 'This PC' instead of 'Home'",
             "benefit": "Faster access to drives",
             "risks": "None",
             "rollback": "reg add \"HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced\" /v LaunchTo /t REG_DWORD /d 0 /f"},
            {"path": "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced", "name": "HideFileExt", "value": "0", "type": "REG_DWORD",
             "explanation": "Shows file extension for known file types",
             "benefit": "Security: prevents disguised malware extensions",
             "risks": "None",
             "rollback": "reg add \"HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced\" /v HideFileExt /t REG_DWORD /d 1 /f"},
            {"path": "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced", "name": "Hidden", "value": "1", "type": "REG_DWORD",
             "explanation": "Shows hidden files and folders",
             "benefit": "Better visibility of system files",
             "risks": "Can confuse non-technical users",
             "rollback": "reg add \"HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced\" /v Hidden /t REG_DWORD /d 2 /f"},
            {"path": "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced", "name": "TaskbarMn", "value": "0", "type": "REG_DWORD",
             "explanation": "Hides the Chat/widgets icon on taskbar",
             "benefit": "Cleaner taskbar, frees space",
             "risks": "None",
             "rollback": "reg add \"HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced\" /v TaskbarMn /t REG_DWORD /d 1 /f"},
        ]

    def get_experimental_tweaks(self):
        """🔴 Experimental — NEVER run automatically.
        These require user consent and are documented with risks.
        """
        return []

    def get_all_services(self):
        """🟢 Safe services to disable — verified for Windows 11 24H2."""
        return [
            {"name": "DiagTrack", "desc": "Connected User Experiences and Telemetry", "safe": True,
             "explanation": "Collects diagnostic data. Safe to disable if telemetry is opt-out.",
             "benefit": "Reduces background CPU/disk usage",
             "risks": "Some Microsoft apps may retry sending telemetry repeatedly (wastes CPU)",
             "rollback": "sc config DiagTrack start=auto"},
            {"name": "WSearch", "desc": "Windows Search Indexer", "safe": True,
             "explanation": "Indexes files for faster search. Disabling saves CPU but makes searches slower.",
             "benefit": "Reduces constant disk I/O and CPU",
             "risks": "Windows Search becomes slow. File Explorer search still works but is slower.",
             "rollback": "sc config WSearch start=auto"},
            {"name": "MapsBroker", "desc": "Downloaded Maps Manager", "safe": True,
             "explanation": "Manages map downloads. Safe to disable if you don't use Maps app.",
             "benefit": "Frees ~50MB RAM",
             "risks": "Maps app won't work offline",
             "rollback": "sc config MapsBroker start=demand"},
            {"name": "RemoteRegistry", "desc": "Remote Registry Service", "safe": True,
             "explanation": "Allows remote registry editing. Security risk. Disable on all non-domain PCs.",
             "benefit": "Security improvement",
             "risks": "None for home users",
             "rollback": "sc config RemoteRegistry start=demand"},
            {"name": "XblAuthManager", "desc": "Xbox Live Auth Manager", "safe": True,
             "explanation": "Provides Xbox Live authentication. Safe to disable if not gaming on Xbox ecosystem.",
             "benefit": "Frees ~30MB RAM",
             "risks": "Xbox app/games won't sign in",
             "rollback": "sc config XblAuthManager start=demand"},
            {"name": "XblGameSave", "desc": "Xbox Live Game Save", "safe": True,
             "explanation": "Syncs Xbox save games to cloud. Safe to disable if not using Xbox.",
             "benefit": "Frees ~15MB RAM",
             "risks": "Xbox cloud saves disabled",
             "rollback": "sc config XblGameSave start=demand"},
            {"name": "XboxNetApiSvc", "desc": "Xbox Live Networking", "safe": True,
             "explanation": "Xbox Live networking service.",
             "benefit": "Frees ~10MB RAM",
             "risks": "Multiplayer in Xbox app games may not work",
             "rollback": "sc config XboxNetApiSvc start=demand"},
            {"name": "edgeupdate", "desc": "Edge Update Service", "safe": True,
             "explanation": "Auto-updates Microsoft Edge. Disabling means manual updates.",
             "benefit": "Reduces background network usage",
             "risks": "Edge won't auto-update, potential security risk",
             "rollback": "sc config edgeupdate start=auto"},
            {"name": "WerSvc", "desc": "Windows Error Reporting", "safe": True,
             "explanation": "Reports crashes to Microsoft. Safe to disable.",
             "benefit": "No crash dialogs, less background network",
             "risks": "Crashes are not reported to Microsoft",
             "rollback": "sc config WerSvc start=demand"},
        ]

    def apply_registry_tweaks(self, tweaks=None):
        """Apply registry tweaks with rollback snapshots."""
        if tweaks is None:
            tweaks = self.get_all_registry_tweaks()
        results = []
        applied = 0
        for t in tweaks:
            try:
                if self.rollback:
                    full_path = t["path"].replace("HKLM\\", "HKLM\\").replace("HKCU\\", "HKCU\\")
                    self.rollback.snapshot_registry(full_path, t["name"])
                cmd = f'reg add "{t["path"]}" /v {t["name"]} /t {t["type"]} /d {t["value"]} /f'
                subprocess.run(cmd, capture_output=True, shell=True, timeout=10)
                applied += 1
            except Exception:
                continue
        if self.rollback:
            self.rollback.save_snapshot()
        results.append({"success": True, "message": f"Applied {applied}/{len(tweaks)} registry tweaks"})
        return results

    def apply_all_optimizations(self):
        """Safe full optimization. No dangerous tweaks."""
        results = []
        if self.rollback:
            r = self.rollback.create_restore_point("Optinix Safe Optimize")
            results.append(r)
            self.rollback.snapshot_power_plan()
        results.extend(self.apply_registry_tweaks())
        results.extend(self._disable_safe_services())
        results.extend(self._disable_safe_tasks())
        if self.rollback:
            self.rollback.save_snapshot()
        return results

    def _disable_safe_services(self):
        services = [s for s in self.get_all_services() if s["safe"]]
        disabled = 0
        for svc in services:
            try:
                if self.rollback:
                    self.rollback.snapshot_service(svc["name"])
                subprocess.run(
                    ["powershell", "-Command",
                     f"Stop-Service -Name '{svc['name']}' -Force -EA SilentlyContinue; "
                     f"Set-Service -Name '{svc['name']}' -StartupType Disabled -EA SilentlyContinue"],
                    capture_output=True, timeout=15
                )
                disabled += 1
            except Exception:
                continue
        return [{"success": True, "message": f"Disabled {disabled} safe services"}]

    def _disable_safe_tasks(self):
        tasks = [
            "Microsoft\\Windows\\Customer Experience Improvement Program\\Consolidator",
            "Microsoft\\Windows\\Customer Experience Improvement Program\\UsbCeip",
            "Microsoft\\Windows\\Feedback\\Siuf\\DmClient",
            "Microsoft\\Windows\\Feedback\\Siuf\\DmClientOnScenarioDownload",
            "Microsoft\\Office\\OfficeTelemetryAgentFallBack",
            "Microsoft\\Office\\OfficeTelemetryAgentLogOn",
        ]
        disabled = 0
        for t in tasks:
            try:
                if self.rollback:
                    self.rollback.snapshot_task(t)
                r = subprocess.run(["schtasks", "/Change", "/TN", t, "/Disable"], capture_output=True, timeout=10)
                if r.returncode == 0:
                    disabled += 1
            except Exception:
                continue
        return [{"success": True, "message": f"Disabled {disabled} telemetry tasks"}]
