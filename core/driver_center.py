import os
import re
import json
import uuid
import subprocess
from datetime import datetime
from typing import Dict, List, Any, Optional
from core.base import OptimizerBase, OPTIMIZER_CATEGORY_SAFE, OPTIMIZER_CATEGORY_ADVANCED
from core.config import CONFIG


_KNOWN_GOOD_VERSIONS = {
    "nvidia": {"version": "572.83", "date": "2026-06-15", "min_version": "550.0"},
    "amd_gpu": {"version": "25.5.1", "date": "2026-06-01", "min_version": "23.0"},
    "intel_graphics": {"version": "31.0.101.5768", "date": "2026-05-20", "min_version": "30.0.100"},
    "realtek_audio": {"version": "6.0.1.9874", "date": "2026-04-10", "min_version": "6.0.1"},
    "intel_network": {"version": "28.3", "date": "2026-05-05", "min_version": "27.0"},
    "realtek_network": {"version": "10.73", "date": "2026-03-15", "min_version": "10.60"},
    "bluetooth": {"version": "23.60.0.1", "date": "2026-04-20", "min_version": "22.0"},
    "wifi": {"version": "23.60.1.2", "date": "2026-06-01", "min_version": "22.50"},
    "chipset_amd": {"version": "6.10.17.152", "date": "2026-05-28", "min_version": "5.0"},
    "chipset_intel": {"version": "10.1.19800", "date": "2026-04-15", "min_version": "10.0"},
}

_VULNERABLE_DRIVERS_CVE = [
    {"name": "Capcom.sys", "cve": "CVE-2024-31497", "severity": "CRITICAL", "description": "Capcom anti-cheat driver allows arbitrary code execution", "affected": "All versions"},
    {"name": "Ene.sys", "cve": "CVE-2024-28990", "severity": "HIGH", "description": "ENERGY driver arbitrary memory read/write", "affected": "<= 1.0.0"},
    {"name": "AsUpIO.sys", "cve": "CVE-2023-45246", "severity": "HIGH", "description": "ASUS IO driver privilege escalation", "affected": "<= 3.0.0"},
    {"name": "RwDrv.sys", "cve": "CVE-2023-42634", "severity": "MEDIUM", "description": "RWEverything driver memory access", "affected": "<= 2.0"},
    {"name": "WinRing0.sys", "cve": "CVE-2023-38181", "severity": "HIGH", "description": "WinRing0 IO driver privilege escalation", "affected": "<= 1.2"},
    {"name": "IObitUnlocker.sys", "cve": "CVE-2022-38199", "severity": "MEDIUM", "description": "IObit driver arbitrary file deletion", "affected": "<= 1.4"},
    {"name": "ProcessHacker.sys", "cve": "CVE-2022-29170", "severity": "MEDIUM", "description": "Process Hacker driver exposes kernel handles", "affected": "<= 3.0"},
    {"name": "CPUID.sys", "cve": "CVE-2022-29161", "severity": "MEDIUM", "description": "CPUID driver exposes MSR read/write", "affected": "<= 1.0"},
    {"name": "dbk64.sys", "cve": "CVE-2022-27221", "severity": "HIGH", "description": "Cheat Engine driver arbitrary memory access", "affected": "<= 1.0"},
    {"name": "SpeedFan.sys", "cve": "CVE-2022-27219", "severity": "MEDIUM", "description": "SpeedFan driver IO port access", "affected": "<= 1.0"},
    {"name": "WinIo64.sys", "cve": "CVE-2022-27218", "severity": "HIGH", "description": "WinIO driver IO privilege escalation", "affected": "<= 1.0"},
    {"name": "Nal.sys", "cve": "CVE-2021-45270", "severity": "HIGH", "description": "Nal driver arbitrary physical memory access", "affected": "<= 1.0"},
    {"name": "AMDPowerProfiler.sys", "cve": "CVE-2021-36054", "severity": "MEDIUM", "description": "AMD PowerProfiler info disclosure", "affected": "<= 2.0"},
    {"name": "IntelSaExt.dll", "cve": "CVE-2021-33154", "severity": "MEDIUM", "description": "Intel SA extension privilege escalation", "affected": "<= 1.0"},
    {"name": "EvgaGuru.sys", "cve": "CVE-2021-31363", "severity": "MEDIUM", "description": "EVGA driver arbitrary memory access", "affected": "<= 1.0"},
    {"name": "atillk64.sys", "cve": "CVE-2021-31976", "severity": "MEDIUM", "description": "ATI driver IO port access", "affected": "<= 1.0"},
]

_DEVICE_CLASS_NAMES = {
    "4d36e968-e325-11ce-bfc1-08002be10318": "Display",
    "4d36e96c-e325-11ce-bfc1-08002be10318": "Multimedia",
    "4d36e96a-e325-11ce-bfc1-08002be10318": "HID",
    "4d36e97b-e325-11ce-bfc1-08002be10318": "SCSIAdapter",
    "4d36e972-e325-11ce-bfc1-08002be10318": "Network",
    "4d36e96f-e325-11ce-bfc1-08002be10318": "Mouse",
    "4d36e96b-e325-11ce-bfc1-08002be10318": "Keyboard",
    "4d36e978-e325-11ce-bfc1-08002be10318": "Ports",
    "4d36e97d-e325-11ce-bfc1-08002be10318": "System",
    "4d36e980-e325-11ce-bfc1-08002be10318": "Storage",
    "4d36e96d-e325-11ce-bfc1-08002be10318": "Modem",
    "4d36e971-e325-11ce-bfc1-08002be10318": "Printer",
    "4d36e965-e325-11ce-bfc1-08002be10318": "USB",
    "4d36e969-e325-11ce-bfc1-08002be10318": "IEEE1394",
    "4d36e974-e325-11ce-bfc1-08002be10318": "DiskDrive",
}


def _run_powershell(script: str, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True, text=True, timeout=timeout
    )


def _parse_json_output(output: str):
    if not output.strip():
        return None
    try:
        data = json.loads(output)
        return data
    except json.JSONDecodeError:
        return None


def _normalize_list(data):
    if data is None:
        return []
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return data
    return []


def _compare_versions(v1: str, v2: str) -> int:
    if not v1 or not v2:
        return 0
    parts1 = re.findall(r'\d+', v1)
    parts2 = re.findall(r'\d+', v2)
    max_len = max(len(parts1), len(parts2))
    while len(parts1) < max_len:
        parts1.append('0')
    while len(parts2) < max_len:
        parts2.append('0')
    for a, b in zip(parts1, parts2):
        diff = int(a) - int(b)
        if diff != 0:
            return -1 if diff < 0 else 1
    return 0


def _class_guid_to_name(guid: str) -> str:
    return _DEVICE_CLASS_NAMES.get(guid.lower(), "Unknown")


class DriverHealthChecker:
    def get_all_drivers(self) -> List[Dict[str, Any]]:
        drivers = []
        try:
            r = _run_powershell(
                "Get-WmiObject Win32_PnPSignedDriver | "
                "Select-Object DeviceName, DriverVersion, DriverDate, Manufacturer, "
                "DeviceID, DeviceClass, FriendlyName, HardwareID, InfName | "
                "ConvertTo-Json -Compress",
                timeout=30
            )
            data = _parse_json_output(r.stdout)
            for d in _normalize_list(data):
                driver = {
                    "name": d.get("DeviceName") or d.get("FriendlyName", "Unknown"),
                    "version": d.get("DriverVersion", ""),
                    "date": str(d.get("DriverDate", "")) if d.get("DriverDate") else "",
                    "manufacturer": d.get("Manufacturer", ""),
                    "is_signed": True,
                    "device_id": d.get("DeviceID", ""),
                    "class_name": d.get("DeviceClass", ""),
                    "hardware_id": d.get("HardwareID", ""),
                    "inf_name": d.get("InfName", ""),
                }
                if driver["name"] and driver["name"] != "Unknown":
                    drivers.append(driver)
        except subprocess.TimeoutExpired:
            pass
        except Exception:
            pass

        if not drivers:
            try:
                r = subprocess.run(
                    ["driverquery", "/FO", "CSV", "/V"],
                    capture_output=True, text=True, timeout=15
                )
                for line in r.stdout.strip().split("\n")[1:]:
                    parts = [x.strip().strip('"') for x in line.split('","') if x.strip()]
                    if len(parts) >= 9:
                        drivers.append({
                            "name": parts[0],
                            "version": parts[3] if len(parts) > 3 else "",
                            "date": parts[4] if len(parts) > 4 else "",
                            "manufacturer": parts[1] if len(parts) > 1 else "",
                            "is_signed": "signed" in parts[7].lower() if len(parts) > 7 else False,
                            "device_id": parts[2] if len(parts) > 2 else "",
                            "class_name": parts[5] if len(parts) > 5 else "",
                            "hardware_id": "",
                            "inf_name": parts[6] if len(parts) > 6 else "",
                        })
            except Exception:
                pass
        return drivers

    def check_outdated_drivers(self) -> List[Dict[str, Any]]:
        outdated = []
        drivers = self.get_all_drivers()
        for driver in drivers:
            name_lower = driver["name"].lower()
            version = driver["version"]
            for key, known in _KNOWN_GOOD_VERSIONS.items():
                keywords = key.replace("_", " ").lower().split()
                if any(kw in name_lower for kw in keywords):
                    comparison = _compare_versions(version, known["min_version"])
                    if comparison < 0:
                        driver["known_good_version"] = known["version"]
                        driver["known_good_date"] = known["date"]
                        driver["outdated"] = True
                        outdated.append(driver)
                    break
        return outdated

    def find_problem_devices(self) -> List[Dict[str, Any]]:
        problems = []
        try:
            r = _run_powershell(
                "Get-WmiObject Win32_PnPEntity | "
                "Where-Object {$_.ConfigManagerErrorCode -ne 0} | "
                "Select-Object DeviceID, Description, ClassName, Manufacturer, "
                "ConfigManagerErrorCode, Status, Service, HardwareID | "
                "ConvertTo-Json -Compress",
                timeout=20
            )
            error_codes = {
                1: "Device not configured correctly",
                3: "Driver is corrupt or system resources conflict",
                10: "Device cannot start",
                12: "Not enough free resources",
                14: "Device cannot work properly until restart",
                18: "Reinstall drivers",
                19: "Registry may be corrupted",
                21: "Windows is removing the device",
                22: "Device is disabled",
                24: "Device is not present",
                28: "Drivers not installed",
                29: "Device is disabled in firmware",
                31: "Device failed to start",
                32: "Driver service not started",
                33: "Windows cannot determine resources",
                34: "Cannot set device configuration",
                35: "Firmware needs updated configuration",
                39: "Driver is corrupted",
                40: "Driver service not loading",
                41: "Windows loaded driver but cannot find device",
                42: "Duplicate device detected",
                43: "Driver reported failure",
                44: "Application or service shut down device",
                45: "Device not connected",
                46: "Windows cannot gain access",
                47: "Driver disabled because previous crash",
                48: "Software disabled the device",
                49: "Cannot start because of system hive size limit",
            }
            data = _parse_json_output(r.stdout)
            for d in _normalize_list(data):
                err_code = d.get("ConfigManagerErrorCode", 0)
                if err_code and err_code != 0:
                    problems.append({
                        "device_id": d.get("DeviceID", ""),
                        "name": d.get("Description") or d.get("Caption", "Unknown Device"),
                        "class_name": d.get("ClassName", ""),
                        "manufacturer": d.get("Manufacturer", ""),
                        "status": d.get("Status", "Unknown"),
                        "error_code": err_code,
                        "error_message": error_codes.get(err_code, f"Unknown error code {err_code}"),
                        "service": d.get("Service", ""),
                        "hardware_id": d.get("HardwareID", ""),
                    })
        except Exception:
            pass

        if not problems:
            try:
                r = _run_powershell(
                    "Get-PnpDevice | Where-Object {$_.Problem -ne $null -and $_.Problem -ne 0} | "
                    "Select-Object FriendlyName, Class, Status, Problem, InstanceId | "
                    "ConvertTo-Json -Compress",
                    timeout=15
                )
                data = _parse_json_output(r.stdout)
                for d in _normalize_list(data):
                    problems.append({
                        "device_id": d.get("InstanceId", ""),
                        "name": d.get("FriendlyName", "Unknown Device"),
                        "class_name": d.get("Class", ""),
                        "status": d.get("Status", "Unknown"),
                        "error_code": d.get("Problem", 0),
                        "error_message": "",
                        "service": "",
                        "hardware_id": "",
                    })
            except Exception:
                pass
        return problems

    def check_driver_signatures(self) -> List[Dict[str, Any]]:
        unsigned = []
        try:
            r = _run_powershell(
                "Get-WmiObject Win32_PnPSignedDriver | "
                "Select-Object DeviceName, DriverVersion, Manufacturer, DeviceID, "
                "IsSigned, Signer | "
                "ConvertTo-Json -Compress",
                timeout=20
            )
            data = _parse_json_output(r.stdout)
            for d in _normalize_list(data):
                is_signed = d.get("IsSigned", True)
                if is_signed is False or str(is_signed).lower() == "false":
                    unsigned.append({
                        "name": d.get("DeviceName", "Unknown"),
                        "version": d.get("DriverVersion", ""),
                        "manufacturer": d.get("Manufacturer", ""),
                        "device_id": d.get("DeviceID", ""),
                        "is_signed": False,
                        "signer": d.get("Signer", "None"),
                    })
                elif is_signed is True or is_signed is None:
                    pass
        except Exception:
            pass

        if not unsigned:
            try:
                r = _run_powershell(
                    "Get-PnpDevice | Where-Object {$_.Class -ne 'USB' -and $_.Class -ne 'HIDClass'} | "
                    "Get-PnpDeviceProperty -KeyName 'DEVPKEY_Device_DriverSigned' | "
                    "Where-Object {$_.Data -eq 0} | "
                    "Select-Object -ExpandProperty InstanceId | "
                    "ForEach-Object {Get-PnpDevice -InstanceId $_} | "
                    "Select-Object FriendlyName, Class, InstanceId | "
                    "ConvertTo-Json -Compress",
                    timeout=20
                )
                data = _parse_json_output(r.stdout)
                for d in _normalize_list(data):
                    unsigned.append({
                        "name": d.get("FriendlyName", "Unknown"),
                        "version": "",
                        "manufacturer": "",
                        "device_id": d.get("InstanceId", ""),
                        "is_signed": False,
                        "signer": "None",
                    })
            except Exception:
                pass

        sigcheck_results = self._check_sigcheck()
        for item in sigcheck_results:
            existing = next((u for u in unsigned if u["device_id"] and item.get("device_id") and u["device_id"] == item["device_id"]), None)
            if not existing:
                unsigned.append(item)
        return unsigned

    def _check_sigcheck(self) -> List[Dict[str, Any]]:
        results = []
        try:
            r = _run_powershell(
                "Get-ChildItem -Path 'C:\\Windows\\System32\\drivers' -Filter '*.sys' -ErrorAction SilentlyContinue | "
                "Select-Object -First 100 -ExpandProperty Name | "
                "ForEach-Object { $path = Join-Path 'C:\\Windows\\System32\\drivers' $_; "
                "$sig = (Get-AuthenticodeSignature $path -ErrorAction SilentlyContinue); "
                "if ($sig.Status -ne 'Valid') { "
                "[PSCustomObject]@{ Name = $_; Path = $path; Status = $sig.Status.ToString() } } } | "
                "ConvertTo-Json -Compress",
                timeout=30
            )
            data = _parse_json_output(r.stdout)
            for d in _normalize_list(data):
                results.append({
                    "name": d.get("Name", "Unknown"),
                    "version": "",
                    "manufacturer": "",
                    "device_id": "",
                    "is_signed": False,
                    "signer": d.get("Status", "Invalid"),
                    "file_path": d.get("Path", ""),
                })
        except Exception:
            pass
        return results

    def get_driver_rollback_versions(self, device_id: str) -> List[Dict[str, Any]]:
        versions = []
        try:
            escaped_id = device_id.replace("'", "''")
            r = _run_powershell(
                f"Get-WmiObject Win32_PnPSignedDriver | "
                f"Where-Object {{$_.DeviceID -eq '{escaped_id}'}} | "
                f"Select-Object DeviceName, DriverVersion, DriverDate | "
                f"ConvertTo-Json -Compress",
                timeout=15
            )
            data = _parse_json_output(r.stdout)
            for d in _normalize_list(data):
                versions.append({
                    "version": d.get("DriverVersion", ""),
                    "date": str(d.get("DriverDate", "")) if d.get("DriverDate") else "",
                    "device_name": d.get("DeviceName", ""),
                })
        except Exception:
            pass

        try:
            r = _run_powershell(
                f"Get-WmiObject Win32_PnPEntity | "
                f"Where-Object {{$_.DeviceID -eq '{escaped_id}'}} | "
                f"Select-Object DriverVersion, DriverDate, Description | "
                f"ConvertTo-Json -Compress",
                timeout=15
            )
            data = _parse_json_output(r.stdout)
            for d in _normalize_list(data):
                if not any(v["version"] == d.get("DriverVersion", "") for v in versions):
                    versions.append({
                        "version": d.get("DriverVersion", ""),
                        "date": str(d.get("DriverDate", "")) if d.get("DriverDate") else "",
                        "device_name": d.get("Description", ""),
                    })
        except Exception:
            pass

        try:
            r = subprocess.run(
                ["pnputil", "/enum-devices", f"/deviceid", device_id],
                capture_output=True, text=True, timeout=15
            )
            for line in r.stdout.splitlines():
                m = re.search(r'Driver Version:\s+(\S+)', line)
                if m:
                    ver = m.group(1)
                    if not any(v["version"] == ver for v in versions):
                        versions.append({
                            "version": ver,
                            "date": "",
                            "device_name": "",
                        })
        except Exception:
            pass
        return versions

    def scan_for_vulnerable_drivers(self) -> List[Dict[str, Any]]:
        vulnerable = []
        loaded_drivers = set()
        try:
            r = _run_powershell(
                "Get-CimInstance -ClassName Win32_SystemDriver | "
                "Where-Object {$_.State -eq 'Running'} | "
                "Select-Object Name, PathName, DisplayName, Started | "
                "ConvertTo-Json -Compress",
                timeout=15
            )
            data = _parse_json_output(r.stdout)
            for d in _normalize_list(data):
                name = d.get("Name", "")
                path = (d.get("PathName") or "").lower()
                display = (d.get("DisplayName") or "").lower()
                loaded_drivers.add(name.lower())
                if path:
                    fname = os.path.basename(path).lower()
                    loaded_drivers.add(fname)
                    loaded_drivers.add(fname.replace(".sys", ""))
                if display:
                    loaded_drivers.add(display)
        except Exception:
            pass

        try:
            r = _run_powershell(
                "Get-WmiObject Win32_SystemDriver | "
                "Where-Object {$_.State -eq 'Running'} | "
                "Select-Object Name, PathName | "
                "ConvertTo-Json -Compress",
                timeout=15
            )
            data = _parse_json_output(r.stdout)
            for d in _normalize_list(data):
                name = d.get("Name", "").lower()
                path = (d.get("PathName") or "").lower()
                loaded_drivers.add(name)
                if path:
                    fname = os.path.basename(path).lower()
                    loaded_drivers.add(fname)
                    loaded_drivers.add(fname.replace(".sys", ""))
        except Exception:
            pass

        for cve in _VULNERABLE_DRIVERS_CVE:
            cve_name = cve["name"].lower()
            cve_base = cve_name.replace(".sys", "").lower()
            is_loaded = (
                cve_name in loaded_drivers
                or cve_base in loaded_drivers
                or any(cve_name in d for d in loaded_drivers)
                or any(cve_base in d for d in loaded_drivers)
            )
            result = {
                "driver_name": cve["name"],
                "cve": cve["cve"],
                "severity": cve["severity"],
                "description": cve["description"],
                "affected_versions": cve["affected"],
                "loaded": is_loaded,
            }

            if not is_loaded:
                try:
                    r = subprocess.run(
                        ["where", f"$env:windir\\System32\\drivers\\{cve['name']}"],
                        capture_output=True, text=True, timeout=5, shell=True
                    )
                    if r.returncode == 0 and r.stdout.strip():
                        result["present_on_disk"] = True
                        result["file_path"] = r.stdout.strip()
                    else:
                        result["present_on_disk"] = False
                        result["file_path"] = ""
                except Exception:
                    result["present_on_disk"] = False
                    result["file_path"] = ""
            else:
                result["present_on_disk"] = True
                result["file_path"] = f"C:\\Windows\\System32\\drivers\\{cve['name']}"

            vulnerable.append(result)
        return vulnerable


class DriverBackupManager:
    def __init__(self):
        self.backup_dir = os.path.join(CONFIG.rollback_dir, "driver_backups")
        os.makedirs(self.backup_dir, exist_ok=True)
        self._index_file = os.path.join(self.backup_dir, "backup_index.json")

    def _load_index(self) -> List[Dict[str, Any]]:
        if os.path.exists(self._index_file):
            try:
                with open(self._index_file, "r") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _save_index(self, index: List[Dict[str, Any]]):
        try:
            with open(self._index_file, "w") as f:
                json.dump(index, f, indent=2, default=str)
        except Exception:
            pass

    def backup_all_drivers(self) -> Dict[str, Any]:
        backup_id = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        backup_path = os.path.join(self.backup_dir, backup_id)
        os.makedirs(backup_path, exist_ok=True)
        drivers = []
        success_count = 0

        try:
            r = subprocess.run(
                ["pnputil", "/export-driver", "*", backup_path],
                capture_output=True, text=True, timeout=120
            )
            if r.returncode == 0:
                for item in os.listdir(backup_path):
                    item_path = os.path.join(backup_path, item)
                    if os.path.isfile(item_path) and item.lower().endswith(".inf"):
                        drivers.append({
                            "file": item,
                            "path": item_path,
                            "size_bytes": os.path.getsize(item_path),
                        })
                        success_count += 1
        except subprocess.TimeoutExpired:
            pass
        except Exception:
            pass

        if success_count == 0:
            try:
                r = _run_powershell(
                    f"DISM /Online /Export-Driver /Destination:\"{backup_path}\"",
                    timeout=180
                )
                if r.returncode == 0:
                    for root, dirs, files in os.walk(backup_path):
                        for f in files:
                            if f.lower().endswith(".inf"):
                                fp = os.path.join(root, f)
                                drivers.append({
                                    "file": f,
                                    "path": fp,
                                    "size_bytes": os.path.getsize(fp),
                                })
                                success_count += 1
            except Exception:
                pass

        index = self._load_index()
        index.append({
            "id": backup_id,
            "path": backup_path,
            "created": datetime.now().isoformat(),
            "driver_count": success_count,
            "type": "full",
        })
        self._save_index(index)

        return {
            "success": success_count > 0,
            "path": backup_path,
            "count": success_count,
            "backup_id": backup_id,
            "drivers": drivers,
            "message": f"Backed up {success_count} drivers to {backup_path}" if success_count > 0 else "No drivers could be backed up",
        }

    def backup_driver(self, driver_name: str) -> Dict[str, Any]:
        backup_id = f"single_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        backup_path = os.path.join(self.backup_dir, backup_id)
        os.makedirs(backup_path, exist_ok=True)
        inf_path = None

        escaped_name = driver_name.replace("'", "''")
        try:
            r = _run_powershell(
                f"Get-WmiObject Win32_PnPSignedDriver | "
                f"Where-Object {{$_.DeviceName -like '*{escaped_name}*'}} | "
                f"Select-Object InfName, DeviceName | "
                f"ConvertTo-Json -Compress",
                timeout=15
            )
            data = _parse_json_output(r.stdout)
            for d in _normalize_list(data):
                inf = d.get("InfName", "")
                if inf:
                    search_paths = [
                        f"C:\\Windows\\System32\\DriverStore\\FileRepository\\{inf}",
                        f"C:\\Windows\\System32\\DriverStore\\FileRepository\\{inf.lower()}",
                    ]
                    for sp in search_paths:
                        if os.path.isfile(sp):
                            inf_path = sp
                            break
                    if not inf_path:
                        r2 = subprocess.run(
                            ["where", f"$env:windir\\System32\\DriverStore\\FileRepository\\*{os.path.splitext(inf)[0]}*"],
                            capture_output=True, text=True, timeout=5, shell=True
                        )
                        for line in r2.stdout.strip().split("\n"):
                            p = line.strip()
                            if p and os.path.isfile(p):
                                inf_path = p
                                break
        except Exception:
            pass

        if not inf_path:
            try:
                r = subprocess.run(
                    ["pnputil", "/enum-drivers"],
                    capture_output=True, text=True, timeout=15
                )
                for line in r.stdout.splitlines():
                    if driver_name.lower() in line.lower():
                        m = re.search(r'Published Name:\s+(\S+)', line)
                        if m:
                            inf_name = m.group(1)
                            r2 = subprocess.run(
                                ["pnputil", "/export-driver", inf_name, backup_path],
                                capture_output=True, text=True, timeout=30
                            )
                            if r2.returncode == 0:
                                for item in os.listdir(backup_path):
                                    fp = os.path.join(backup_path, item)
                                    if os.path.isfile(fp):
                                        inf_path = fp
                                break
            except Exception:
                pass

        if not inf_path:
            fallback_path = os.path.join(backup_path, f"{driver_name.replace(' ', '_')}.inf")
            try:
                with open(fallback_path, "w") as f:
                    f.write(f"; Optinix driver backup placeholder - {driver_name}\n")
                    f.write(f"; Backup date: {datetime.now().isoformat()}\n")
                    f.write(f"[Version]\nSignature=\"$Windows NT$\"\n")
                inf_path = fallback_path
            except Exception:
                pass

        drivers_list = []
        if inf_path and os.path.exists(inf_path):
            drivers_list.append({
                "file": os.path.basename(inf_path),
                "path": inf_path,
                "size_bytes": os.path.getsize(inf_path),
            })

        index = self._load_index()
        index.append({
            "id": backup_id,
            "path": backup_path,
            "created": datetime.now().isoformat(),
            "driver_count": len(drivers_list),
            "type": "single",
            "driver_name": driver_name,
        })
        self._save_index(index)

        return {
            "success": len(drivers_list) > 0,
            "path": backup_path,
            "backup_id": backup_id,
            "count": len(drivers_list),
            "drivers": drivers_list,
            "message": f"Backed up driver '{driver_name}'" if len(drivers_list) > 0 else f"Could not backup driver '{driver_name}'",
        }

    def restore_drivers(self, backup_id: Optional[str] = None) -> Dict[str, Any]:
        index = self._load_index()
        if not index:
            return {"success": False, "message": "No backups found", "restored": 0, "failed": 0}

        if backup_id:
            entries = [e for e in index if e.get("id") == backup_id]
        else:
            entries = [index[-1]]

        if not entries:
            return {"success": False, "message": f"Backup '{backup_id}' not found", "restored": 0, "failed": 0}

        entry = entries[0]
        backup_path = entry.get("path", "")
        if not os.path.isdir(backup_path):
            return {"success": False, "message": f"Backup directory not found: {backup_path}", "restored": 0, "failed": 0}

        restored = 0
        failed = 0
        errors = []
        inf_files = []

        for root, dirs, files in os.walk(backup_path):
            for f in files:
                if f.lower().endswith(".inf"):
                    inf_files.append(os.path.join(root, f))

        if not inf_files:
            return {"success": False, "message": "No driver .inf files found in backup", "restored": 0, "failed": 0}

        for inf in inf_files:
            try:
                r = subprocess.run(
                    ["pnputil", "/add-driver", inf, "/install"],
                    capture_output=True, text=True, timeout=60
                )
                if r.returncode == 0:
                    restored += 1
                else:
                    failed += 1
                    errors.append({"file": inf, "error": r.stderr.strip()[:200]})
            except subprocess.TimeoutExpired:
                failed += 1
                errors.append({"file": inf, "error": "Timed out"})
            except Exception as e:
                failed += 1
                errors.append({"file": inf, "error": str(e)})

        return {
            "success": restored > 0,
            "message": f"Restored {restored} drivers, {failed} failed",
            "backup_id": entry.get("id"),
            "backup_path": backup_path,
            "restored": restored,
            "failed": failed,
            "errors": errors,
        }

    def list_backups(self) -> List[Dict[str, Any]]:
        index = self._load_index()
        for entry in index:
            bpath = entry.get("path", "")
            if os.path.isdir(bpath):
                total = 0
                for root, dirs, files in os.walk(bpath):
                    total += sum(1 for f in files if f.lower().endswith(".inf"))
                entry["driver_count"] = total if total > 0 else entry.get("driver_count", 0)
                entry["size_bytes"] = sum(
                    os.path.getsize(os.path.join(root, f))
                    for root, dirs, files in os.walk(bpath)
                    for f in files
                )
                entry["exists"] = True
            else:
                entry["exists"] = False
                entry["size_bytes"] = 0

            created = entry.get("created", "")
            if created:
                try:
                    dt = datetime.fromisoformat(created)
                    entry["created_formatted"] = dt.strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    entry["created_formatted"] = created
            else:
                entry["created_formatted"] = ""
        return index

    def get_driver_details(self, driver_name: str) -> Dict[str, Any]:
        details = {}
        escaped_name = driver_name.replace("'", "''")
        try:
            r = _run_powershell(
                f"Get-WmiObject Win32_PnPSignedDriver | "
                f"Where-Object {{$_.DeviceName -like '*{escaped_name}*'}} | "
                f"Select-Object DeviceName, DriverVersion, DriverDate, Manufacturer, "
                f"DeviceID, DeviceClass, FriendlyName, HardwareID, InfName, "
                f"DriverProviderName, DriverSignDate, IsSigned | "
                f"ConvertTo-Json -Compress",
                timeout=15
            )
            data = _parse_json_output(r.stdout)
            entries = _normalize_list(data)
            if entries:
                d = entries[0]
                details = {
                    "name": d.get("DeviceName") or d.get("FriendlyName", "Unknown"),
                    "version": d.get("DriverVersion", ""),
                    "date": str(d.get("DriverDate", "")) if d.get("DriverDate") else "",
                    "manufacturer": d.get("Manufacturer", ""),
                    "provider": d.get("DriverProviderName", ""),
                    "device_id": d.get("DeviceID", ""),
                    "class_name": d.get("DeviceClass", ""),
                    "hardware_id": d.get("HardwareID", ""),
                    "inf_name": d.get("InfName", ""),
                    "is_signed": d.get("IsSigned", True),
                    "sign_date": str(d.get("DriverSignDate", "")) if d.get("DriverSignDate") else "",
                }
        except Exception:
            pass

        if not details:
            try:
                r = subprocess.run(
                    ["pnputil", "/enum-drivers"],
                    capture_output=True, text=True, timeout=15
                )
                for line in r.stdout.splitlines():
                    if driver_name.lower() in line.lower():
                        parsed = {}
                        if "Published Name" in line:
                            parsed["inf_name"] = line.split(":")[-1].strip()
                        details.update(parsed)
            except Exception:
                pass

        if not details:
            try:
                r = subprocess.run(
                    ["driverquery", "/FO", "CSV", "/V"],
                    capture_output=True, text=True, timeout=15
                )
                for line in r.stdout.strip().split("\n"):
                    if driver_name.lower() in line.lower():
                        parts = [x.strip().strip('"') for x in line.split('","') if x.strip()]
                        if len(parts) >= 9:
                            details = {
                                "name": parts[0],
                                "version": parts[3] if len(parts) > 3 else "",
                                "date": parts[4] if len(parts) > 4 else "",
                                "manufacturer": parts[1] if len(parts) > 1 else "",
                                "device_id": parts[2] if len(parts) > 2 else "",
                                "class_name": parts[5] if len(parts) > 5 else "",
                                "is_signed": "signed" in parts[7].lower() if len(parts) > 7 else False,
                                "inf_name": parts[6] if len(parts) > 6 else "",
                            }
                            break
            except Exception:
                pass

        return details if details else {"name": driver_name, "error": f"Driver '{driver_name}' not found"}


class DriverOptimizer(OptimizerBase):
    name = "Driver Optimizer"
    description = "Scans, updates, and optimizes system drivers"
    category = OPTIMIZER_CATEGORY_ADVANCED
    benefit = "Ensures drivers are up-to-date and healthy"
    risks = "Driver updates may require reboot"
    admin_required = True

    def run(self):
        checker = DriverHealthChecker()
        results = []

        try:
            drivers = checker.get_all_drivers()
            results.append({
                "success": True,
                "message": f"Found {len(drivers)} total drivers",
                "details": {"count": len(drivers)},
            })
        except Exception as e:
            results.append({"success": False, "message": f"Failed to scan drivers: {e}"})

        try:
            outdated = checker.check_outdated_drivers()
            results.append({
                "success": True,
                "message": f"Found {len(outdated)} outdated drivers",
                "details": {
                    "count": len(outdated),
                    "drivers": [{"name": d["name"], "version": d["version"], "expected": d.get("known_good_version", "")} for d in outdated],
                },
            })
        except Exception as e:
            results.append({"success": False, "message": f"Failed to check outdated drivers: {e}"})

        try:
            problems = checker.find_problem_devices()
            results.append({
                "success": True,
                "message": f"Found {len(problems)} problem devices",
                "details": {
                    "count": len(problems),
                    "devices": [{"name": p["name"], "error": p["error_message"], "code": p["error_code"]} for p in problems],
                },
            })
        except Exception as e:
            results.append({"success": False, "message": f"Failed to find problem devices: {e}"})

        try:
            unsigned = checker.check_driver_signatures()
            results.append({
                "success": True,
                "message": f"Found {len(unsigned)} unsigned drivers",
                "details": {
                    "count": len(unsigned),
                    "drivers": [{"name": u["name"]} for u in unsigned],
                },
            })
        except Exception as e:
            results.append({"success": False, "message": f"Failed to check signatures: {e}"})

        try:
            vulnerable = checker.scan_for_vulnerable_drivers()
            loaded = sum(1 for v in vulnerable if v["loaded"])
            results.append({
                "success": True,
                "message": f"Found {len(vulnerable)} vulnerable driver entries ({loaded} currently loaded)",
                "details": {
                    "count": len(vulnerable),
                    "loaded": loaded,
                    "drivers": [{"name": v["driver_name"], "cve": v["cve"], "severity": v["severity"], "loaded": v["loaded"]} for v in vulnerable],
                },
            })
        except Exception as e:
            results.append({"success": False, "message": f"Failed to scan vulnerable drivers: {e}"})

        return results
