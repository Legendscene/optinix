import os
import time
import platform
import subprocess
import psutil
from typing import Dict, Any, List, Optional


class HealthAnalyzer:
    def __init__(self, *args, **kwargs):
        self._os_type = args[0] if args else kwargs.get("os_type", "windows")

    def analyze(self) -> Dict[str, Any]:
        cpu_score, cpu_details = self._analyze_cpu()
        mem_score, mem_details = self._analyze_memory()
        disk_score, disk_details = self._analyze_disk()
        sys_score, sys_details = self._analyze_system()
        sec_score, sec_details = self._analyze_security()
        perf_score, perf_details = self._analyze_performance()

        total = cpu_score + mem_score + disk_score + sys_score + sec_score + perf_score
        total = max(0, min(100, total))

        if total >= 90:
            label, color = "Excellent", "#00e676"
        elif total >= 70:
            label, color = "Good", "#76ff03"
        elif total >= 50:
            label, color = "Fair", "#ffea00"
        elif total >= 25:
            label, color = "Poor", "#ff9100"
        else:
            label, color = "Critical", "#ff1744"

        return {
            "score": total,
            "label": label,
            "color": color,
            "components": {
                "cpu": cpu_score,
                "memory": mem_score,
                "disk": disk_score,
                "system": sys_score,
                "security": sec_score,
                "performance": perf_score,
            },
            "details": {
                "cpu": cpu_details,
                "memory": mem_details,
                "disk": disk_details,
                "system": sys_details,
                "security": sec_details,
                "performance": perf_details,
            },
            "os": self._os_type,
            "timestamp": time.time(),
        }

    def _analyze_cpu(self) -> tuple:
        score = 0
        details = {}
        try:
            load = psutil.cpu_percent(interval=0.5)
            details["load_percent"] = load
            if load < 50:
                score = 25
            elif load < 70:
                score = 15
            elif load < 90:
                score = 5
            else:
                score = 0
        except:
            details["load_percent"] = -1
            score = 15

        try:
            temps = psutil.sensors_temperatures()
            cpu_temp = None
            for key in ("cpu_thermal", "coretemp", "k10temp", "zenpower", "cpu-thermal"):
                if key in temps and temps[key]:
                    cpu_temp = temps[key][0].current
                    break
            if cpu_temp is not None:
                details["temperature"] = cpu_temp
                if cpu_temp > 85:
                    score = max(0, score - 10)
                elif cpu_temp > 75:
                    score = max(0, score - 5)
        except:
            details["temperature"] = None

        try:
            ctx = psutil.cpu_stats()
            details["context_switches"] = ctx.ctx_switches
            details["interrupts"] = ctx.interrupts
        except:
            pass

        try:
            details["physical_cores"] = psutil.cpu_count(logical=False) or 0
            details["logical_cores"] = psutil.cpu_count(logical=True) or 0
        except:
            pass

        return score, details

    def _analyze_memory(self) -> tuple:
        score = 0
        details = {}
        try:
            mem = psutil.virtual_memory()
            avail_gb = mem.available / (1024 ** 3)
            total_gb = mem.total / (1024 ** 3)
            percent_available = (mem.available / mem.total) * 100
            details["total_gb"] = round(total_gb, 1)
            details["available_gb"] = round(avail_gb, 1)
            details["percent_available"] = round(percent_available, 1)
            details["percent_used"] = mem.percent

            if percent_available > 50:
                score = 20
            elif percent_available > 30:
                score = 15
            elif percent_available > 20:
                score = 10
            elif percent_available > 10:
                score = 5
            else:
                score = 0
        except:
            details["available_gb"] = -1
            score = 10

        try:
            swap = psutil.swap_memory()
            details["swap_total_gb"] = round(swap.total / (1024 ** 3), 1)
            details["swap_used_gb"] = round(swap.used / (1024 ** 3), 1)
            details["swap_percent"] = swap.percent
        except:
            pass

        return score, details

    def _analyze_disk(self) -> tuple:
        score = 0
        details = {}
        disk_scores = []
        try:
            parts = psutil.disk_partitions()
            drives = []
            for p in parts:
                try:
                    usage = psutil.disk_usage(p.mountpoint)
                    free_pct = (usage.free / usage.total) * 100
                    is_ssd = self._is_ssd(p.mountpoint)
                    drive_info = {
                        "mountpoint": p.mountpoint,
                        "fstype": p.fstype,
                        "total_gb": round(usage.total / (1024 ** 3), 1),
                        "free_gb": round(usage.free / (1024 ** 3), 1),
                        "free_percent": round(free_pct, 1),
                        "is_ssd": is_ssd,
                    }
                    drives.append(drive_info)

                    if free_pct > 30:
                        ds = 20
                    elif free_pct > 20:
                        ds = 15
                    elif free_pct > 10:
                        ds = 10
                    elif free_pct > 5:
                        ds = 5
                    else:
                        ds = 0
                    disk_scores.append(ds)
                except:
                    continue
            details["drives"] = drives
            score = int(sum(disk_scores) / len(disk_scores)) if disk_scores else 10
        except:
            details["drives"] = []
            score = 10

        try:
            io = psutil.disk_io_counters()
            details["read_bytes_mb"] = round(io.read_bytes / (1024 ** 2), 1)
            details["write_bytes_mb"] = round(io.write_bytes / (1024 ** 2), 1)
            details["read_count"] = io.read_count
            details["write_count"] = io.write_count
        except:
            pass

        return score, details

    def _is_ssd(self, mountpoint: str) -> Optional[bool]:
        try:
            if platform.system() != "Windows":
                return None
            drive = mountpoint[0].upper()
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"(Get-PhysicalDisk -DeviceId (Get-Partition -DriveLetter {drive} | Select-Object -ExpandProperty DiskNumber) | Select-Object -ExpandProperty MediaType)"],
                capture_output=True, text=True, timeout=5,
            )
            output = r.stdout.strip()
            if "SSD" in output or "4" in output:
                return True
            if "HDD" in output or "3" in output or "Unspecified" in output:
                return False
            return None
        except:
            return None

    def _analyze_system(self) -> tuple:
        score = 0
        details = {}
        try:
            boot = psutil.boot_time()
            uptime_seconds = time.time() - boot
            uptime_days = uptime_seconds / 86400
            details["uptime_days"] = round(uptime_days, 1)
            details["boot_time"] = boot

            if uptime_days < 7:
                score = 15
            elif uptime_days < 30:
                score = 10
            elif uptime_days < 90:
                score = 5
            else:
                score = 0
        except:
            details["uptime_days"] = -1
            score = 7

        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
            details["is_admin"] = is_admin
            if is_admin:
                score += 5
        except:
            details["is_admin"] = False

        try:
            details["os_version"] = platform.version()
            details["os_release"] = platform.release()
            details["machine"] = platform.machine()
        except:
            pass

        return score, details

    def _analyze_security(self) -> tuple:
        score = 0
        details = {}
        checks = []

        if platform.system() == "Windows":
            defender = self._check_defender()
            checks.append(("defender_active", defender))
            if defender:
                score += 4

            firewall = self._check_firewall()
            checks.append(("firewall_active", firewall))
            if firewall:
                score += 3

            uac = self._check_uac()
            checks.append(("uac_enabled", uac))
            if uac:
                score += 3
        else:
            score = 5

        details["checks"] = checks
        return score, details

    def _check_defender(self) -> bool:
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-MpComputerStatus).RealTimeProtectionEnabled"],
                capture_output=True, text=True, timeout=5,
            )
            return r.stdout.strip() == "True"
        except:
            return False

    def _check_firewall(self) -> bool:
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-NetFirewallProfile -Profile Domain,Public,Private | Where-Object {$_.Enabled -eq $True}).Count -eq 3"],
                capture_output=True, text=True, timeout=5,
            )
            return r.stdout.strip() == "True"
        except:
            return False

    def _check_uac(self) -> bool:
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-ItemProperty -Path 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System' -Name EnableLUA).EnableLUA"],
                capture_output=True, text=True, timeout=5,
            )
            return r.stdout.strip() == "1"
        except:
            return False

    def _analyze_performance(self) -> tuple:
        score = 0
        details = {}
        try:
            procs = len(psutil.pids())
            details["running_processes"] = procs
            if procs < 100:
                score = 5
            elif procs < 200:
                score = 3
            elif procs < 300:
                score = 1
            else:
                score = 0
        except:
            details["running_processes"] = -1
            score = 2

        try:
            svcs = len([p for p in psutil.process_iter(['pid']) if p.is_running()])
            services_count = 0
            for p in psutil.process_iter(['pid', 'name']):
                try:
                    if p.info.get('name') and p.info['name'].endswith('.exe'):
                        if p.info['name'] in ('svchost.exe', 'services.exe', 'lsass.exe', 'winlogon.exe', 'csrss.exe'):
                            services_count += 1
                except:
                    pass
            details["background_services"] = services_count
            if services_count < 50:
                score += 5
            elif services_count < 100:
                score += 3
            elif services_count < 150:
                score += 1
            else:
                score += 0
        except:
            details["background_services"] = -1
            score += 2

        try:
            cpu_freq = psutil.cpu_freq()
            if cpu_freq:
                details["cpu_freq_current_mhz"] = round(cpu_freq.current, 1)
                details["cpu_freq_max_mhz"] = round(cpu_freq.max, 1)
        except:
            pass

        score = min(score, 10)
        return score, details

    def detect_bottlenecks(self) -> List[Dict[str, Any]]:
        bottlenecks = []

        cpu_bn = self._detect_cpu_bottleneck()
        if cpu_bn:
            bottlenecks.append(cpu_bn)

        ram_bn = self._detect_ram_bottleneck()
        if ram_bn:
            bottlenecks.append(ram_bn)

        disk_bn = self._detect_disk_bottleneck()
        if disk_bn:
            bottlenecks.append(disk_bn)

        gpu_bn = self._detect_gpu_bottleneck()
        if gpu_bn:
            bottlenecks.append(gpu_bn)

        net_bn = self._detect_network_bottleneck()
        if net_bn:
            bottlenecks.append(net_bn)

        return bottlenecks

    def _detect_cpu_bottleneck(self) -> Optional[Dict[str, Any]]:
        try:
            cpu_percent = psutil.cpu_percent(interval=0.5)
            if cpu_percent > 80:
                severity = "critical" if cpu_percent > 95 else "high"
                return {
                    "type": "cpu",
                    "severity": severity,
                    "description": f"CPU usage is at {cpu_percent}% — system may be throttling under load",
                    "recommendation": "Close unused applications, check for background processes consuming CPU, consider upgrading CPU if persistent",
                }

            try:
                ctx = psutil.cpu_stats()
                interrupts = ctx.interrupts
                if interrupts > 100000:
                    return {
                        "type": "cpu",
                        "severity": "medium",
                        "description": f"High interrupt rate detected ({interrupts} interrupts). Possible driver or hardware issue.",
                        "recommendation": "Check for malfunctioning hardware drivers, run Driver Verifier, update chipset drivers",
                    }
            except:
                pass
        except:
            pass
        return None

    def _detect_ram_bottleneck(self) -> Optional[Dict[str, Any]]:
        try:
            mem = psutil.virtual_memory()
            avail_gb = mem.available / (1024 ** 3)
            if avail_gb < 2:
                severity = "critical" if avail_gb < 1 else "high"
                return {
                    "type": "ram",
                    "severity": severity,
                    "description": f"Low memory available: {avail_gb:.1f} GB. System may use page file heavily, degrading performance.",
                    "recommendation": "Close memory-heavy applications, disable unnecessary startup programs, consider adding more RAM",
                }

            try:
                swap = psutil.swap_memory()
                if swap.percent > 50:
                    return {
                        "type": "ram",
                        "severity": "medium",
                        "description": f"High page file usage at {swap.percent}% ({swap.used / (1024**3):.1f} GB used). Indicates physical memory pressure.",
                        "recommendation": "Increase physical RAM, reduce memory usage by closing applications, adjust virtual memory settings",
                    }
            except:
                pass
        except:
            pass
        return None

    def _detect_disk_bottleneck(self) -> Optional[Dict[str, Any]]:
        try:
            io = psutil.disk_io_counters()
            if io is None:
                return None

            try:
                r = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     "(Get-CimInstance Win32_PerfFormattedData_PerfDisk_LogicalDisk | Measure-Object -Property AvgDisksecPerRead -Average).Average"],
                    capture_output=True, text=True, timeout=5,
                )
                avg_sec = r.stdout.strip()
                if avg_sec and avg_sec != "0":
                    avg_sec_f = float(avg_sec) / 1000
                    if avg_sec_f > 50:
                        severity = "critical" if avg_sec_f > 100 else "high"
                        return {
                            "type": "disk",
                            "severity": severity,
                            "description": f"High disk latency: {avg_sec_f:.1f} ms average response time. Disk may be bottlenecking IO.",
                            "recommendation": "Check for disk-heavy processes in Task Manager, run CHKDSK, consider upgrading to SSD",
                        }
            except:
                pass

            try:
                r = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     "(Get-CimInstance Win32_PerfFormattedData_PerfDisk_LogicalDisk | Measure-Object -Property CurrentDiskQueueLength -Average).Average"],
                    capture_output=True, text=True, timeout=5,
                )
                queue = r.stdout.strip()
                if queue and float(queue) > 2:
                    return {
                        "type": "disk",
                        "severity": "medium",
                        "description": f"Disk queue depth at {float(queue):.1f}. Multiple processes waiting for disk IO.",
                        "recommendation": "Identify and close processes with high disk usage, defragment HDD or optimize SSD",
                    }
            except:
                pass
        except:
            pass
        return None

    def _detect_gpu_bottleneck(self) -> Optional[Dict[str, Any]]:
        try:
            r = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5,
            )
            if r.returncode == 0:
                gpu_util = float(r.stdout.strip())
                if gpu_util > 95:
                    return {
                        "type": "gpu",
                        "severity": "high",
                        "description": f"GPU usage at {gpu_util}% — graphics card is near full capacity",
                        "recommendation": "Lower graphics settings in games/applications, close GPU-accelerated background apps, consider GPU upgrade",
                    }
        except:
            pass
        return None

    def _detect_network_bottleneck(self) -> Optional[Dict[str, Any]]:
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "ping -n 3 8.8.8.8 | Select-String 'time=' | ForEach-Object { [int]($_.Line -replace '.*time=(\\d+).*', '$1') } | Measure-Object -Average | Select-Object -ExpandProperty Average"],
                capture_output=True, text=True, timeout=15,
            )
            latency = r.stdout.strip()
            if latency and latency != "0":
                latency_f = float(latency)
                if latency_f > 150:
                    return {
                        "type": "network",
                        "severity": "high" if latency_f > 300 else "medium",
                        "description": f"High network latency detected: {latency_f:.0f} ms average ping",
                        "recommendation": "Check for bandwidth-heavy applications, restart router, check network adapter drivers, consider wired connection",
                    }
                if latency_f > 80:
                    return {
                        "type": "network",
                        "severity": "low",
                        "description": f"Elevated network latency: {latency_f:.0f} ms",
                        "recommendation": "Close background network applications, check for interference on WiFi",
                    }
        except:
            pass

        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "ping -n 5 8.8.8.8 | Select-String 'loss' | ForEach-Object { ($_ -replace '.*\\((\\d+)% loss\\).*', '$1') }"],
                capture_output=True, text=True, timeout=15,
            )
            loss = r.stdout.strip()
            if loss and int(loss) > 0:
                return {
                    "type": "network",
                    "severity": "high" if int(loss) > 5 else "medium",
                    "description": f"Packet loss detected: {loss}%",
                    "recommendation": "Check WiFi signal strength, restart network equipment, verify cable connections",
                }
        except:
            pass
        return None

    def get_health_score(self) -> Dict[str, Any]:
        result = self.analyze()
        return {
            "score": result["score"],
            "label": result["label"],
            "color": result["color"],
            "cpu": result["components"]["cpu"],
            "memory": result["components"]["memory"],
            "disk": result["components"]["disk"],
            "gpu": result["components"].get("gpu", 0),
            "network": result["components"].get("network", 0),
            "overall": result["score"],
            "details": result["details"],
        }

    def troubleshoot(self, problem: str) -> List[Dict[str, Any]]:
        try:
            from core.ai.recommendation_engine import RecommendationEngine
            engine = RecommendationEngine(self._os_type)
            return engine.troubleshoot(problem)
        except ImportError:
            return [{"issue_matched": "general", "confidence": 0.5, "suggestions": [{"title": "Run Health Check", "description": "Unable to load recommendation engine. Run a full system health analysis.", "action": "analyze"}]}]

    def get_maintenance_suggestions(self) -> Dict[str, Any]:
        try:
            from core.ai.recommendation_engine import RecommendationEngine
            engine = RecommendationEngine(self._os_type)
            items = engine.get_maintenance_suggestions()
            return {"suggestions": items, "count": len(items)}
        except ImportError:
            return {"suggestions": [], "count": 0}
