import subprocess
import platform
import json
import os
from typing import Dict, List, Any, Optional

class CustomDebloater:
    def __init__(self, os_type: str):
        self.os_type = os_type
        self.debloat_categories = self._load_categories()
    
    def _load_categories(self) -> Dict[str, Dict[str, Any]]:
        return {
            "windows_telemetry": {
                "name": "Windows Telemetry",
                "description": "Disable diagnostic data collection",
                "risk": "low",
                "services": ["DiagTrack", "dmwappushservice", "WerSvc"],
                "registry": [
                    {"path": "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\DataCollection", "name": "AllowTelemetry", "value": "0", "type": "REG_DWORD"},
                    {"path": "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\DataCollection", "name": "AllowTelemetry", "value": "0", "type": "REG_DWORD"},
                ],
                "tasks": ["\\Microsoft\\Windows\\Customer Experience Improvement Program", "\\Microsoft\\Windows\\Application Experience"]
            },
            "cortana": {
                "name": "Cortana & Search",
                "description": "Disable Cortana and web search integration",
                "risk": "low",
                "packages": ["Microsoft.549981C3F5F10", "Microsoft.Windows.Cortana"],
                "registry": [
                    {"path": "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\Windows Search", "name": "AllowCortana", "value": "0", "type": "REG_DWORD"},
                    {"path": "HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Search", "name": "CortanaEnabled", "value": "0", "type": "REG_DWORD"},
                ]
            },
            "edge": {
                "name": "Microsoft Edge",
                "description": "Disable Edge background processes and startup",
                "risk": "low",
                "services": ["edgeupdate", "edgeupdatem"],
                "packages": ["Microsoft.MicrosoftEdge.Stable"],
                "registry": [
                    {"path": "HKLM\\SOFTWARE\\Policies\\Microsoft\\Edge", "name": "StartupBoostEnabled", "value": "0", "type": "REG_DWORD"},
                    {"path": "HKLM\\SOFTWARE\\Policies\\Microsoft\\Edge", "name": "EdgeCollectionsEnabled", "value": "0", "type": "REG_DWORD"},
                ]
            },
            "onedrive": {
                "name": "OneDrive",
                "description": "Disable OneDrive sync and integration",
                "risk": "medium",
                "services": [],
                "registry": [
                    {"path": "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\OneDrive", "name": "DisableFileSyncNGSC", "value": "1", "type": "REG_DWORD"},
                    {"path": "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\OneDrive", "name": "DisableFileSync", "value": "1", "type": "REG_DWORD"},
                ]
            },
            "xbox_gaming": {
                "name": "Xbox & Gaming Services",
                "description": "Disable Xbox services if not gaming on PC",
                "risk": "low",
                "services": ["XblAuthManager", "XblGameSave", "XboxNetApiSvc", "XboxGipSvc", "GamingServices", "GamingServicesNet"],
                "packages": ["Microsoft.XboxApp", "Microsoft.XboxGameOverlay", "Microsoft.XboxGamingOverlay", "Microsoft.XboxIdentityProvider", "Microsoft.XboxSpeechToTextOverlay", "Microsoft.GamingServices"]
            },
            "mixed_reality": {
                "name": "Mixed Reality & Holographic",
                "description": "Remove Mixed Reality portal if no VR headset",
                "risk": "low",
                "packages": ["Microsoft.MixedReality.Portal", "Microsoft.Windows.HolographicFirstRun"]
            },
            "maps": {
                "name": "Maps & Location",
                "description": "Disable Maps app and location services",
                "risk": "low",
                "services": ["lfsvc", "MapsBroker"],
                "packages": ["Microsoft.WindowsMaps"]
            },
            "feedback_hub": {
                "name": "Feedback Hub",
                "description": "Remove Feedback Hub app",
                "risk": "low",
                "packages": ["Microsoft.WindowsFeedbackHub"]
            },
            "tips": {
                "name": "Tips & Get Started",
                "description": "Remove Tips app and Get Started",
                "risk": "low",
                "packages": ["Microsoft.Getstarted", "Microsoft.GetHelp"]
            },
            "office": {
                "name": "Office & Skype",
                "description": "Remove pre-installed Office trial and Skype",
                "risk": "medium",
                "packages": ["Microsoft.Office.OneNote", "Microsoft.SkypeApp", "Microsoft.MicrosoftOfficeHub"]
            },
            "store_apps": {
                "name": "Store Apps (Photos, Mail, Calendar, etc.)",
                "description": "Remove unused default Store apps",
                "risk": "low",
                "packages": [
                    "Microsoft.Windows.Photos", "Microsoft.WindowsCamera", "Microsoft.WindowsSoundRecorder",
                    "Microsoft.WindowsAlarms", "Microsoft.ZuneMusic", "Microsoft.ZuneVideo",
                    "Microsoft.BingWeather", "Microsoft.BingNews", "Microsoft.BingSports",
                    "Microsoft.BingFinance", "Microsoft.WindowsCalculator", "Microsoft.WindowsCommunicationsApps"
                ]
            },
            "defender_cloud": {
                "name": "Defender Cloud Protection",
                "description": "Disable cloud-delivered protection (reduces network usage)",
                "risk": "medium",
                "registry": [
                    {"path": "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows Defender\\Spynet", "name": "SubmitSamplesConsent", "value": "0", "type": "REG_DWORD"},
                    {"path": "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows Defender\\Spynet", "name": "DisableBlockAtFirstSeen", "value": "1", "type": "REG_DWORD"},
                ]
            },
            "windows_update": {
                "name": "Windows Update Control",
                "description": "Configure Windows Update behavior",
                "risk": "medium",
                "services": ["wuauserv", "UsoSvc", "WaaSMedicSvc"],
                "registry": [
                    {"path": "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate\\AU", "name": "NoAutoUpdate", "value": "1", "type": "REG_DWORD"},
                    {"path": "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate\\AU", "name": "AUOptions", "value": "2", "type": "REG_DWORD"},
                ]
            },
            "privacy_general": {
                "name": "General Privacy",
                "description": "Disable advertising ID, location, and app permissions",
                "risk": "low",
                "registry": [
                    {"path": "HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\AdvertisingInfo", "name": "Enabled", "value": "0", "type": "REG_DWORD"},
                    {"path": "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\AdvertisingInfo", "name": "DisabledByGroupPolicy", "value": "1", "type": "REG_DWORD"},
                    {"path": "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\LocationAndSensors", "name": "DisableLocation", "value": "1", "type": "REG_DWORD"},
                ]
            }
        }
    
    def get_categories(self) -> Dict[str, Any]:
        return {k: {**v, "id": k} for k, v in self.debloat_categories.items()}
    
    def apply_category(self, category_id: str, dry_run: bool = False) -> Dict[str, Any]:
        if self.os_type != "windows":
            return {"success": False, "message": "Windows only"}
        
        if category_id not in self.debloat_categories:
            return {"success": False, "message": f"Unknown category: {category_id}"}
        
        cat = self.debloat_categories[category_id]
        results = []
        
        if "services" in cat:
            for svc in cat["services"]:
                try:
                    cmd = ["sc", "config", svc, "start=", "disabled"]
                    if not dry_run:
                        subprocess.run(cmd, capture_output=True, timeout=5)
                    subprocess.run(["sc", "stop", svc], capture_output=True, timeout=5)
                    results.append({"success": True, "message": f"Service {svc} disabled"})
                except Exception as e:
                    results.append({"success": False, "message": f"Service {svc}: {e}"})
        
        if "packages" in cat:
            for pkg in cat["packages"]:
                try:
                    cmd = ["powershell", "-Command", f"Get-AppxPackage *{pkg}* | Remove-AppxPackage"]
                    if not dry_run:
                        subprocess.run(cmd, capture_output=True, timeout=30)
                    results.append({"success": True, "message": f"Package {pkg} removed"})
                except Exception as e:
                    results.append({"success": False, "message": f"Package {pkg}: {e}"})
        
        if "registry" in cat:
            for reg in cat["registry"]:
                try:
                    cmd = ["reg", "add", reg["path"], "/v", reg["name"], "/t", reg["type"], "/d", reg["value"], "/f"]
                    if not dry_run:
                        subprocess.run(cmd, capture_output=True, timeout=5)
                    results.append({"success": True, "message": f"Registry {reg['path']}\\{reg['name']} = {reg['value']}"})
                except Exception as e:
                    results.append({"success": False, "message": f"Registry {reg['name']}: {e}"})
        
        if "tasks" in cat:
            for task in cat["tasks"]:
                try:
                    cmd = ["schtasks", "/Change", "/TN", task, "/Disable"]
                    if not dry_run:
                        subprocess.run(cmd, capture_output=True, timeout=5)
                    results.append({"success": True, "message": f"Task {task} disabled"})
                except Exception as e:
                    results.append({"success": False, "message": f"Task {task}: {e}"})
        
        return {"success": True, "category": category_id, "results": results}
    
    def apply_multiple(self, category_ids: List[str], dry_run: bool = False) -> Dict[str, Any]:
        all_results = []
        for cat_id in category_ids:
            result = self.apply_category(cat_id, dry_run)
            all_results.extend(result.get("results", []))
        
        success_count = sum(1 for r in all_results if r.get("success"))
        total = len(all_results)
        
        return {
            "success": success_count == total,
            "message": f"Applied {success_count}/{total} operations",
            "results": all_results
        }
    
    def create_restore_point(self, description: str = "Optinix Debloat Restore Point") -> Dict[str, Any]:
        if self.os_type != "windows":
            return {"success": False, "message": "Windows only"}
        
        try:
            subprocess.run([
                "powershell", "-Command",
                f"Checkpoint-Computer -Description '{description}' -RestorePointType 'MODIFY_SETTINGS'"
            ], capture_output=True, timeout=60)
            return {"success": True, "message": "Restore point created"}
        except Exception as e:
            return {"success": False, "message": f"Restore point: {e}"}

class AppOptimizer:
    def __init__(self, os_type: str):
        self.os_type = os_type
    
    def optimize_steam(self) -> Dict[str, Any]:
        if self.os_type != "windows":
            return {"success": False, "message": "Windows only"}
        
        results = []
        try:
            subprocess.run([
                "reg", "add", "HKCU\\Software\\Valve\\Steam",
                "/v", "AutoLoginUser", "/t", "REG_SZ", "/d", "", "/f"
            ], capture_output=True, timeout=5)
            results.append({"success": True, "message": "Steam auto-login cleared"})
        except Exception as e:
            results.append({"success": False, "message": f"Steam: {e}"})
        
        return {"success": True, "results": results}
    
    def optimize_discord(self) -> Dict[str, Any]:
        if self.os_type != "windows":
            return {"success": False, "message": "Windows only"}
        
        results = []
        try:
            subprocess.run([
                "reg", "add", "HKCU\\Software\\Discord",
                "/v", "SKIP_HOST_UPDATE", "/t", "REG_DWORD", "/d", "1", "/f"
            ], capture_output=True, timeout=5)
            results.append({"success": True, "message": "Discord auto-update disabled"})
        except Exception as e:
            results.append({"success": False, "message": f"Discord: {e}"})
        
        return {"success": True, "results": results}
    
    def optimize_browsers(self) -> Dict[str, Any]:
        if self.os_type != "windows":
            return {"success": False, "message": "Windows only"}
        
        results = []
        
        browsers = {
            "chrome": "HKCU\\Software\\Policies\\Google\\Chrome",
            "edge": "HKCU\\Software\\Policies\\Microsoft\\Edge",
            "firefox": "HKCU\\Software\\Policies\\Mozilla\\Firefox"
        }
        
        for browser, path in browsers.items():
            try:
                subprocess.run([
                    "reg", "add", path,
                    "/v", "HardwareAccelerationModeEnabled", "/t", "REG_DWORD", "/d", "1", "/f"
                ], capture_output=True, timeout=5)
                results.append({"success": True, "message": f"{browser}: Hardware acceleration enabled"})
            except Exception as e:
                results.append({"success": False, "message": f"{browser}: {e}"})
        
        return {"success": True, "results": results}

if __name__ == "__main__":
    db = CustomDebloater("windows")
    print("Categories:", json.dumps(db.get_categories(), indent=2))