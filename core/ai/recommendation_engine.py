import os
import platform
import subprocess
from typing import Dict, Any, List, Optional


class RecommendationEngine:
    def __init__(self, *args, **kwargs):
        self._os_type = args[0] if args else kwargs.get("os_type", "windows")
        self._is_windows = self._os_type == "windows"

    def get_recommendations(self, hardware_info: dict = None) -> List[Dict[str, Any]]:
        recs = []
        recs.extend(self._maintenance_recs())
        recs.extend(self._performance_recs())
        recs.extend(self._privacy_recs())
        recs.extend(self._security_recs())
        recs.extend(self._power_recs())
        recs.extend(self._gaming_recs())
        recs.sort(key=lambda r: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(r.get("priority", "low"), 4))
        return recs

    def _maintenance_recs(self) -> List[Dict[str, Any]]:
        recs = []

        recs.append({
            "type": "maintenance",
            "priority": "medium",
            "title": "Clear Temporary Files",
            "description": "Remove Windows temporary files, cache, and prefetch data to free up disk space and improve system responsiveness.",
            "benefit": "Frees up to several GB of disk space",
            "risk": "safe",
            "category": "safe",
        })

        recs.append({
            "type": "maintenance",
            "priority": "low",
            "title": "Run Disk Cleanup",
            "description": "Use Windows Disk Cleanup to remove system files, update caches, and old Windows installations.",
            "benefit": "Frees significant disk space and improves filesystem performance",
            "risk": "safe",
            "category": "safe",
        })

        recs.append({
            "type": "maintenance",
            "priority": "medium",
            "title": "Back Up Registry",
            "description": "Create a backup of the Windows Registry before making system changes.",
            "benefit": "Provides restore point if registry modifications cause issues",
            "risk": "safe",
            "category": "safe",
        })

        recs.append({
            "type": "maintenance",
            "priority": "high",
            "title": "Run System File Checker (SFC)",
            "description": "Scan and repair corrupted Windows system files using sfc /scannow.",
            "benefit": "Fixes system file corruption that can cause crashes and instability",
            "risk": "safe",
            "category": "safe",
        })

        recs.append({
            "type": "maintenance",
            "priority": "medium",
            "title": "Defragment HDD or Optimize SSD",
            "description": "Defragment traditional hard drives or run TRIM on SSDs to maintain peak performance.",
            "benefit": "Improves read/write speeds and extends drive lifespan",
            "risk": "safe",
            "category": "safe",
        })

        recs.append({
            "type": "maintenance",
            "priority": "low",
            "title": "Check for Windows Updates",
            "description": "Ensure the system has the latest Windows updates installed for security and stability.",
            "benefit": "Patches security vulnerabilities and improves system stability",
            "risk": "safe",
            "category": "safe",
        })

        return recs

    def _performance_recs(self) -> List[Dict[str, Any]]:
        recs = []

        recs.append({
            "type": "performance",
            "priority": "high",
            "title": "Disable Unnecessary Startup Programs",
            "description": "Reduce boot time by disabling programs that launch automatically at startup.",
            "benefit": "Faster boot times and lower background resource usage",
            "risk": "safe",
            "category": "safe",
        })

        recs.append({
            "type": "performance",
            "priority": "medium",
            "title": "Disable Unnecessary Windows Services",
            "description": "Stop and disable background services that consume CPU and memory resources.",
            "benefit": "Frees up system resources for foreground applications",
            "risk": "advanced",
            "category": "advanced",
        })

        recs.append({
            "type": "performance",
            "priority": "medium",
            "title": "Adjust Visual Effects",
            "description": "Disable animations, transparency, and other visual effects for better performance.",
            "benefit": "Improves UI responsiveness on lower-end hardware",
            "risk": "safe",
            "category": "safe",
        })

        recs.append({
            "type": "performance",
            "priority": "high",
            "title": "Enable Game Mode",
            "description": "Turn on Windows Game Mode to prioritize gaming performance.",
            "benefit": "Better frame rates and reduced background interference during gaming",
            "risk": "safe",
            "category": "safe",
        })

        recs.append({
            "type": "performance",
            "priority": "medium",
            "title": "Enable Hardware-Accelerated GPU Scheduling",
            "description": "Let the GPU manage its own memory for reduced latency and improved performance.",
            "benefit": "Lower input lag and smoother rendering in supported applications",
            "risk": "safe",
            "category": "safe",
        })

        recs.append({
            "type": "performance",
            "priority": "low",
            "title": "Adjust Processor Scheduling",
            "description": "Optimize processor scheduling for programs (vs background services) for better application responsiveness.",
            "benefit": "Smoother application performance under load",
            "risk": "advanced",
            "category": "advanced",
        })

        recs.append({
            "type": "performance",
            "priority": "medium",
            "title": "Disable SysMain (Superfetch)",
            "description": "Disable the SysMain service which preloads applications into memory — can help on SSDs where it provides minimal benefit.",
            "benefit": "Reduces memory usage and disk activity",
            "risk": "advanced",
            "category": "advanced",
        })

        return recs

    def _privacy_recs(self) -> List[Dict[str, Any]]:
        recs = []

        recs.append({
            "type": "privacy",
            "priority": "low",
            "title": "Disable Telemetry and Data Collection",
            "description": "Limit or disable Windows telemetry features that send usage data to Microsoft.",
            "benefit": "Enhanced privacy and reduced background network activity",
            "risk": "advanced",
            "category": "advanced",
        })

        recs.append({
            "type": "privacy",
            "priority": "low",
            "title": "Disable Advertising ID",
            "description": "Turn off the unique advertising ID that Windows and apps use for personalized ads.",
            "benefit": "Reduces targeted advertising and tracking",
            "risk": "safe",
            "category": "safe",
        })

        recs.append({
            "type": "privacy",
            "priority": "low",
            "title": "Disable Cortana",
            "description": "Disable Cortana voice assistant to reduce background resource usage and improve privacy.",
            "benefit": "Frees up memory and background CPU, improves privacy",
            "risk": "safe",
            "category": "safe",
        })

        recs.append({
            "type": "privacy",
            "priority": "low",
            "title": "Disable Location Tracking",
            "description": "Turn off location services for apps that do not need them.",
            "benefit": "Improved privacy and reduced background sensor usage",
            "risk": "safe",
            "category": "safe",
        })

        return recs

    def _security_recs(self) -> List[Dict[str, Any]]:
        recs = []

        recs.append({
            "type": "security",
            "priority": "critical",
            "title": "Install Pending Windows Updates",
            "description": "Critical security updates are pending installation. Restart your system to apply them.",
            "benefit": "Patches known security vulnerabilities",
            "risk": "safe",
            "category": "safe",
        })

        recs.append({
            "type": "security",
            "priority": "high",
            "title": "Run Windows Defender Full Scan",
            "description": "Perform a full system scan with Windows Defender to detect and remove malware.",
            "benefit": "Detects and removes viruses, spyware, and other malicious software",
            "risk": "safe",
            "category": "safe",
        })

        recs.append({
            "type": "security",
            "priority": "high",
            "title": "Verify Firewall Status",
            "description": "Ensure Windows Defender Firewall is enabled on all network profiles.",
            "benefit": "Blocks unauthorized network access to your system",
            "risk": "safe",
            "category": "safe",
        })

        recs.append({
            "type": "security",
            "priority": "medium",
            "title": "Enable User Account Control (UAC)",
            "description": "Ensure UAC is enabled to prevent unauthorized system changes.",
            "benefit": "Prevents malware from making silent system changes",
            "risk": "safe",
            "category": "safe",
        })

        return recs

    def _power_recs(self) -> List[Dict[str, Any]]:
        recs = []

        recs.append({
            "type": "power",
            "priority": "high",
            "title": "Switch to High Performance Power Plan",
            "description": "Set the active power plan to High Performance to prevent CPU throttling and improve responsiveness.",
            "benefit": "Maximum CPU and GPU performance at the cost of higher power consumption",
            "risk": "safe",
            "category": "safe",
        })

        recs.append({
            "type": "power",
            "priority": "medium",
            "title": "Enable Ultimate Performance Power Plan",
            "description": "Enable Windows Ultimate Performance plan that removes micro-latencies for demanding workloads.",
            "benefit": "Lower latency and maximum throughput for high-performance tasks",
            "risk": "advanced",
            "category": "advanced",
        })

        recs.append({
            "type": "power",
            "priority": "medium",
            "title": "Optimize Battery Saver Settings",
            "description": "Configure battery saver thresholds for optimal balance of performance and battery life on laptops.",
            "benefit": "Extended battery life when unplugged",
            "risk": "safe",
            "category": "safe",
        })

        recs.append({
            "type": "power",
            "priority": "low",
            "title": "Disable Hibernation",
            "description": "Disable hibernation to free up disk space equal to your RAM size.",
            "benefit": "Recovers significant disk space (same as installed RAM size)",
            "risk": "advanced",
            "category": "advanced",
        })

        recs.append({
            "type": "power",
            "priority": "low",
            "title": "Enable Fast Startup",
            "description": "Enable hybrid shutdown for faster boot times after shutdown (not restart).",
            "benefit": "Reduces cold boot time significantly",
            "risk": "safe",
            "category": "safe",
        })

        return recs

    def _gaming_recs(self) -> List[Dict[str, Any]]:
        recs = []

        recs.append({
            "type": "gaming",
            "priority": "high",
            "title": "Enable Game Mode",
            "description": "Turn on Windows Game Mode to prioritize game processes and reduce background activity.",
            "benefit": "More consistent frame rates and reduced stuttering",
            "risk": "safe",
            "category": "safe",
        })

        recs.append({
            "type": "gaming",
            "priority": "medium",
            "title": "Disable Game DVR and Game Bar",
            "description": "Turn off Xbox Game Bar and background recording to free up GPU resources.",
            "benefit": "Frees GPU memory and improves FPS by up to 5-10%",
            "risk": "safe",
            "category": "safe",
        })

        recs.append({
            "type": "gaming",
            "priority": "medium",
            "title": "Set High Performance GPU Preference",
            "description": "Configure specific games to use the dedicated high-performance GPU in multi-GPU systems.",
            "benefit": "Ensures games use the discrete GPU instead of integrated graphics",
            "risk": "safe",
            "category": "safe",
        })

        recs.append({
            "type": "gaming",
            "priority": "medium",
            "title": "Disable Fullscreen Optimizations",
            "description": "Disable Windows fullscreen optimizations for games to reduce input lag.",
            "benefit": "Lower input latency and smoother gameplay in fullscreen mode",
            "risk": "advanced",
            "category": "advanced",
        })

        recs.append({
            "type": "gaming",
            "priority": "low",
            "title": "Enable Hardware-Accelerated GPU Scheduling",
            "description": "Reduce GPU scheduling overhead by letting the GPU manage its own video memory.",
            "benefit": "Lower rendering latency and improved FPS in supported titles",
            "risk": "safe",
            "category": "safe",
        })

        recs.append({
            "type": "gaming",
            "priority": "high",
            "title": "Set High Performance Power Plan",
            "description": "Use the High Performance or Ultimate Performance power plan during gaming sessions.",
            "benefit": "Prevents CPU/GPU throttling for maximum gaming performance",
            "risk": "safe",
            "category": "safe",
        })

        return recs

    def get_maintenance_suggestions(self) -> List[Dict[str, Any]]:
        suggestions = []

        suggestions.append({
            "task": "Temporary File Cleanup",
            "due": "7 days",
            "priority": "medium",
            "description": "Clear temp files, browser cache, and prefetch data to free disk space",
            "category": "cleanup",
        })

        suggestions.append({
            "task": "Disk Cleanup (System Files)",
            "due": "30 days",
            "priority": "medium",
            "description": "Run Windows Disk Cleanup to remove Windows Update cache and old system files",
            "category": "cleanup",
        })

        suggestions.append({
            "task": "SFC Scan (System File Checker)",
            "due": "30 days",
            "priority": "high",
            "description": "Scan and repair corrupted Windows system files",
            "category": "maintenance",
        })

        suggestions.append({
            "task": "DISM Health Restore",
            "due": "60 days",
            "priority": "high",
            "description": "Repair Windows component store corruption using DISM",
            "category": "maintenance",
        })

        suggestions.append({
            "task": "Defragment / Optimize Drives",
            "due": "30 days",
            "priority": "low",
            "description": "Defragment HDDs or run TRIM on SSDs for optimal performance",
            "category": "maintenance",
        })

        suggestions.append({
            "task": "Driver Updates Check",
            "due": "14 days",
            "priority": "high",
            "description": "Check for and install critical driver updates for system hardware",
            "category": "drivers",
        })

        suggestions.append({
            "task": "Windows Update Check",
            "due": "7 days",
            "priority": "critical",
            "description": "Install pending Windows security and quality updates",
            "category": "security",
        })

        suggestions.append({
            "task": "Startup Program Review",
            "due": "14 days",
            "priority": "medium",
            "description": "Review and disable unnecessary startup programs for faster boot",
            "category": "performance",
        })

        suggestions.append({
            "task": "Registry Backup",
            "due": "90 days",
            "priority": "low",
            "description": "Create a backup of the Windows Registry before making system changes",
            "category": "maintenance",
        })

        suggestions.append({
            "task": "Browser Cache Cleanup",
            "due": "7 days",
            "priority": "low",
            "description": "Clear browser cache, cookies, and browsing history for all installed browsers",
            "category": "cleanup",
        })

        return suggestions

    def get_gaming_recommendations(self) -> List[Dict[str, Any]]:
        recs = self._gaming_recs()

        try:
            game_mode = self._check_game_mode()
        except:
            game_mode = "Unknown"

        try:
            gpu_sched = self._check_gpu_scheduling()
        except:
            gpu_sched = "Unknown"

        try:
            power_plan = self._get_current_power_plan()
        except:
            power_plan = "Unknown"

        threshold_boost = self._check_threshold_boost()

        return {
            "recommendations": recs,
            "count": len(recs),
            "current_settings": {
                "game_mode": game_mode,
                "gpu_hardware_scheduling": gpu_sched,
                "power_plan": power_plan,
                "gaming_score": self._compute_gaming_score(),
            },
            "details": {
                "gpu_throttling_risk": threshold_boost,
            },
        }

    def _check_game_mode(self) -> str:
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\GameBar' -Name 'AllowAutoGameMode').AllowAutoGameMode"],
                capture_output=True, text=True, timeout=5,
            )
            val = r.stdout.strip()
            return "Enabled" if val == "1" else "Disabled"
        except:
            return "Unknown"

    def _check_gpu_scheduling(self) -> str:
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-ItemProperty -Path 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\GraphicsDrivers' -Name 'HwSchMode').HwSchMode"],
                capture_output=True, text=True, timeout=5,
            )
            val = r.stdout.strip()
            return "Enabled" if val == "2" else "Disabled"
        except:
            return "Unknown"

    def _get_current_power_plan(self) -> str:
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-CimInstance -Name Win32_PowerPlan -Filter 'IsActive = True').ElementName"],
                capture_output=True, text=True, timeout=5,
            )
            return r.stdout.strip() or "Unknown"
        except:
            return "Unknown"

    def _check_threshold_boost(self) -> str:
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-ItemProperty -Path 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Power\\PowerThrottling' -Name 'PowerThrottlingOff' -ErrorAction SilentlyContinue).PowerThrottlingOff"],
                capture_output=True, text=True, timeout=5,
            )
            val = r.stdout.strip()
            return "Low — throttling may be active" if val != "1" else "High — throttling disabled"
        except:
            return "Unknown"

    def _compute_gaming_score(self) -> int:
        score = 50
        try:
            if self._check_game_mode() == "Enabled":
                score += 15
        except:
            pass
        try:
            if self._check_gpu_scheduling() == "Enabled":
                score += 10
        except:
            pass
        try:
            plan = self._get_current_power_plan()
            if "High Performance" in plan or "Ultimate" in plan:
                score += 15
            elif "Balanced" in plan:
                score += 5
        except:
            pass
        try:
            mem = __import__("psutil").virtual_memory()
            if mem.available / mem.total > 0.3:
                score += 10
        except:
            pass
        return min(100, score)

    def troubleshoot(self, problem: str) -> List[Dict[str, Any]]:
        if not problem:
            return [self._general_check()]

        problem_lower = problem.lower()

        if any(kw in problem_lower for kw in ("slow boot", "slow startup", "long boot", "takes forever to start")):
            return [self._slow_boot_troubleshoot()]

        if any(kw in problem_lower for kw in ("slow game", "low fps", "lag", "stutter", "game stuttering", "low frame rate")):
            return [self._slow_game_troubleshoot()]

        if any(kw in problem_lower for kw in ("crash", "blue screen", "bsod", "system crash", "freeze", "hard lock")):
            return [self._crash_troubleshoot()]

        if any(kw in problem_lower for kw in ("internet", "slow network", "wifi", "network", "connection", "slow internet", "no internet")):
            return [self._network_troubleshoot()]

        if any(kw in problem_lower for kw in ("disk full", "no space", "out of space", "low disk space", "storage full")):
            return [self._disk_full_troubleshoot()]

        if any(kw in problem_lower for kw in ("ram", "memory", "slow pc", "computer slow", "running slow", "slow computer", "slow performance")):
            return [self._ram_troubleshoot()]

        return [self._general_check()]

    def _slow_boot_troubleshoot(self) -> Dict[str, Any]:
        return {
            "issue_matched": "slow startup",
            "confidence": 0.85,
            "suggestions": [
                {
                    "title": "Disable Unnecessary Startup Programs",
                    "description": "Open Task Manager > Startup tab and disable programs that are not needed at boot.",
                    "action": "ms-settings:startupapps",
                },
                {
                    "title": "Check Disk Health",
                    "description": "Run CHKDSK to check for disk errors that may slow down boot.",
                    "action": "chkdsk /f",
                },
                {
                    "title": "Enable Fast Startup",
                    "description": "Enable hybrid shutdown in Power Options for faster boots.",
                    "action": "powercfg /hibernate on",
                },
                {
                    "title": "Check if Boot Drive is SSD",
                    "description": "If running Windows on an HDD, upgrading to an SSD provides the biggest boot time improvement.",
                    "action": "check_disk_type",
                },
                {
                    "title": "Reduce Boot Timeout",
                    "description": "Lower the boot menu timeout in System Configuration.",
                    "action": "msconfig",
                },
            ],
        }

    def _slow_game_troubleshoot(self) -> Dict[str, Any]:
        return {
            "issue_matched": "low gaming performance",
            "confidence": 0.8,
            "suggestions": [
                {
                    "title": "Enable Game Mode",
                    "description": "Windows Game Mode prioritizes game processes for better performance.",
                    "action": "game_mode_enable",
                },
                {
                    "title": "Switch to High Performance Power Plan",
                    "description": "Prevents CPU/GPU throttling during gaming sessions.",
                    "action": "powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
                },
                {
                    "title": "Disable Game DVR and Background Recording",
                    "description": "Xbox Game Bar recording consumes GPU resources in the background.",
                    "action": "game_dvr_disable",
                },
                {
                    "title": "Close Background Applications",
                    "description": "Close browser tabs, chat apps, and other programs consuming CPU and memory.",
                    "action": "task_manager",
                },
                {
                    "title": "Update GPU Drivers",
                    "description": "Outdated graphics drivers can significantly impact gaming performance.",
                    "action": "driver_update",
                },
                {
                    "title": "Lower Graphics Settings",
                    "description": "Reduce in-game resolution, texture quality, and shadow details for smoother gameplay.",
                    "action": "in_game_settings",
                },
            ],
        }

    def _crash_troubleshoot(self) -> Dict[str, Any]:
        return {
            "issue_matched": "system crash / BSOD",
            "confidence": 0.75,
            "suggestions": [
                {
                    "title": "Run System File Checker",
                    "description": "Scan and repair corrupted Windows system files.",
                    "action": "sfc /scannow",
                },
                {
                    "title": "Run DISM Health Restore",
                    "description": "Repair Windows component store corruption.",
                    "action": "dism /online /cleanup-image /restorehealth",
                },
                {
                    "title": "Run Windows Memory Diagnostic",
                    "description": "Check for faulty RAM modules that can cause crashes and BSODs.",
                    "action": "mdsched.exe",
                },
                {
                    "title": "Check for Driver Issues",
                    "description": "Faulty or outdated drivers are a common cause of BSODs.",
                    "action": "driver_verifier",
                },
                {
                    "title": "Analyze Crash Dumps",
                    "description": "Check %SystemRoot%\\Minidump for crash dump files to identify the cause.",
                    "action": "analyze_dumps",
                },
                {
                    "title": "Check Disk for Errors",
                    "description": "Run CHKDSK to rule out disk corruption causing crashes.",
                    "action": "chkdsk /f /r",
                },
            ],
        }

    def _network_troubleshoot(self) -> Dict[str, Any]:
        return {
            "issue_matched": "network / internet issue",
            "confidence": 0.8,
            "suggestions": [
                {
                    "title": "Flush DNS Cache",
                    "description": "Clear the DNS resolver cache to fix resolution issues.",
                    "action": "ipconfig /flushdns",
                },
                {
                    "title": "Reset Network Stack",
                    "description": "Reset Winsock, IP configuration, and TCP/IP stack.",
                    "action": "netsh int ip reset && netsh winsock reset",
                },
                {
                    "title": "Update Network Adapter Drivers",
                    "description": "Outdated network drivers can cause slow speeds and disconnections.",
                    "action": "driver_update_network",
                },
                {
                    "title": "Disable Background Bandwidth Apps",
                    "description": "Check for apps consuming bandwidth in the background (updates, cloud sync).",
                    "action": "task_manager_network",
                },
                {
                    "title": "Run Windows Network Troubleshooter",
                    "description": "Let Windows automatically detect and fix network problems.",
                    "action": "ms-settings:troubleshoot",
                },
                {
                    "title": "Change DNS to Google or Cloudflare",
                    "description": "Switching to 8.8.8.8 / 1.1.1.1 can improve DNS resolution speed.",
                    "action": "change_dns",
                },
            ],
        }

    def _disk_full_troubleshoot(self) -> Dict[str, Any]:
        return {
            "issue_matched": "disk space full",
            "confidence": 0.9,
            "suggestions": [
                {
                    "title": "Run Disk Cleanup",
                    "description": "Use Windows Disk Cleanup to remove temp files, recycle bin, and update cache.",
                    "action": "cleanmgr.exe",
                },
                {
                    "title": "Clear Temporary Files",
                    "description": "Remove files from %TEMP%, prefetch, and browser caches.",
                    "action": "clean_temp",
                },
                {
                    "title": "Uninstall Unused Applications",
                    "description": "Remove programs that are no longer needed to free up space.",
                    "action": "ms-settings:appsfeatures",
                },
                {
                    "title": "Run Duplicate File Finder",
                    "description": "Find and remove duplicate files taking up unnecessary space.",
                    "action": "deduplicate",
                },
                {
                    "title": "Move Files to External Storage",
                    "description": "Transfer large media files, documents, or projects to an external drive or cloud storage.",
                    "action": "move_files",
                },
                {
                    "title": "Disable Hibernation",
                    "description": "Disable hibernation to free up disk space equal to your RAM size.",
                    "action": "powercfg /hibernate off",
                },
            ],
        }

    def _ram_troubleshoot(self) -> Dict[str, Any]:
        return {
            "issue_matched": "low memory / slow performance",
            "confidence": 0.8,
            "suggestions": [
                {
                    "title": "Close Memory-Heavy Applications",
                    "description": "Check Task Manager for apps consuming large amounts of RAM and close unused ones.",
                    "action": "task_manager",
                },
                {
                    "title": "Disable Startup Programs",
                    "description": "Prevent unnecessary programs from loading at startup and consuming memory.",
                    "action": "ms-settings:startupapps",
                },
                {
                    "title": "Disable Unnecessary Background Services",
                    "description": "Stop services like SysMain (Superfetch) and Windows Search to free memory.",
                    "action": "services.msc",
                },
                {
                    "title": "Adjust Visual Effects for Best Performance",
                    "description": "Disable animations and visual effects to reduce memory usage.",
                    "action": "system_properties_performance",
                },
                {
                    "title": "Check for Memory Leaks",
                    "description": "Monitor memory usage over time to identify leaking applications.",
                    "action": "resource_monitor",
                },
                {
                    "title": "Increase Virtual Memory",
                    "description": "Adjust the paging file size if physical RAM is insufficient.",
                    "action": "virtual_memory_settings",
                },
            ],
        }

    def _general_check(self) -> Dict[str, Any]:
        return {
            "issue_matched": "general system health",
            "confidence": 0.5,
            "suggestions": [
                {
                    "title": "Run Full System Health Analysis",
                    "description": "Perform a comprehensive check of CPU, memory, disk, and system health.",
                    "action": "analyze",
                },
                {
                    "title": "Run Windows Update",
                    "description": "Check for and install the latest Windows updates.",
                    "action": "ms-settings:windowsupdate",
                },
                {
                    "title": "Scan for Malware",
                    "description": "Run a full Windows Defender scan to rule out malware.",
                    "action": "windows_defender_scan",
                },
                {
                    "title": "Check for Driver Updates",
                    "description": "Update drivers for critical hardware components.",
                    "action": "driver_update",
                },
                {
                    "title": "Run Disk Cleanup",
                    "description": "Free up disk space and improve system responsiveness.",
                    "action": "cleanmgr.exe",
                },
            ],
        }


smart_recommendations = RecommendationEngine
