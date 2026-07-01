import os
import json
import subprocess
import platform
import re
import urllib.request
import tempfile
from datetime import datetime
from typing import List, Dict, Optional


class DriverUpdater:
    """Detects outdated drivers and can download/install updates."""

    def __init__(self, os_type: str = "windows"):
        self.os_type = os_type
        self.drivers: List[Dict] = []
        self._known_drivers_db = self._build_driver_db()

    def _build_driver_db(self) -> Dict:
        """Built-in database of known driver versions and sources."""
        return {
            "nvidia": {
                "name": "NVIDIA Graphics Driver",
                "url": "https://www.nvidia.com/download/driverResults.aspx/{id}/",
                "latest_version": "572.83",
                "date": "2026-06-15",
                "type": "GPU",
            },
            "amd_gpu": {
                "name": "AMD Graphics Driver",
                "url": "https://www.amd.com/en/support",
                "latest_version": "25.5.1",
                "date": "2026-06-01",
                "type": "GPU",
            },
            "intel_graphics": {
                "name": "Intel Graphics Driver",
                "url": "https://www.intel.com/content/www/us/en/download-center/home.html",
                "latest_version": "31.0.101.5768",
                "date": "2026-05-20",
                "type": "GPU",
            },
            "realtek_audio": {
                "name": "Realtek Audio Driver",
                "url": "https://www.realtek.com/en/downloads",
                "latest_version": "6.0.1.9874",
                "date": "2026-04-10",
                "type": "Audio",
            },
            "intel_network": {
                "name": "Intel Network Adapter Driver",
                "url": "https://www.intel.com/content/www/us/en/download/18693/",
                "latest_version": "28.3",
                "date": "2026-05-05",
                "type": "Network",
            },
            "realtek_network": {
                "name": "Realtek PCIe Network Driver",
                "url": "https://www.realtek.com/en/component/zoo/category/network-interface-controllers-10-100-1000m-gigabit-ethernet-pci-express-software",
                "latest_version": "10.73",
                "date": "2026-03-15",
                "type": "Network",
            },
            "chipset": {
                "name": "Chipset Driver",
                "url": "https://www.amd.com/en/support/chipsets",
                "latest_version": "6.10.17.152",
                "date": "2026-05-28",
                "type": "Chipset",
            },
            "bluetooth": {
                "name": "Bluetooth Driver",
                "url": "https://www.intel.com/content/www/us/en/download/18612/",
                "latest_version": "23.60.0.1",
                "date": "2026-04-20",
                "type": "Bluetooth",
            },
            "wifi": {
                "name": "Wi-Fi Driver",
                "url": "https://www.intel.com/content/www/us/en/download/19351/",
                "latest_version": "23.60.1.2",
                "date": "2026-06-01",
                "type": "Network",
            },
        }

    def scan(self) -> List[Dict]:
        """Scan system and detect installed drivers with versions."""
        self.drivers = []
        if self.os_type != "windows":
            return self.drivers

        # Detect via wmic
        try:
            r = subprocess.run(
                [
                    "wmic",
                    "path",
                    "win32_PnPSignedDriver",
                    "get",
                    "DeviceName,DriverVersion,DriverDate,Manufacturer,DeviceID",
                    "/format:csv",
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
            for line in r.stdout.strip().split("\n")[1:]:
                if not line.strip():
                    continue
                parts = [x.strip() for x in line.split(",") if x.strip()]
                if len(parts) >= 5:
                    device_name = parts[1] if len(parts) > 1 else ""
                    version = parts[2] if len(parts) > 2 else ""
                    date = parts[3] if len(parts) > 3 else ""
                    manufacturer = parts[4] if len(parts) > 4 else ""
                    device_id = parts[5] if len(parts) > 5 else ""

                    drv = {
                        "name": device_name,
                        "version": version,
                        "date": date,
                        "manufacturer": manufacturer,
                        "device_id": device_id,
                        "category": self._categorize(device_name, manufacturer),
                        "outdated": False,
                        "latest_version": "",
                        "update_available": False,
                    }
                    self.drivers.append(drv)
        except Exception:
            pass

        # Also detect GPU via nvidia-smi
        try:
            r = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if r.returncode == 0 and r.stdout.strip():
                parts = [x.strip() for x in r.stdout.strip().split(", ")]
                gpu_name, gpu_ver = parts[0], parts[1] if len(parts) > 1 else ""
                existing = next(
                    (d for d in self.drivers if gpu_name.lower() in d["name"].lower()),
                    None,
                )
                if not existing:
                    self.drivers.append(
                        {
                            "name": gpu_name,
                            "version": gpu_ver,
                            "date": "",
                            "manufacturer": "NVIDIA Corporation",
                            "device_id": "",
                            "category": "GPU",
                            "outdated": False,
                            "latest_version": "",
                            "update_available": False,
                        }
                    )
        except Exception:
            pass

        # Check against known database
        self._check_updates()

        return self.drivers

    def _categorize(self, name: str, manufacturer: str) -> str:
        n = name.lower()
        if any(x in n for x in ["nvidia", "geforce", "gtx", "rtx"]):
            return "GPU"
        if any(x in n for x in ["amd", "radeon"]):
            return "GPU"
        if any(x in n for x in ["intel graphics", "hd graphics", "iris"]):
            return "GPU"
        if any(x in n for x in ["realtek", "audio", "sound"]):
            return "Audio"
        if any(x in n for x in ["intel", "realtek"]) and any(
            x in n for x in ["network", "ethernet", "wifi", "wireless", "wi-fi"]
        ):
            return "Network"
        if any(x in n for x in ["bluetooth"]):
            return "Bluetooth"
        if any(x in n for x in ["chipset", "amd", "sata", "ahci"]):
            return "Chipset"
        if any(x in n for x in ["usb", "xbox", "hid"]):
            return "Input"
        if any(x in n for x in ["monitor", "display"]):
            return "Display"
        if any(x in n for x in ["printer", "scan"]):
            return "Printer"
        return "Other"

    def _check_updates(self):
        """Compare installed drivers against known latest versions."""
        for drv in self.drivers:
            for key, known in self._known_drivers_db.items():
                type_match = known["type"].lower() in drv["category"].lower()
                name_match = known["name"].lower().split()[0] in drv["name"].lower()
                if type_match or name_match:
                    drv["latest_version"] = known["latest_version"]
                    drv["latest_date"] = known["date"]
                    drv["download_url"] = known["url"]
                    try:
                        current = [int(x) for x in drv["version"].split(".")]
                        latest = [int(x) for x in known["latest_version"].split(".")]
                        while len(current) < len(latest):
                            current.append(0)
                        while len(latest) < len(current):
                            latest.append(0)
                        drv["outdated"] = current < latest
                        drv["update_available"] = current < latest
                    except Exception:
                        drv["outdated"] = False
                        drv["update_available"] = False
                    break

    def download_driver(self, driver_name: str) -> Dict:
        """Download a driver update (simulated - creates metadata file)."""
        drv = next((d for d in self.drivers if d["name"] == driver_name), None)
        if not drv:
            for key, known in self._known_drivers_db.items():
                if key == driver_name or known["name"] == driver_name:
                    drv = known
                    break
        if not drv:
            return {"success": False, "message": f"Driver '{driver_name}' not found"}

        dl_dir = os.path.join(tempfile.gettempdir(), "optinix_drivers")
        os.makedirs(dl_dir, exist_ok=True)

        filename = (
            f"{driver_name.replace(' ', '_').replace('/', '_')}"
            f"_v{drv.get('latest_version', 'latest')}.exe"
        )
        filepath = os.path.join(dl_dir, filename)

        meta = {
            "driver": driver_name,
            "version": drv.get("latest_version", "latest"),
            "url": drv.get("download_url", ""),
            "downloaded_at": datetime.now().isoformat(),
            "file": filepath,
        }
        with open(filepath + ".meta.json", "w") as f:
            json.dump(meta, f)
        with open(filepath, "w") as f:
            f.write(
                f"# Optinix Driver Package\n"
                f"# {driver_name} v{drv.get('latest_version', 'latest')}\n"
                f"# Download URL: {drv.get('download_url', '')}\n"
            )

        drv["downloaded"] = True
        drv["download_path"] = filepath

        return {
            "success": True,
            "message": f"Driver downloaded: {filename}",
            "path": filepath,
            "version": drv.get("latest_version", ""),
        }

    def install_driver(self, driver_name: str) -> Dict:
        """Install a downloaded driver (simulated)."""
        drv = next((d for d in self.drivers if d["name"] == driver_name), None)
        if not drv:
            return {"success": False, "message": f"Driver '{driver_name}' not found"}

        path = drv.get("download_path", "")
        if not path or not os.path.exists(path):
            result = self.download_driver(driver_name)
            if not result["success"]:
                return result
            path = result["path"]

        try:
            if path.endswith(".exe"):
                subprocess.run([path, "/S", "/silent"], capture_output=True, timeout=120)
            drv["installed"] = True
            drv["version"] = drv.get("latest_version", drv["version"])
            drv["update_available"] = False
            return {
                "success": True,
                "message": f"Installed: {driver_name} v{drv['version']}",
            }
        except Exception as e:
            return {"success": False, "message": f"Install failed: {e}"}

    def download_all(self) -> Dict:
        """Download all available updates."""
        results = []
        for drv in self.drivers:
            if drv.get("update_available"):
                r = self.download_driver(drv["name"])
                results.append(r)
        return {"success": True, "results": results}

    def install_all(self) -> Dict:
        """Install all downloaded drivers."""
        results = []
        for drv in self.drivers:
            if drv.get("downloaded"):
                r = self.install_driver(drv["name"])
                results.append(r)
        return {"success": True, "results": results}

    def get_scan_summary(self) -> Dict:
        drivers = self.drivers if self.drivers else self.scan()
        total = len(drivers)
        outdated = sum(1 for d in drivers if d.get("update_available"))
        up_to_date = total - outdated
        return {
            "total": total,
            "outdated": outdated,
            "up_to_date": up_to_date,
            "drivers": drivers,
        }
