import subprocess
import platform
import json
import os
import re
from typing import Dict, List, Optional, Any

class BIOSOptimizer:
    def __init__(self, os_type: str):
        self.os_type = os_type
        self.motherboard_info = self._get_motherboard_info()
        self.bios_vendor = self._get_bios_vendor()
    
    def _get_motherboard_info(self) -> Dict[str, str]:
        info = {"manufacturer": "Unknown", "model": "Unknown", "version": "Unknown"}
        if self.os_type == "windows":
            try:
                r = subprocess.run([
                    "wmic", "baseboard", "get", "Manufacturer,Product,Version", "/format:csv"
                ], capture_output=True, text=True, timeout=10)
                lines = r.stdout.strip().split('\n')
                if len(lines) >= 2:
                    parts = lines[1].split(',')
                    if len(parts) >= 4:
                        info = {"manufacturer": parts[1], "model": parts[2], "version": parts[3]}
            except Exception:
                pass
        return info
    
    def _get_bios_vendor(self) -> str:
        if self.os_type == "windows":
            try:
                r = subprocess.run([
                    "wmic", "bios", "get", "Manufacturer,SMBIOSBIOSVersion", "/format:csv"
                ], capture_output=True, text=True, timeout=10)
                lines = r.stdout.strip().split('\n')
                if len(lines) >= 2:
                    parts = lines[1].split(',')
                    if len(parts) >= 3:
                        return f"{parts[1]} {parts[2]}"
            except Exception:
                pass
        return "Unknown"
    
    def get_bios_info(self) -> Dict[str, Any]:
        return {
            "motherboard": self.motherboard_info,
            "bios_vendor": self.bios_vendor,
            "os_type": self.os_type
        }
    
    def get_recommended_settings(self) -> List[Dict[str, Any]]:
        vendor = self.bios_vendor.lower()
        manufacturer = self.motherboard_info.get("manufacturer", "").lower()
        
        recommendations = []
        
        if "asus" in vendor or "asus" in manufacturer:
            recommendations.extend(self._asus_recommendations())
        elif "msi" in vendor or "msi" in manufacturer:
            recommendations.extend(self._msi_recommendations())
        elif "gigabyte" in vendor or "gigabyte" in manufacturer or "aorus" in vendor:
            recommendations.extend(self._gigabyte_recommendations())
        elif "asrock" in vendor or "asrock" in manufacturer:
            recommendations.extend(self._asrock_recommendations())
        else:
            recommendations.extend(self._generic_recommendations())
        
        return recommendations
    
    def _asus_recommendations(self) -> List[Dict[str, Any]]:
        return [
            {"name": "AI Overclock Tuner", "setting": "DOCP/XMP", "description": "Enable memory XMP profile for rated speeds"},
            {"name": "CPU Core Ratio", "setting": "Sync All Cores", "description": "Synchronize all core ratios for stability"},
            {"name": "CPU Core Voltage", "setting": "Adaptive/Offset", "description": "Use adaptive voltage for efficiency"},
            {"name": "Load-Line Calibration", "setting": "Level 4-5", "description": "Prevent vdroop under load"},
            {"name": "C-States", "setting": "Disabled", "description": "Disable for maximum performance"},
            {"name": "Intel SpeedStep/AMD Cool'n'Quiet", "setting": "Disabled", "description": "Disable for consistent clocks"},
            {"name": "Turbo Boost", "setting": "Enabled", "description": "Keep turbo enabled for burst performance"},
            {"name": "Memory Frequency", "setting": "Maximum Supported", "description": "Run RAM at rated XMP speed"},
            {"name": "PCIe Link Speed", "setting": "Gen 4/5", "description": "Ensure GPU runs at full bandwidth"},
        ]
    
    def _msi_recommendations(self) -> List[Dict[str, Any]]:
        return [
            {"name": "DRAM XMP", "setting": "Enabled", "description": "Enable memory XMP profile"},
            {"name": "CPU Ratio", "setting": "All Core", "description": "Synchronize all cores"},
            {"name": "CPU Voltage Mode", "setting": "Offset Mode", "description": "Use offset voltage"},
            {"name": "LLC", "setting": "Mode 3", "description": "Balanced load-line calibration"},
            {"name": "C-States", "setting": "Disabled", "description": "Disable for performance"},
            {"name": "Intel SpeedStep", "setting": "Disabled", "description": "Disable for consistent clocks"},
            {"name": "Turbo Boost", "setting": "Enabled", "description": "Keep turbo enabled"},
        ]
    
    def _gigabyte_recommendations(self) -> List[Dict[str, Any]]:
        return [
            {"name": "XMP Profile", "setting": "Profile 1", "description": "Enable rated memory speed"},
            {"name": "CPU Clock Ratio", "setting": "All Core", "description": "Synchronize all cores"},
            {"name": "CPU Vcore", "setting": "Adaptive + Offset", "description": "Adaptive voltage with offset"},
            {"name": "Load Line Calibration", "setting": "High", "description": "Prevent voltage droop"},
            {"name": "Global C-State Control", "setting": "Disabled", "description": "Disable C-states"},
            {"name": "Intel Speed Shift", "setting": "Disabled", "description": "Disable for performance"},
        ]
    
    def _asrock_recommendations(self) -> List[Dict[str, Any]]:
        return [
            {"name": "Load XMP Setting", "setting": "Profile 1", "description": "Enable XMP"},
            {"name": "CPU Ratio", "setting": "All Core", "description": "Sync all cores"},
            {"name": "CPU Vcore", "setting": "Offset", "description": "Use offset voltage"},
            {"name": "LLC", "setting": "Level 3", "description": "Balanced LLC"},
            {"name": "C-States", "setting": "Disabled", "description": "Disable for performance"},
        ]
    
    def _generic_recommendations(self) -> List[Dict[str, Any]]:
        return [
            {"name": "XMP/DOCP", "setting": "Enabled", "description": "Enable memory profile for rated speed"},
            {"name": "CPU Core Sync", "setting": "All Cores", "description": "Synchronize all core ratios"},
            {"name": "C-States", "setting": "Disabled", "description": "Disable for maximum performance"},
            {"name": "Intel SpeedStep/AMD Cool'n'Quiet", "setting": "Disabled", "description": "Disable for consistent clocks"},
            {"name": "Turbo Boost", "setting": "Enabled", "description": "Keep turbo enabled"},
            {"name": "PCIe Gen", "setting": "Max Supported", "description": "Ensure full GPU bandwidth"},
        ]
    
    def apply_settings(self, settings: List[Dict[str, Any]]) -> Dict[str, Any]:
        if self.os_type != "windows":
            return {"success": False, "message": "BIOS settings can only be viewed on Windows. Apply manually in BIOS."}
        
        return {
            "success": False,
            "message": "BIOS settings must be applied manually in BIOS/UEFI. Use the recommendations above as a guide.",
            "settings": settings,
            "instructions": [
                "Restart PC and enter BIOS (usually F2, Del, or F12)",
                "Navigate to Advanced/Overclocking section",
                "Apply each recommended setting",
                "Save and exit (F10)",
                "Test stability with stress tests"
            ]
        }

if __name__ == "__main__":
    bios = BIOSOptimizer(platform.system())
    print(json.dumps(bios.get_bios_info(), indent=2))
    print("\nRecommendations:")
    for rec in bios.get_recommended_settings():
        print(f"  {rec['name']}: {rec['setting']} - {rec['description']}")