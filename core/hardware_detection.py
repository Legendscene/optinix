import os
import sys
import platform
import subprocess
import psutil
import ctypes
from typing import Dict, Any, Optional


class HardwareDetector:
    def __init__(self):
        self._info: Optional[Dict[str, Any]] = None
        self._laptop: Optional[bool] = None
        self._cpu_vendor: Optional[str] = None
        self._gpu_vendor: Optional[str] = None
        self._is_admin: Optional[bool] = None

    def _run(self, cmd, timeout=10):
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except:
            return type('', (), {'returncode': -1, 'stdout': '', 'stderr': ''})()

    def detect_cpu_vendor(self) -> str:
        if self._cpu_vendor:
            return self._cpu_vendor
        try:
            r = self._run(["powershell", "-NoProfile", "-Command",
                "(Get-CimInstance Win32_Processor).Name"], timeout=5)
            name = r.stdout.strip()
            if not name:
                name = platform.processor() or ""
            upper = name.upper()
            if "INTEL" in upper:
                self._cpu_vendor = "intel"
            elif "AMD" in upper:
                self._cpu_vendor = "amd"
            elif "ARM" in upper:
                self._cpu_vendor = "arm"
            else:
                self._cpu_vendor = "unknown"
        except:
            self._cpu_vendor = "unknown"
        return self._cpu_vendor

    def detect_cpu_cores(self) -> Dict[str, int]:
        return {
            "physical": psutil.cpu_count(logical=False) or 1,
            "logical": psutil.cpu_count(logical=True) or 1,
        }

    def detect_gpu_vendor(self) -> str:
        if self._gpu_vendor:
            return self._gpu_vendor
        try:
            r = self._run(["wmic", "path", "Win32_VideoController", "get", "Name"], timeout=5)
            for line in r.stdout.splitlines()[1:]:
                name = line.strip()
                if name:
                    upper = name.upper()
                    if "NVIDIA" in upper:
                        self._gpu_vendor = "nvidia"
                    elif "AMD" in upper or "RADEON" in upper:
                        self._gpu_vendor = "amd"
                    elif "INTEL" in upper:
                        self._gpu_vendor = "intel"
                    elif "MICROSOFT" not in upper:
                        self._gpu_vendor = "unknown"
                    if self._gpu_vendor != "unknown":
                        break
            if not self._gpu_vendor:
                self._gpu_vendor = "none"
        except:
            self._gpu_vendor = "unknown"
        return self._gpu_vendor

    def detect_laptop(self) -> bool:
        if self._laptop is not None:
            return self._laptop
        try:
            r = self._run(["powershell", "-NoProfile", "-Command",
                "Get-CimInstance -ClassName Win32_Battery | Measure-Object | Select-Object -ExpandProperty Count"],
                timeout=5)
            self._laptop = int(r.stdout.strip()) > 0 if r.stdout.strip().isdigit() else False
        except:
            self._laptop = False
        return self._laptop

    def detect_disk_type(self) -> Dict[str, Any]:
        ssd = False
        hdd = False
        try:
            r = self._run(["powershell", "-NoProfile", "-Command",
                "Get-PhysicalDisk | Select-Object MediaType, Size | ConvertTo-Json -Compress"],
                timeout=10)
            import json
            data = json.loads(r.stdout) if r.stdout.strip() else []
            if isinstance(data, dict):
                data = [data]
            for disk in data:
                mt = str(disk.get("MediaType", "")).lower() if isinstance(disk, dict) else ""
                if "ssd" in mt or mt == "4":
                    ssd = True
                elif "hdd" in mt or mt == "3":
                    hdd = True
        except:
            try:
                r = self._run(["wmic", "diskdrive", "get", "MediaType"], timeout=5)
                for line in r.stdout.splitlines()[1:]:
                    line = line.strip()
                    if "SSD" in line or "Solid State" in line:
                        ssd = True
                    elif "HDD" in line or "Fixed" in line:
                        hdd = True
            except:
                pass
        return {"is_ssd": ssd, "is_hdd": hdd, "type": "ssd" if ssd else ("hdd" if hdd else "unknown")}

    def detect_windows_version(self) -> Dict[str, str]:
        release = platform.release()
        version = platform.version()
        build = version.split(".")[-1] if "." in version else version
        is_win11 = False
        is_win10 = False
        try:
            r = self._run(["powershell", "-NoProfile", "-Command",
                "(Get-ItemProperty 'HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion').ProductName"],
                timeout=5)
            product = r.stdout.strip()
            is_win11 = "Windows 11" in product or "Windows 10" not in product
            is_win10 = "Windows 10" in product
        except:
            try:
                build_num = int(build)
                is_win11 = build_num >= 22000
                is_win10 = 10240 <= build_num < 22000
            except:
                pass
        return {
            "release": release,
            "version": version,
            "build": build,
            "is_win11": is_win11,
            "is_win10": is_win10,
            "product": product if 'product' in dir() else f"Windows {release}"
        }

    def detect_admin(self) -> bool:
        if self._is_admin is not None:
            return self._is_admin
        try:
            self._is_admin = os.name == 'nt' and ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            self._is_admin = False
        return self._is_admin

    def detect_power_plan(self) -> Dict[str, Any]:
        try:
            r = self._run(["powercfg", "/getactivescheme"], timeout=5)
            if r.returncode == 0 and ":" in r.stdout:
                parts = r.stdout.split(":")
                guid = parts[1].strip().split()[0] if len(parts) > 1 else ""
                name = parts[1].strip().split("(", 1)[-1].rstrip(")") if "(" in parts[1] else ""
                return {"guid": guid, "name": name, "is_high_performance": "High Performance" in r.stdout or "Ultimate" in r.stdout}
        except:
            pass
        return {"guid": "", "name": "", "is_high_performance": False}

    def detect_vm(self) -> bool:
        indicators = [
            "vbox", "vmware", "virtual", "hyper-v", "qemu", "kvm",
            "xen", "parallels", "docker"
        ]
        try:
            r = self._run(["powershell", "-NoProfile", "-Command",
                "(Get-CimInstance Win32_ComputerSystem).Model"], timeout=5)
            model = r.stdout.strip().lower()
            for ind in indicators:
                if ind in model:
                    return True
        except:
            pass
        try:
            r = self._run(["powershell", "-NoProfile", "-Command",
                "(Get-CimInstance Win32_ComputerSystem).Manufacturer"], timeout=5)
            mfr = r.stdout.strip().lower()
            for ind in indicators:
                if ind in mfr:
                    return True
        except:
            pass
        return False

    def detect_secure_boot(self) -> Optional[bool]:
        try:
            r = self._run(["powershell", "-NoProfile", "-Command",
                "Confirm-SecureBootUEFI"], timeout=5)
            return "True" in r.stdout
        except:
            return None

    def detect_tpm(self) -> Dict[str, Any]:
        try:
            r = self._run(["powershell", "-NoProfile", "-Command",
                "$tpm=Get-CimInstance -Namespace 'Root/CIMv2/Security/MicrosoftTpm' -ClassName Win32_Tpm 2>$null; if($tpm){$tpm.IsEnabled_InitialValue}else{$false}"],
                timeout=5)
            enabled = "True" in r.stdout
            return {"present": True, "enabled": enabled}
        except:
            return {"present": False, "enabled": False}

    def detect_ram(self) -> Dict[str, Any]:
        try:
            m = psutil.virtual_memory()
            return {
                "total_gb": round(m.total / (1024**3), 1),
                "available_gb": round(m.available / (1024**3), 1),
                "used_gb": round(m.used / (1024**3), 1),
                "percent": m.percent,
            }
        except:
            return {"total_gb": 0, "available_gb": 0, "used_gb": 0, "percent": 0}

    def detect_all(self) -> Dict[str, Any]:
        if self._info:
            return self._info
        cores = self.detect_cpu_cores()
        disk = self.detect_disk_type()
        win = self.detect_windows_version()
        tpm = self.detect_tpm()
        self._info = {
            "cpu": {
                "vendor": self.detect_cpu_vendor(),
                "physical_cores": cores["physical"],
                "logical_cores": cores["logical"],
                "brand": platform.processor(),
            },
            "gpu": {
                "vendor": self.detect_gpu_vendor(),
            },
            "ram": self.detect_ram(),
            "disk": disk,
            "system": {
                "is_laptop": self.detect_laptop(),
                "is_vm": self.detect_vm(),
                "is_admin": self.detect_admin(),
                "os": win,
            },
            "power_plan": self.detect_power_plan(),
            "security": {
                "secure_boot": self.detect_secure_boot(),
                "tpm": tpm,
            },
        }
        return self._info

    def check_compatibility(self, requirements: Dict[str, Any]) -> Dict[str, str]:
        info = self.detect_all()
        results = {}

        cpu_req = requirements.get("cpu_vendor", "")
        if cpu_req:
            actual = info["cpu"]["vendor"]
            results["cpu_vendor"] = "pass" if actual == cpu_req else f"fail: needs {cpu_req}, has {actual}"

        gpu_req = requirements.get("gpu_vendor", "")
        if gpu_req:
            actual = info["gpu"]["vendor"]
            results["gpu_vendor"] = "pass" if actual == gpu_req else f"fail: needs {gpu_req}, has {actual}"

        if requirements.get("laptop_only"):
            results["laptop"] = "pass" if info["system"]["is_laptop"] else "fail: Desktop detected, laptop-only optimization"
        if requirements.get("desktop_only"):
            results["desktop"] = "pass" if not info["system"]["is_laptop"] else "fail: Laptop detected, desktop-only optimization"

        if requirements.get("ssd_only"):
            results["ssd"] = "pass" if info["disk"]["is_ssd"] else "fail: HDD detected, SSD-only optimization"

        if requirements.get("hdd_only"):
            results["hdd"] = "pass" if info["disk"]["is_hdd"] else "fail: SSD detected, HDD-only optimization"

        admin_req = requirements.get("admin_required")
        if admin_req:
            results["admin"] = "pass" if info["system"]["is_admin"] else "fail: Administrator privileges required"

        win_req = requirements.get("min_win_build", 0)
        try:
            build = int(info["system"]["os"].get("build", "0"))
            results["win_build"] = "pass" if build >= win_req else f"fail: needs build >= {win_req}, has {build}"
        except:
            results["win_build"] = "fail: cannot determine Windows build"

        ram_req = requirements.get("min_ram_gb", 0)
        if ram_req:
            results["ram"] = "pass" if info["ram"]["total_gb"] >= ram_req else f"fail: needs {ram_req}GB RAM, has {info['ram']['total_gb']}GB"

        cores_req = requirements.get("min_cores", 0)
        if cores_req:
            actual = info["cpu"]["physical_cores"]
            results["cores"] = "pass" if actual >= cores_req else f"fail: needs {cores_req} cores, has {actual}"

        vm_req = requirements.get("vm_allowed")
        if vm_req is not None:
            is_vm = info["system"]["is_vm"]
            if vm_req and not is_vm:
                results["vm"] = "warn: not running in VM, but optimization targets VMs"
            elif not vm_req and is_vm:
                results["vm"] = "fail: running in VM, optimization not compatible"

        return results
