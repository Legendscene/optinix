import subprocess
import json
import os


class DriverManager:
    def __init__(self, os_type):
        self.os_type = os_type

    def scan_drivers(self):
        drivers = []
        if self.os_type == "windows":
            drivers = self._scan_windows_drivers()
        elif self.os_type == "linux":
            drivers = self._scan_linux_drivers()
        elif self.os_type == "macos":
            drivers = self._scan_macos_drivers()
        return drivers

    def check_updates(self):
        results = []
        if self.os_type == "windows":
            results = self._check_windows_updates()
        return results

    def get_driver_links(self):
        return {
            "nvidia": "https://www.nvidia.com/Download/index.aspx",
            "amd": "https://www.amd.com/en/support",
            "intel": "https://www.intel.com/content/www/us/en/download-center/home.html",
            "realtek_audio": "https://www.realtek.com/en/component/zoo/category/pc-audio-codecs-high-definition-audio-codecs-software",
            "realtek_network": "https://www.realtek.com/en/component/zoo/category/network-interface-controllers-10-100-1000m-gigabit-ethernet-pci-express-software",
            "qualcomm_wifi": "https://www.qualcomm.com/products/connectivity/wi-fi",
            "broadcom_wifi": "https://www.broadcom.com/site-home/p/pc/wireless-lan-network-adapters",
            "intel_wifi": "https://www.intel.com/content/www/us/en/products/details/wireless/wi-fi-adapters.html",
            "amd_chipset": "https://www.amd.com/en/support/chipsets",
            "intel_chipset": "https://www.intel.com/content/www/us/en/download-center/home.html",
            "microsoft_update": "https://support.microsoft.com/en-us/topic/windows-update-drivers-background-23f799a3-44c7-5d19-68d4-e43801f63604"
        }

    def get_missing_drivers(self):
        missing = []
        if self.os_type == "windows":
            try:
                r = subprocess.run(
                    ["powershell", "-Command",
                     "Get-PnpDevice | Where-Object {$_.Status -ne 'OK'} | "
                     "Select-Object Class, FriendlyName, Status, InstanceId | ConvertTo-Json"],
                    capture_output=True, text=True, timeout=15
                )
                if r.stdout.strip():
                    devices = json.loads(r.stdout)
                    if isinstance(devices, dict):
                        devices = [devices]
                    for d in devices:
                        missing.append({
                            "class": d.get("Class", "Unknown"),
                            "name": d.get("FriendlyName", "Unknown Device"),
                            "status": d.get("Status", "Unknown"),
                            "id": d.get("InstanceId", "")
                        })
            except Exception:
                pass

            try:
                r = subprocess.run(
                    ["powershell", "-Command",
                     "Get-PnpDevice | Where-Object {$_.Class -eq 'Unknown' -or $_.Status -eq 'Error'} | "
                     "Select-Object Class, FriendlyName, Status | ConvertTo-Json"],
                    capture_output=True, text=True, timeout=15
                )
                if r.stdout.strip():
                    devices = json.loads(r.stdout)
                    if isinstance(devices, dict):
                        devices = [devices]
                    for d in devices:
                        if not any(m["name"] == d.get("FriendlyName") for m in missing):
                            missing.append({
                                "class": d.get("Class", "Unknown"),
                                "name": d.get("FriendlyName", "Unknown Device"),
                                "status": d.get("Status", "Unknown"),
                                "id": ""
                            })
            except Exception:
                pass

        return missing

    def _scan_windows_drivers(self):
        drivers = []
        try:
            r = subprocess.run(
                ["powershell", "-Command",
                 "Get-WmiObject Win32_PnPSignedDriver | Where-Object {$_.DriverVersion} | "
                 "Select-Object DeviceName, DriverVersion, DriverDate, Manufacturer, DeviceClass | "
                 "Sort-Object DeviceClass | ConvertTo-Json"],
                capture_output=True, text=True, timeout=30
            )
            if r.stdout.strip():
                data = json.loads(r.stdout)
                if isinstance(data, dict):
                    data = [data]
                for d in data:
                    drivers.append({
                        "name": d.get("DeviceName", "Unknown"),
                        "version": d.get("DriverVersion", "N/A"),
                        "date": d.get("DriverDate", "N/A"),
                        "manufacturer": d.get("Manufacturer", "Unknown"),
                        "class": d.get("DeviceClass", "Unknown"),
                        "download_url": self._get_download_url(d.get("DeviceClass", ""), d.get("Manufacturer", ""))
                    })
        except Exception:
            pass
        return drivers

    def _scan_linux_drivers(self):
        drivers = []
        try:
            r = subprocess.run(["lsmod"], capture_output=True, text=True, timeout=5)
            for line in r.stdout.strip().split("\n")[1:]:
                parts = line.split()
                if len(parts) >= 3:
                    drivers.append({
                        "name": parts[0],
                        "size": parts[1],
                        "used_by": parts[2] if len(parts) > 2 else "0",
                        "class": "kernel_module",
                        "download_url": ""
                    })
        except Exception:
            pass
        return drivers

    def _scan_macos_drivers(self):
        drivers = []
        try:
            r = subprocess.run(["system_profiler", "SPExtensionsDataType", "-json"],
                             capture_output=True, text=True, timeout=15)
            if r.stdout:
                data = json.loads(r.stdout)
                for ext in data.get("SPExtensionsDataType", [])[:20]:
                    drivers.append({
                        "name": ext.get("_name", "Unknown"),
                        "version": ext.get("version", "N/A"),
                        "class": "kext",
                        "manufacturer": ext.get("developer", "Unknown"),
                        "download_url": ""
                    })
        except Exception:
            pass
        return drivers

    def _check_windows_updates(self):
        results = []
        try:
            r = subprocess.run(
                ["powershell", "-Command",
                 "Get-WindowsDriver -Online | Where-Object {$_.Date} | "
                 "Sort-Object Date -Descending | Select-Object -First 10 "
                 "ClassName, ProviderName, Date, Version, OriginalFileName | ConvertTo-Json"],
                capture_output=True, text=True, timeout=30
            )
            if r.stdout.strip():
                data = json.loads(r.stdout)
                if isinstance(data, dict):
                    data = [data]
                for d in data:
                    results.append({
                        "class": d.get("ClassName", ""),
                        "provider": d.get("ProviderName", ""),
                        "date": str(d.get("Date", "")),
                        "version": d.get("Version", ""),
                        "file": d.get("OriginalFileName", "")
                    })
        except Exception:
            pass
        return results

    def _get_download_url(self, device_class, manufacturer):
        class_lower = device_class.lower() if device_class else ""
        mfg_lower = manufacturer.lower() if manufacturer else ""

        if "display" in class_lower or "video" in class_lower:
            if "nvidia" in mfg_lower:
                return "https://www.nvidia.com/Download/index.aspx"
            elif "amd" in mfg_lower or "ati" in mfg_lower or "radeon" in mfg_lower:
                return "https://www.amd.com/en/support"
            elif "intel" in mfg_lower:
                return "https://www.intel.com/content/www/us/en/download-center/home.html"
            return "https://www.intel.com/content/www/us/en/download-center/home.html"

        elif "net" in class_lower:
            if "realtek" in mfg_lower:
                return "https://www.realtek.com/en/component/zoo/category/network-interface-controllers-10-100-1000m-gigabit-ethernet-pci-express-software"
            elif "intel" in mfg_lower:
                return "https://www.intel.com/content/www/us/en/products/details/wireless/wi-fi-adapters.html"
            elif "qualcomm" in mfg_lower or "atheros" in mfg_lower:
                return "https://www.qualcomm.com/products/connectivity/wi-fi"
            elif "broadcom" in mfg_lower:
                return "https://www.broadcom.com/site-home/p/pc/wireless-lan-network-adapters"
            return "https://www.intel.com/content/www/us/en/download-center/home.html"

        elif "audio" in class_lower or "media" in class_lower:
            if "realtek" in mfg_lower:
                return "https://www.realtek.com/en/component/zoo/category/pc-audio-codecs-high-definition-audio-codecs-software"
            return "https://www.realtek.com/en/component/zoo/category/pc-audio-codecs-high-definition-audio-codecs-software"

        elif "usb" in class_lower or "hid" in class_lower:
            return "https://www.intel.com/content/www/us/en/download-center/home.html"

        elif "storage" in class_lower or "disk" in class_lower:
            return "https://www.intel.com/content/www/us/en/download-center/home.html"

        return ""
