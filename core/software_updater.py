import os
import re
import subprocess
import json
import urllib.request
import tempfile
from datetime import datetime
from typing import List, Dict, Optional

class SoftwareUpdater:
    """Detects outdated software and provides update capability."""

    def __init__(self, os_type: str = "windows"):
        self.os_type = os_type
        self.software: List[Dict] = []

    def _get_installed_software(self) -> List[Dict]:
        """Get list of installed software from registry."""
        apps = []
        if self.os_type != "windows":
            return apps

        paths = [
            r"HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall",
            r"HKLM\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
        ]
        for path in paths:
            try:
                r = subprocess.run(
                    ["reg", "query", path, "/s", "/f", "DisplayName", "/t", "REG_SZ", "/e"],
                    capture_output=True, text=True, timeout=30
                )
                lines = r.stdout.split("\n")
                current_key = ""
                name = ""
                version = ""
                for line in lines:
                    line = line.strip()
                    if line.startswith("HKEY_"):
                        current_key = line
                        name = ""
                        version = ""
                    elif "DisplayName" in line and "REG_SZ" in line:
                        name = line.split("REG_SZ")[-1].strip()
                    elif "DisplayVersion" in line and "REG_SZ" in line:
                        version = line.split("REG_SZ")[-1].strip()
                    elif not line and name:
                        if name and version:
                            apps.append({"name": name, "version": version, "key": current_key})
                        name = ""
                        version = ""
            except:
                pass

        return apps

    def _common_apps_db(self) -> Dict:
        """Built-in database of common software and their latest versions."""
        return {
            "google chrome": {"latest": "148.0.5961.0", "url": "https://www.google.com/chrome/"},
            "mozilla firefox": {"latest": "150.0.1", "url": "https://www.mozilla.org/firefox/"},
            "microsoft edge": {"latest": "148.0.2427.0", "url": "https://www.microsoft.com/edge"},
            "7-zip": {"latest": "24.09", "url": "https://www.7-zip.org/"},
            "vlc media player": {"latest": "3.0.21", "url": "https://www.videolan.org/vlc/"},
            "discord": {"latest": "1.0.9182", "url": "https://discord.com/download"},
            "spotify": {"latest": "1.2.62.472", "url": "https://www.spotify.com/download/"},
            "notepad++": {"latest": "8.7.5", "url": "https://notepad-plus-plus.org/downloads/"},
            "libreoffice": {"latest": "25.2.3", "url": "https://www.libreoffice.org/download/"},
            "gimp": {"latest": "2.10.38", "url": "https://www.gimp.org/downloads/"},
            "python": {"latest": "3.13.3", "url": "https://www.python.org/downloads/"},
            "node.js": {"latest": "22.14.0", "url": "https://nodejs.org/"},
            "git": {"latest": "2.49.0", "url": "https://git-scm.com/downloads"},
            "obs studio": {"latest": "31.0.3", "url": "https://obsproject.com/download"},
            "steam": {"latest": "1.0.0.82", "url": "https://store.steampowered.com/about/"},
            "visual studio code": {"latest": "1.100.0", "url": "https://code.visualstudio.com/download"},
            "adobe acrobat reader": {"latest": "24.005.20408", "url": "https://get.adobe.com/reader/"},
            "java": {"latest": "8.0.4410.1", "url": "https://www.java.com/download/"},
            "powertoys": {"latest": "0.89.0", "url": "https://github.com/microsoft/PowerToys/releases"},
            "everything": {"latest": "1.4.1.1026", "url": "https://www.voidtools.com/"},
            "cpu-z": {"latest": "2.14", "url": "https://www.cpuid.com/softwares/cpu-z.html"},
            "gpu-z": {"latest": "2.62", "url": "https://www.techpowerup.com/gpuz/"},
            "hwmonitor": {"latest": "7.76", "url": "https://www.cpuid.com/softwares/hwmonitor.html"},
            "ccleaner": {"latest": "6.33.11488", "url": "https://www.ccleaner.com/"},
            "malwarebytes": {"latest": "5.2.6.151", "url": "https://www.malwarebytes.com/"},
        }

    def _parse_version(self, v: str):
        """Parse version string into comparable tuple."""
        try:
            parts = re.findall(r'\d+', v)
            return tuple(int(x) for x in parts)
        except:
            return (0,)

    def scan(self) -> List[Dict]:
        """Scan installed software and check for updates."""
        installed = self._get_installed_software()
        db = self._common_apps_db()

        self.software = []
        for app in installed:
            name = app["name"]
            version = app["version"]

            matched = None
            for key, info in db.items():
                if key.lower() in name.lower() or name.lower() in key.lower():
                    matched = (key, info)
                    break

            if matched:
                key, info = matched
                current_ver = self._parse_version(version)
                latest_ver = self._parse_version(info["latest"])

                entry = {
                    "name": name,
                    "current_version": version,
                    "latest_version": info["latest"],
                    "update_available": current_ver < latest_ver,
                    "download_url": info["url"],
                    "category": self._categorize(name)
                }
            else:
                entry = {
                    "name": name,
                    "current_version": version,
                    "latest_version": "",
                    "update_available": False,
                    "download_url": "",
                    "category": "Other"
                }

            self.software.append(entry)

        self.software.sort(key=lambda x: (not x["update_available"], x["name"].lower()))
        return self.software

    def _categorize(self, name: str) -> str:
        n = name.lower()
        if any(x in n for x in ["browser", "chrome", "firefox", "edge", "opera"]):
            return "Browser"
        if any(x in n for x in ["driver", "nvidia", "amd", "intel"]):
            return "Driver"
        if any(x in n for x in ["adobe", "reader", "office", "word", "excel"]):
            return "Productivity"
        if any(x in n for x in ["game", "steam", "discord", "spotify"]):
            return "Entertainment"
        if any(x in n for x in ["visual studio", "python", "node", "git", "code"]):
            return "Development"
        if any(x in n for x in ["security", "antivirus", "malware", "defender"]):
            return "Security"
        if any(x in n for x in ["utility", "tool", "cpu-z", "gpu-z", "7-zip"]):
            return "Utility"
        return "Other"

    def get_updates_summary(self) -> Dict:
        if not self.software:
            self.scan()
        total = len(self.software)
        updates = sum(1 for s in self.software if s.get("update_available"))
        return {
            "total": total,
            "updates_available": updates,
            "up_to_date": total - updates,
            "software": self.software[:50]
        }
