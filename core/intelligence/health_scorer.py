import psutil
import os
import subprocess
import re
import json
from datetime import datetime
from typing import Dict, Optional
from ..config import CONFIG
from ..logger import get_logger
from ..hardware_detection import HardwareDetector
from ..scanner import SystemScanner as Scanner


_GPU_TIERS = [
    (r"RTX 5090", 100), (r"RTX 5080", 98), (r"RTX 5070 Ti", 96), (r"RTX 5070", 94),
    (r"RTX 5060", 90), (r"RTX 4090", 100), (r"RTX 4080 (Super|Ti)?", 95),
    (r"RTX 4070 Ti( Super)?", 92), (r"RTX 4070( Super)?", 88),
    (r"RTX 4060( Ti)?", 82), (r"RTX 4050", 75),
    (r"RTX 3090( Ti)?", 93), (r"RTX 3080( Ti)?", 88),
    (r"RTX 3070( Ti)?", 82), (r"RTX 3060( Ti)?", 75),
    (r"RTX 3050", 65), (r"RTX 2080( Ti| Super)?", 80),
    (r"RTX 2070( Super)?", 72), (r"RTX 2060( Super)?", 65),
    (r"GTX 1660( Super| Ti)?", 58), (r"GTX 1650", 45),
    (r"GTX 1080( Ti)?", 70), (r"GTX 1070( Ti)?", 60),
    (r"GTX 1060", 50), (r"GTX 1050( Ti)?", 35),
    (r"RX 7900 XTX?", 96), (r"RX 7900 GRE?", 92),
    (r"RX 7800 XT", 88), (r"RX 7700 XT", 84),
    (r"RX 7600 XT?", 78), (r"RX 6950 XT", 90),
    (r"RX 6900 XT", 88), (r"RX 6800 XT?", 84),
    (r"RX 6750 XT", 80), (r"RX 6700 XT?", 76),
    (r"RX 6650 XT", 72), (r"RX 6600 XT?", 68),
    (r"RX 6500 XT", 50), (r"RX 6400", 40),
    (r"Arc A770", 75), (r"Arc A750", 68), (r"Arc A580", 55), (r"Arc A380", 35),
    (r"Intel Iris Xe", 25), (r"Intel UHD", 15), (r"Intel HD Graphics", 10),
    (r"AMD Radeon (Vega|Graphics)", 20),
    (r"AMD Radeon (HD|R[57])", 15),
]


class HealthScorer:
    def __init__(self):
        self.logger = get_logger("health_scorer")
        self._cache = {}
        self._cache_time = 0
        self._cache_ttl = 30
        self._detector = HardwareDetector()

    def _run(self, cmd, timeout=10):
        try:
            return subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
        except subprocess.TimeoutExpired:
            self.logger.warning(f"Command timed out after {timeout}s: {' '.join(cmd)}")
            return type("", (), {"returncode": -1, "stdout": "", "stderr": ""})()
        except Exception as e:
            self.logger.debug(f"Command failed: {e}")
            return type("", (), {"returncode": -1, "stdout": "", "stderr": ""})()

    def _ps(self, cmd, timeout=10):
        return self._run(
            ["powershell", "-NoProfile", "-Command", cmd], timeout=timeout
        )

    def _is_cache_valid(self):
        return self._cache and (datetime.now().timestamp() - self._cache_time) < self._cache_ttl

    def score_all(self) -> Dict:
        if self._is_cache_valid():
            return self._cache

        results = {}

        scorers = [
            ("windows_health", self._score_windows_health),
            ("gaming", self._score_gaming),
            ("developer", self._score_developer),
            ("security", self._score_security),
            ("storage", self._score_storage),
            ("battery", self._score_battery),
        ]

        for name, scorer in scorers:
            try:
                results[name] = scorer()
            except Exception as e:
                self.logger.error(f"Failed to compute {name} score: {e}")
                results[name] = {"score": 0, "label": "Error", "details": {"error": str(e)}}

        scores = [v["score"] for v in results.values() if isinstance(v.get("score"), (int, float))]
        results["overall"] = round(sum(scores) / len(scores)) if scores else 0
        results["pc_health"] = self._compute_pc_health(results)
        results["timestamp"] = datetime.now().isoformat()

        self._cache = results
        self._cache_time = datetime.now().timestamp()
        return results

    def _compute_pc_health(self, results: Dict) -> Dict:
        keys = ["windows_health", "gaming", "developer", "security", "storage", "battery"]
        scores = []
        details = {}
        for k in keys:
            v = results.get(k, {})
            s = v.get("score", 0) if isinstance(v, dict) else 0
            if isinstance(s, (int, float)):
                scores.append(s)
                details[k] = s
        avg = round(sum(scores) / len(scores)) if scores else 0
        if avg >= 90:
            label = "Excellent"
        elif avg >= 75:
            label = "Good"
        elif avg >= 50:
            label = "Fair"
        elif avg >= 25:
            label = "Poor"
        else:
            label = "Critical"
        return {"score": avg, "label": label, "details": details}

    def get_pc_health_score(self) -> int:
        data = self.score_all()
        pc = data.get("pc_health", {})
        return pc.get("score", 0) if isinstance(pc, dict) else 0

    def get_score(self, name: str) -> Dict:
        data = self.score_all()
        if name in data:
            return data[name]
        self.logger.warning(f"Unknown score requested: {name}")
        return {"score": 0, "label": "Unknown", "details": {}}

    def _score_windows_health(self) -> Dict:
        details = {}
        score = 100

        try:
            boot_time = psutil.boot_time()
            uptime_seconds = datetime.now().timestamp() - boot_time
            uptime_days = uptime_seconds / 86400
            details["uptime_days"] = round(uptime_days, 2)
            if uptime_days > 30:
                score -= 15
            elif uptime_days > 14:
                score -= 10
            elif uptime_days > 7:
                score -= 5
        except Exception as e:
            details["uptime_error"] = str(e)

        r = self._ps(
            "Get-WinEvent -FilterHashtable @{LogName='System';Level=2} -MaxEvents 100 -EA SilentlyContinue | Measure-Object | Select-Object -ExpandProperty Count"
        )
        try:
            error_count = int(r.stdout.strip()) if r.stdout.strip().isdigit() else 0
            details["event_log_errors"] = error_count
            if error_count > 50:
                score -= 20
            elif error_count > 20:
                score -= 10
            elif error_count > 10:
                score -= 5
        except (ValueError, AttributeError):
            details["event_log_errors"] = -1

        r = self._ps(
            "Get-MpComputerStatus -EA SilentlyContinue | Select-Object RealTimeProtectionEnabled, AntispywareEnabled | ConvertTo-Json -Compress"
        )
        try:
            defender = json.loads(r.stdout.strip()) if r.stdout.strip() else {}
            if isinstance(defender, list):
                defender = defender[0] if defender else {}
            defender_enabled = defender.get("RealTimeProtectionEnabled") is True
            defender_as = defender.get("AntispywareEnabled") is True
            details["defender_enabled"] = defender_enabled
            details["defender_antispyware"] = defender_as
            if not defender_enabled:
                score -= 15
            if not defender_as:
                score -= 5
        except (json.JSONDecodeError, AttributeError, IndexError):
            details["defender_status"] = "unknown"

        r = self._ps(
            "(New-Object -ComObject Microsoft.Update.AutoUpdate).State -EA SilentlyContinue"
        )
        try:
            wu_state = r.stdout.strip()
            details["windows_update_state"] = wu_state
            if wu_state in ("4", "5"):
                pass
            elif wu_state in ("2", "3"):
                score -= 5
            else:
                score -= 10
        except Exception:
            details["windows_update_status"] = "unknown"

        score = max(0, min(100, score))

        label = (
            "Healthy" if score >= 80 else
            "Needs Attention" if score >= 50 else
            "Critical"
        )
        return {"score": score, "label": label, "details": details}

    def _score_gaming(self) -> Dict:
        details = {}
        score = 0
        weights = {"gpu": 0.40, "cpu": 0.25, "ram": 0.20, "game_mode": 0.15}

        gpu_score = 20
        try:
            r = self._ps(
                "Get-CimInstance Win32_VideoController -EA SilentlyContinue | Select-Object -First 1 -ExpandProperty Name"
            )
            gpu_name = r.stdout.strip()
            details["gpu_name"] = gpu_name if gpu_name else "Unknown"
            if gpu_name:
                gpu_score = 20
                for pattern, tier_score in _GPU_TIERS:
                    if re.search(pattern, gpu_name, re.IGNORECASE):
                        gpu_score = tier_score
                        break
        except Exception as e:
            details["gpu_error"] = str(e)
            gpu_score = 20
        details["gpu_score"] = gpu_score

        try:
            logical = psutil.cpu_count(logical=True) or 1
            physical = psutil.cpu_count(logical=False) or 1
            details["cpu_logical_cores"] = logical
            details["cpu_physical_cores"] = physical
            if logical >= 16:
                cpu_score = 100
            elif logical >= 12:
                cpu_score = 90
            elif logical >= 8:
                cpu_score = 75
            elif logical >= 6:
                cpu_score = 60
            elif logical >= 4:
                cpu_score = 40
            else:
                cpu_score = 20
        except Exception:
            cpu_score = 50
        details["cpu_score"] = cpu_score

        try:
            ram_gb = psutil.virtual_memory().total / (1024 ** 3)
            details["ram_gb"] = round(ram_gb, 1)
            if ram_gb >= 64:
                ram_score = 100
            elif ram_gb >= 32:
                ram_score = 90
            elif ram_gb >= 16:
                ram_score = 70
            elif ram_gb >= 12:
                ram_score = 55
            elif ram_gb >= 8:
                ram_score = 40
            else:
                ram_score = 20
        except Exception:
            ram_score = 50
        details["ram_score"] = ram_score

        r = self._run(
            ["reg", "query", "HKCU\\Software\\Microsoft\\GameBar", "/v", "AllowAutoGameMode"],
            timeout=5,
        )
        game_mode = r.returncode == 0 and "0x1" in r.stdout
        details["game_mode_enabled"] = game_mode
        game_mode_score = 100 if game_mode else 30

        score = (
            gpu_score * weights["gpu"]
            + cpu_score * weights["cpu"]
            + ram_score * weights["ram"]
            + game_mode_score * weights["game_mode"]
        )
        score = round(score)
        score = max(0, min(100, score))

        label = (
            "High-End" if score >= 85 else
            "Mid-Range" if score >= 60 else
            "Entry-Level" if score >= 40 else
            "Low-End"
        )
        return {"score": score, "label": label, "details": details}

    def _score_developer(self) -> Dict:
        details = {}
        score = 0
        weights = {"tools": 0.30, "ram": 0.25, "cpu": 0.25, "storage": 0.20}

        tools = {"code": "VS Code", "node": "Node.js", "git": "Git", "python": "Python"}
        found_tools = []
        for cmd, display_name in tools.items():
            r = self._run(["where", cmd], timeout=5)
            if r.returncode == 0:
                found_tools.append(display_name)
        details["tools_found"] = found_tools
        tools_score = round(len(found_tools) / len(tools) * 100)

        try:
            ram_gb = psutil.virtual_memory().total / (1024 ** 3)
            details["ram_gb"] = round(ram_gb, 1)
            if ram_gb >= 64:
                ram_score = 100
            elif ram_gb >= 32:
                ram_score = 90
            elif ram_gb >= 16:
                ram_score = 70
            elif ram_gb >= 8:
                ram_score = 40
            else:
                ram_score = 10
        except Exception:
            ram_score = 50

        try:
            logical = psutil.cpu_count(logical=True) or 1
            details["cpu_logical_cores"] = logical
            if logical >= 16:
                cpu_score = 100
            elif logical >= 12:
                cpu_score = 85
            elif logical >= 8:
                cpu_score = 65
            elif logical >= 4:
                cpu_score = 40
            else:
                cpu_score = 20
        except Exception:
            cpu_score = 50

        try:
            r = self._ps(
                "Get-PhysicalDisk -EA SilentlyContinue | Where-Object MediaType -eq 4 | Measure-Object | Select-Object -ExpandProperty Count"
            )
            ssd_count = int(r.stdout.strip()) if r.stdout.strip().isdigit() else 0
            details["ssd_count"] = ssd_count
            if ssd_count > 0:
                try:
                    r2 = self._ps(
                        "Get-PhysicalDisk -EA SilentlyContinue | Where-Object MediaType -eq 4 | Select-Object -First 1 -ExpandProperty Size"
                    )
                    total_ssd_gb = int(r2.stdout.strip()) / (1024 ** 3) if r2.stdout.strip().isdigit() else 0
                    details["primary_ssd_gb"] = round(total_ssd_gb, 1)
                except Exception:
                    total_ssd_gb = 0
                storage_score = 100 if total_ssd_gb >= 1000 else 80 if total_ssd_gb >= 500 else 60
            else:
                storage_score = 30
                details["primary_ssd_gb"] = 0
        except Exception:
            storage_score = 50

        score = (
            tools_score * weights["tools"]
            + ram_score * weights["ram"]
            + cpu_score * weights["cpu"]
            + storage_score * weights["storage"]
        )
        score = round(score)
        score = max(0, min(100, score))

        label = (
            "Excellent Dev Setup" if score >= 85 else
            "Good Dev Setup" if score >= 65 else
            "Adequate Dev Setup" if score >= 40 else
            "Minimal Dev Setup"
        )
        return {"score": score, "label": label, "details": details}

    def _score_security(self) -> Dict:
        details = {}
        score = 100

        r = self._ps(
            "Get-MpComputerStatus -EA SilentlyContinue | Select-Object RealTimeProtectionEnabled, AntispywareEnabled | ConvertTo-Json -Compress"
        )
        try:
            defender = json.loads(r.stdout.strip()) if r.stdout.strip() else {}
            if isinstance(defender, list):
                defender = defender[0] if defender else {}
            defender_enabled = defender.get("RealTimeProtectionEnabled") is True
            details["defender_enabled"] = defender_enabled
            if not defender_enabled:
                score -= 25
        except (json.JSONDecodeError, AttributeError, IndexError):
            details["defender_status"] = "unknown"
            score -= 10

        r = self._run(
            ["netsh", "advfirewall", "show", "allprofiles", "state"], timeout=10
        )
        try:
            profiles = r.stdout.lower()
            domain_on = "Domain Profile Settings:" in r.stdout and "State                                 ON" in r.stdout
            private_on = "Private Profile Settings:" in r.stdout and "State                                 ON" in r.stdout
            public_on = "Public Profile Settings:" in r.stdout and "State                                 ON" in r.stdout
            all_on = all([domain_on, private_on, public_on])
            details["firewall_domain"] = domain_on
            details["firewall_private"] = private_on
            details["firewall_public"] = public_on
            details["firewall_all_on"] = all_on
            if not all_on:
                score -= 15
        except Exception:
            details["firewall_status"] = "unknown"
            score -= 5

        r = self._run(
            ["reg", "query", "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System", "/v", "EnableLUA"],
            timeout=5,
        )
        try:
            uac_enabled = "0x1" in r.stdout
            details["uac_enabled"] = uac_enabled
            if not uac_enabled:
                score -= 15
        except Exception:
            details["uac_status"] = "unknown"
            score -= 5

        r = self._ps("(New-Object -ComObject Microsoft.Update.AutoUpdate).State -EA SilentlyContinue")
        try:
            wu_state = r.stdout.strip()
            details["windows_update_state"] = wu_state
            if wu_state not in ("4", "5"):
                score -= 10
        except Exception:
            details["windows_update_status"] = "unknown"
            score -= 5

        r = self._ps("Confirm-SecureBootUEFI -EA SilentlyContinue")
        try:
            secure_boot = "True" in r.stdout
            details["secure_boot"] = secure_boot
            if not secure_boot:
                score -= 15
        except Exception:
            details["secure_boot"] = None

        r = self._ps(
            "Get-BitLockerVolume -EA SilentlyContinue -MountPoint $env:SystemDrive | Select-Object ProtectionStatus | ConvertTo-Json -Compress"
        )
        try:
            bl = json.loads(r.stdout.strip()) if r.stdout.strip() else {}
            if isinstance(bl, list):
                bl = bl[0] if bl else {}
            bitlocker_on = bl.get("ProtectionStatus") == 1 or bl.get("ProtectionStatus") == "On"
            details["bitlocker_enabled"] = bitlocker_on
            if bitlocker_on:
                score += 5
        except (json.JSONDecodeError, AttributeError, IndexError):
            details["bitlocker_status"] = "unknown"

        score = max(0, min(100, score))
        label = (
            "Secure" if score >= 85 else
            "Moderate" if score >= 60 else
            "Vulnerable"
        )
        return {"score": score, "label": label, "details": details}

    def _score_storage(self) -> Dict:
        details = {}
        score = 100
        drive_details = []

        try:
            is_laptop = self._detector.detect_laptop()
        except Exception:
            is_laptop = False

        try:
            partitions = psutil.disk_partitions()
            if not partitions:
                details["drives"] = []
                return {"score": 50, "label": "Unknown", "details": {"error": "No drives found"}}

            ssd_detected = False
            for part in partitions:
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    total_gb = usage.total / (1024 ** 3)
                    free_gb = usage.free / (1024 ** 3)
                    free_pct = usage.free / usage.total * 100 if usage.total > 0 else 0
                    drive_info = {
                        "mount": part.mountpoint,
                        "device": part.device,
                        "total_gb": round(total_gb, 1),
                        "free_gb": round(free_gb, 1),
                        "free_pct": round(free_pct, 1),
                    }
                    if free_pct < 10:
                        score -= 10
                        drive_info["warning"] = "Critically low free space"
                    elif free_pct < 20:
                        score -= 5
                        drive_info["warning"] = "Low free space"
                    drive_details.append(drive_info)
                except (PermissionError, OSError):
                    continue

            details["drives"] = drive_details

            r = self._ps(
                "Get-PhysicalDisk -EA SilentlyContinue | Select-Object MediaType | ConvertTo-Json -Compress"
            )
            try:
                disks = json.loads(r.stdout.strip()) if r.stdout.strip() else []
                if isinstance(disks, dict):
                    disks = [disks]
                for disk in disks:
                    if isinstance(disk, dict) and str(disk.get("MediaType", "")).strip() in ("4", "SSD"):
                        ssd_detected = True
                        break
            except (json.JSONDecodeError, AttributeError):
                pass

            details["has_ssd"] = ssd_detected
            if ssd_detected:
                score += 10
            else:
                score -= 10

        except Exception as e:
            self.logger.error(f"Storage scoring error: {e}")
            return {"score": 50, "label": "Error", "details": {"error": str(e)}}

        score = max(0, min(100, score))
        label = (
            "Excellent" if score >= 85 else
            "Good" if score >= 65 else
            "Low Space" if score >= 40 else
            "Critical"
        )
        return {"score": score, "label": label, "details": details}

    def _score_battery(self) -> Dict:
        details = {}

        try:
            is_laptop = self._detector.detect_laptop()
        except Exception:
            is_laptop = False

        if not is_laptop:
            return {
                "score": 100,
                "label": "Desktop (No Battery)",
                "details": {"is_laptop": False, "health_pct": None, "cycle_count": None, "est_runtime_min": None},
            }

        try:
            r = self._ps(
                "Get-WmiObject -Namespace root\\wmi -Class BatteryFullChargedCapacity -EA SilentlyContinue | Select-Object -ExpandProperty FullChargedCapacity"
            )
            full_capacity = int(r.stdout.strip()) if r.stdout.strip().isdigit() else None
        except Exception:
            full_capacity = None

        try:
            r = self._ps(
                "Get-WmiObject -Namespace root\\wmi -Class BatteryCycleCount -EA SilentlyContinue | Select-Object -First 1 -ExpandProperty CycleCount"
            )
            cycle_count = int(r.stdout.strip()) if r.stdout.strip().isdigit() else None
        except Exception:
            cycle_count = None

        try:
            r = self._ps(
                "Get-WmiObject -Namespace root\\wmi -Class BatteryStatus -EA SilentlyContinue | Select-Object -First 1 -ExpandProperty EstimatedRunTime"
            )
            est_runtime = int(r.stdout.strip()) if r.stdout.strip().isdigit() else None
        except Exception:
            est_runtime = None

        try:
            r = self._ps(
                "Get-WmiObject -Namespace root\\wmi -Class BatteryStaticData -EA SilentlyContinue | Select-Object -First 1 -ExpandProperty DesignedCapacity"
            )
            designed_capacity = int(r.stdout.strip()) if r.stdout.strip().isdigit() else None
        except Exception:
            designed_capacity = None

        health_pct = None
        if full_capacity is not None and designed_capacity and designed_capacity > 0:
            health_pct = round(full_capacity / designed_capacity * 100, 1)

        score = 80
        if health_pct is not None:
            details["health_pct"] = health_pct
            if health_pct >= 90:
                score = 100
            elif health_pct >= 80:
                score = 90
            elif health_pct >= 70:
                score = 75
            elif health_pct >= 50:
                score = 50
            else:
                score = 25
        else:
            details["health_pct"] = None

        if cycle_count is not None:
            details["cycle_count"] = cycle_count
            if cycle_count > 800:
                score -= 20
            elif cycle_count > 500:
                score -= 10
            elif cycle_count > 300:
                score -= 5
        else:
            details["cycle_count"] = None

        if est_runtime is not None:
            details["est_runtime_min"] = est_runtime
            if est_runtime < 30:
                score -= 15
            elif est_runtime < 60:
                score -= 10
            elif est_runtime < 120:
                score -= 5
        else:
            details["est_runtime_min"] = None

        try:
            r = self._run(["powercfg", "/getactivescheme"], timeout=5)
            power_plan = r.stdout.strip() if r.returncode == 0 else "unknown"
            details["power_plan"] = power_plan
            if "High Performance" in power_plan or "Ultimate" in power_plan:
                score += 5
        except Exception:
            details["power_plan"] = "unknown"

        details["is_laptop"] = True
        score = max(0, min(100, score))

        label = (
            "Excellent Battery" if score >= 90 else
            "Good Battery" if score >= 70 else
            "Fair Battery" if score >= 50 else
            "Replace Soon"
        )
        return {"score": score, "label": label, "details": details}
