import subprocess
import json
from typing import Dict, List, Any

TWEAKS = {
    "classic_context_menu": {"path": r"HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "name": "EnableXamlStartMenu", "type": "REG_DWORD", "on": "1", "off": "0"},
    "show_file_extensions": {"path": r"HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "name": "HideFileExt", "type": "REG_DWORD", "on": "0", "off": "1"},
    "show_hidden_files": {"path": r"HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "name": "Hidden", "type": "REG_DWORD", "on": "1", "off": "2"},
    "disable_thumbnail_cache": {"path": r"HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "name": "DisableThumbnailCache", "type": "REG_DWORD", "on": "1", "off": "0"},
    "small_taskbar_icons": {"path": r"HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "name": "TaskbarSmallIcons", "type": "REG_DWORD", "on": "1", "off": "0"},
    "never_combine_buttons": {"path": r"HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "name": "TaskbarGlomLevel", "type": "REG_DWORD", "on": "2", "off": "0"},
    "show_seconds_in_clock": {"path": r"HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "name": "ShowSecondsInSystemClock", "type": "REG_DWORD", "on": "1", "off": "0"},
    "disable_uac": {"path": r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System", "name": "EnableLUA", "type": "REG_DWORD", "on": "0", "off": "1"},
    "disable_hibernation": {"path": r"HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Power", "name": "HiberbootEnabled", "type": "REG_DWORD", "on": "0", "off": "1"},
    "disable_error_reporting": {"path": r"HKLM\SOFTWARE\Microsoft\Windows\Windows Error Reporting", "name": "Disabled", "type": "REG_DWORD", "on": "1", "off": "0"},
    "disable_action_center": {"path": r"HKCU\SOFTWARE\Policies\Microsoft\Windows\Explorer", "name": "DisableNotificationCenter", "type": "REG_DWORD", "on": "1", "off": "0"},
    "best_performance_visuals": {"path": r"HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects", "name": "BestPerformance", "type": "REG_DWORD", "on": "1", "off": "0"},
    "disable_animations": {"path": r"HKCU\Control Panel\Desktop", "name": "UserPreferencesMask", "type": "REG_BINARY", "on": "90000000", "off": "9e3e0780"},
    "disable_window_shadows": {"path": r"HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "name": "DisableWindowShadow", "type": "REG_DWORD", "on": "1", "off": "0"},
}

CATEGORIES = {
    "Explorer": ["classic_context_menu", "show_file_extensions", "show_hidden_files", "disable_thumbnail_cache"],
    "Taskbar": ["small_taskbar_icons", "never_combine_buttons", "show_seconds_in_clock"],
    "System": ["disable_uac", "disable_hibernation", "disable_error_reporting", "disable_action_center"],
    "Performance": ["best_performance_visuals", "disable_animations", "disable_window_shadows"],
}

class WindowsTweaks:
    def __init__(self, os_type: str):
        self.os_type = os_type

    def get_tweaks(self) -> Dict[str, Any]:
        return {"tweaks": TWEAKS, "categories": CATEGORIES}

    def apply_tweak(self, tweak_id: str, enable: bool) -> Dict[str, Any]:
        if self.os_type != "windows":
            return {"success": False, "message": "Windows only"}

        if tweak_id not in TWEAKS:
            return {"success": False, "message": f"Unknown tweak: {tweak_id}"}

        t = TWEAKS[tweak_id]
        try:
            subprocess.run([
                "reg", "add", t["path"], "/v", t["name"],
                "/t", t["type"], "/d", t["on"] if enable else t["off"], "/f"
            ], capture_output=True, timeout=5)
            return {"success": True, "message": f"{'Enabled' if enable else 'Disabled'}: {tweak_id}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def apply_multiple(self, tweaks: Dict[str, bool]) -> Dict[str, Any]:
        results = []
        for tid, enable in tweaks.items():
            results.append(self.apply_tweak(tid, enable))
        success_count = sum(1 for r in results if r.get("success"))
        return {"success": success_count == len(results), "results": results}

    def export_settings(self, active_tweaks: Dict[str, bool]) -> Dict[str, Any]:
        return {"success": True, "tweaks": active_tweaks}

    def import_settings(self, tweaks: Dict[str, bool]) -> Dict[str, Any]:
        return self.apply_multiple(tweaks)
