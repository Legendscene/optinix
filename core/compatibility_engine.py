import json
import os
import subprocess
from typing import Dict, List, Any, Optional
from .hardware_detection import HardwareDetector


# Category definitions
CATEGORY_SAFE = "safe"
CATEGORY_ADVANCED = "advanced"
CATEGORY_EXPERIMENTAL = "experimental"

OPTIMIZATIONS: Dict[str, Dict[str, Any]] = {
    # ==================== SAFE (Green) ====================
    "privacy_telemetry": {
        "name": "Disable Telemetry",
        "category": CATEGORY_SAFE,
        "description": "Opts out of Windows telemetry data collection",
        "benefit": "Reduces network usage and Microsoft data collection",
        "risks": "None",
        "admin_required": True,
    },
    "privacy_advertising_id": {
        "name": "Disable Advertising ID",
        "category": CATEGORY_SAFE,
        "description": "Disables the unique advertising identifier",
        "benefit": "Stops targeted advertising tracking",
        "risks": "None",
        "admin_required": False,
    },
    "privacy_cortana": {
        "name": "Disable Cortana",
        "category": CATEGORY_SAFE,
        "description": "Disables Cortana assistant",
        "benefit": "Saves ~200MB RAM, reduces background CPU",
        "risks": "Voice assistant disabled",
        "admin_required": True,
        "compatibility": {"min_win_build": 10240},
    },
    "privacy_location": {
        "name": "Disable Location Tracking",
        "category": CATEGORY_SAFE,
        "description": "Disables Windows location services",
        "benefit": "Privacy improvement",
        "risks": "Apps cannot use location",
        "admin_required": True,
    },
    "privacy_content_delivery": {
        "name": "Disable Content Delivery",
        "category": CATEGORY_SAFE,
        "description": "Stops automatic app reinstallation and suggestions",
        "benefit": "Prevents Windows from reinstalling bloatware",
        "risks": "None",
        "admin_required": True,
    },
    "ux_menu_delay": {
        "name": "Faster Menu Appearance",
        "category": CATEGORY_SAFE,
        "description": "Reduces menu show delay to 200ms",
        "benefit": "UI feels more responsive",
        "risks": "None",
        "admin_required": False,
    },
    "ux_file_explorer": {
        "name": "File Explorer opens to This PC",
        "category": CATEGORY_SAFE,
        "description": "Changes default File Explorer target from Quick Access to This PC",
        "benefit": "Faster access to drives",
        "risks": "None",
        "admin_required": False,
    },
    "ux_show_extensions": {
        "name": "Show File Extensions",
        "category": CATEGORY_SAFE,
        "description": "Makes file extensions visible in Explorer",
        "benefit": "Security improvement against disguised malware",
        "risks": "None",
        "admin_required": False,
    },
    "ux_show_hidden": {
        "name": "Show Hidden Files",
        "category": CATEGORY_SAFE,
        "description": "Shows hidden system files in Explorer",
        "benefit": "Better visibility of system files",
        "risks": "Can accidentally modify system files",
        "admin_required": False,
    },
    "ux_small_taskbar": {
        "name": "Small Taskbar Icons",
        "category": CATEGORY_SAFE,
        "description": "Uses smaller taskbar icons",
        "benefit": "Saves taskbar space",
        "risks": "None",
        "admin_required": False,
    },
    "ux_seconds_in_clock": {
        "name": "Show Seconds in Clock",
        "category": CATEGORY_SAFE,
        "description": "Displays seconds in system tray clock",
        "benefit": "More precise time display",
        "risks": "Minor battery impact on laptops",
        "admin_required": False,
    },
    "network_dns_flush": {
        "name": "Flush DNS Cache",
        "category": CATEGORY_SAFE,
        "description": "Clears DNS resolver cache",
        "benefit": "Resolves DNS-related connectivity issues",
        "risks": "None",
        "admin_required": True,
    },
    "network_dns_cloudflare": {
        "name": "Set DNS to Cloudflare",
        "category": CATEGORY_SAFE,
        "description": "Changes DNS server to Cloudflare 1.1.1.1",
        "benefit": "Faster and more private DNS resolution",
        "risks": "May not work with enterprise networks",
        "admin_required": True,
    },
    "network_tcp_autotuning": {
        "name": "TCP Auto-Tuning (Normal)",
        "category": CATEGORY_SAFE,
        "description": "Sets TCP auto-tuning level to normal",
        "benefit": "Default balanced TCP performance",
        "risks": "None",
        "admin_required": True,
    },
    "network_bbr2": {
        "name": "Enable BBR2 Congestion",
        "category": CATEGORY_SAFE,
        "description": "Enables BBR2 congestion control algorithm",
        "benefit": "Better throughput on high-latency connections",
        "risks": "Requires Win 11 or Win 10 21H2+",
        "admin_required": True,
        "compatibility": {"min_win_build": 19044},
    },
    "network_fastopen": {
        "name": "TCP Fast Open",
        "category": CATEGORY_SAFE,
        "description": "Enables TCP Fast Open via netsh",
        "benefit": "Reduced latency for repeated connections",
        "risks": "None",
        "admin_required": True,
    },
    "network_rss": {
        "name": "Enable RSS",
        "category": CATEGORY_SAFE,
        "description": "Enables Receive Side Scaling via netsh",
        "benefit": "Better multi-core network processing",
        "risks": "None",
        "admin_required": True,
    },
    "disk_trim": {
        "name": "Run SSD TRIM",
        "category": CATEGORY_SAFE,
        "description": "Sends TRIM command to SSD drives",
        "benefit": "Maintains SSD performance and lifespan",
        "risks": "None",
        "admin_required": True,
        "compatibility": {"ssd_only": True},
    },
    "disk_health": {
        "name": "Disk Health Check",
        "category": CATEGORY_SAFE,
        "description": "Checks disk health status via SMART",
        "benefit": "Early detection of disk failure",
        "risks": "None",
        "admin_required": False,
    },
    "memory_gc": {
        "name": "Gentle Memory Cleanup",
        "category": CATEGORY_SAFE,
        "description": "Triggers .NET garbage collection",
        "benefit": "Frees unused managed memory",
        "risks": "None",
        "admin_required": False,
    },
    "gaming_game_mode": {
        "name": "Enable Windows Game Mode",
        "category": CATEGORY_SAFE,
        "description": "Enables Windows Game Mode feature",
        "benefit": "Prioritizes game processes",
        "risks": "None",
        "admin_required": False,
    },
    "gaming_disable_dvr": {
        "name": "Disable Game DVR",
        "category": CATEGORY_SAFE,
        "description": "Disables Xbox Game DVR recording",
        "benefit": "Reduces GPU overhead during gaming",
        "risks": "Cannot record gameplay clips",
        "admin_required": False,
    },
    "gaming_high_priority": {
        "name": "Set Game Priority to HIGH",
        "category": CATEGORY_SAFE,
        "description": "Sets running game processes to HIGH priority class",
        "benefit": "Smoother gaming performance",
        "risks": "None (uses HIGH, not REALTIME)",
        "admin_required": False,
    },
    "cleanup_temp": {
        "name": "Delete Temporary Files",
        "category": CATEGORY_SAFE,
        "description": "Removes contents of %TEMP% folder",
        "benefit": "Frees disk space",
        "risks": "Some apps may need to recreate temp files",
        "admin_required": False,
    },
    "cleanup_recycle_bin": {
        "name": "Empty Recycle Bin",
        "category": CATEGORY_SAFE,
        "description": "Permanently deletes Recycle Bin contents",
        "benefit": "Frees disk space",
        "risks": "Cannot recover deleted files",
        "admin_required": False,
    },
    "services_basic_debloat": {
        "name": "Disable Basic Services",
        "category": CATEGORY_SAFE,
        "description": "Disables services: DiagTrack, WSearch, MapsBroker, RemoteRegistry, Xbox, edgeupdate, WerSvc",
        "benefit": "Reduces background overhead",
        "risks": "Windows Search disabled, map apps may not work",
        "admin_required": True,
    },
    "security_firewall": {
        "name": "Optimize Firewall Rules",
        "category": CATEGORY_SAFE,
        "description": "Ensures firewall is active with secure defaults",
        "benefit": "Security improvement",
        "risks": "None",
        "admin_required": True,
    },
    "gpu_hw_scheduling": {
        "name": "Enable HW GPU Scheduling",
        "category": CATEGORY_SAFE,
        "description": "Enables Hardware Accelerated GPU Scheduling",
        "benefit": "Lower GPU latency, better performance",
        "risks": "Requires reboot",
        "admin_required": True,
        "compatibility": {"min_win_build": 19041},
    },
    "developer_cleanup": {
        "name": "Developer Cache Cleanup",
        "category": CATEGORY_SAFE,
        "description": "Cleans npm, pip, pycache, git gc, docker, IDE caches",
        "benefit": "Frees disk space used by dev tools",
        "risks": "Will need to re-download packages",
        "admin_required": False,
    },

    # ==================== ADVANCED (Yellow) ====================
    "services_advanced_debloat": {
        "name": "Disable Advanced Services",
        "category": CATEGORY_ADVANCED,
        "description": "Disables additional services: SysMain, TabletInput, SharedAccess, TapiSrv, BthAvctpSvc, TrkWks, WbioSrvc, WpnService, BcastDVRUserService",
        "benefit": "Further reduces background processes",
        "risks": "SysMain helps SSD performance; Bluetooth may stop working",
        "admin_required": True,
        "compatibility": {"desktop_only": False},
    },
    "network_hystart": {
        "name": "Disable Hybrid Slow Start",
        "category": CATEGORY_ADVANCED,
        "description": "Disables TCP hybrid slow start via netsh",
        "benefit": "Faster connection ramp-up",
        "risks": "May cause congestion on shared networks",
        "admin_required": True,
    },
    "network_pacing": {
        "name": "Disable TCP Pacing",
        "category": CATEGORY_ADVANCED,
        "description": "Disables TCP pacing profile via netsh",
        "benefit": "Slightly higher throughput",
        "risks": "Can cause bursty traffic and packet loss",
        "admin_required": True,
    },
    "usb_selective_suspend": {
        "name": "Disable USB Selective Suspend",
        "category": CATEGORY_ADVANCED,
        "description": "Disables USB power saving",
        "benefit": "Prevents USB disconnects",
        "risks": "Increases power consumption on laptops",
        "admin_required": True,
        "compatibility": {"laptop_only": False},
    },
    "mouse_raw_input": {
        "name": "Disable Mouse Smoothing",
        "category": CATEGORY_ADVANCED,
        "description": "Sets mouse acceleration to zero, clears smooth mouse curves",
        "benefit": "Raw mouse input (preferred by gamers)",
        "risks": "Mouse may feel different in desktop use",
        "admin_required": False,
    },
    "nvme_queue_depth": {
        "name": "NVMe Queue Depth 256",
        "category": CATEGORY_ADVANCED,
        "description": "Sets NVMe driver queue depth to 256",
        "benefit": "Better NVMe SSD performance",
        "risks": "Minor increase in memory usage",
        "admin_required": True,
        "compatibility": {"ssd_only": True},
    },
    "visual_best_performance": {
        "name": "Best Performance Visuals",
        "category": CATEGORY_ADVANCED,
        "description": "Disables animations, transparency, shadows",
        "benefit": "Faster UI response on low-end systems",
        "risks": "Visual downgrade, no Aero effects",
        "admin_required": False,
    },
    "disable_hibernation": {
        "name": "Disable Hibernation",
        "category": CATEGORY_ADVANCED,
        "description": "Disables Fast Startup and hibernation",
        "benefit": "Frees disk space (~70%% of RAM size)",
        "risks": "Slower boot times, battery drain if shut down",
        "admin_required": True,
        "compatibility": {"desktop_only": False},
    },
    "disable_notification_center": {
        "name": "Disable Notification Center",
        "category": CATEGORY_ADVANCED,
        "description": "Disables Windows action center",
        "benefit": "Reduces distractions",
        "risks": "No notifications",
        "admin_required": False,
    },
    "startup_disable_all": {
        "name": "Disable All Startup Programs",
        "category": CATEGORY_ADVANCED,
        "description": "Disables every startup item",
        "benefit": "Faster boot time",
        "risks": "May disable useful background apps",
        "admin_required": True,
    },

    # ==================== EXPERIMENTAL (Red) ====================
    "network_tcp_registry_hacks": {
        "name": "TCP Registry Tweaks (TcpAckFrequency, TCPNoDelay)",
        "category": CATEGORY_EXPERIMENTAL,
        "description": "Sets TcpAckFrequency=1 and TCPNoDelay=1 in registry",
        "benefit": "Theoretical latency reduction",
        "risks": "NO documented effect on Windows 10/11 TCP stack. Placebo.",
        "admin_required": True,
    },
    "network_hash_table_tweaks": {
        "name": "TCP Hash Table Tweaks",
        "category": CATEGORY_EXPERIMENTAL,
        "description": "Sets MaxHashTableSize and MaxFreeTcbs in registry",
        "benefit": "Theoretical network performance",
        "risks": "Registry keys likely don't exist on modern Windows. Placebo.",
        "admin_required": True,
    },
    "disable_prefetcher": {
        "name": "Disable Prefetcher",
        "category": CATEGORY_EXPERIMENTAL,
        "description": "Sets EnablePrefetcher=0 in registry",
        "benefit": "Theoretical RAM saving",
        "risks": "HARMS boot time and app launch performance. Prefetcher is optimized for SSDs.",
        "admin_required": True,
    },
    "disable_superfetch": {
        "name": "Disable SysMain (Superfetch)",
        "category": CATEGORY_EXPERIMENTAL,
        "description": "Sets EnableSuperfetch=0 in registry",
        "benefit": "Theoretical RAM saving",
        "risks": "HARMS app launch performance on SSDs. SysMain preloads frequently used apps.",
        "admin_required": True,
    },
    "disable_uac": {
        "name": "Disable UAC",
        "category": CATEGORY_EXPERIMENTAL,
        "description": "Sets EnableLUA=0 in registry",
        "benefit": "No admin prompts",
        "risks": "Security vulnerability. Apps can make system changes without consent.",
        "admin_required": True,
    },
    "adapter_gaming_preset": {
        "name": "Network Adapter Gaming Preset",
        "category": CATEGORY_EXPERIMENTAL,
        "description": "Disables Interrupt Moderation, RSC, LSO, Flow Control on adapter",
        "benefit": "Potential latency reduction",
        "risks": "Increases CPU load, may cause network instability or packet loss",
        "admin_required": True,
    },
    "adapter_streaming_preset": {
        "name": "Network Adapter Streaming Preset",
        "category": CATEGORY_EXPERIMENTAL,
        "description": "Enables Jumbo Frames 9014, RSC, Flow Control on adapter",
        "benefit": "Potential throughput increase",
        "risks": "Jumbo frames can cause issues with mismatched network hardware",
        "admin_required": True,
    },
}


class CompatibilityEngine:
    def __init__(self, os_type: str):
        self.os_type = os_type
        self.detector = HardwareDetector()

    def get_optimizations(self) -> Dict[str, Dict[str, Any]]:
        """Returns all optimizations with their categories."""
        return OPTIMIZATIONS

    def get_optimizations_by_category(self) -> Dict[str, List[Dict[str, Any]]]:
        """Returns optimizations grouped by category."""
        result = {CATEGORY_SAFE: [], CATEGORY_ADVANCED: [], CATEGORY_EXPERIMENTAL: []}
        for key, opt in OPTIMIZATIONS.items():
            cat = opt.get("category", CATEGORY_SAFE)
            entry = {"id": key, **opt}
            result.setdefault(cat, []).append(entry)
        return result

    def check(self, optimization_id: str) -> Dict[str, Any]:
        """Checks compatibility for a single optimization."""
        opt = OPTIMIZATIONS.get(optimization_id)
        if not opt:
            return {"compatible": False, "reason": f"Unknown optimization: {optimization_id}"}

        reqs = opt.get("compatibility", {})
        if opt.get("admin_required"):
            reqs["admin_required"] = True

        compatibility = self.detector.check_compatibility(reqs)
        failures = {k: v for k, v in compatibility.items() if v.startswith("fail:")}
        passes = {k: v for k, v in compatibility.items() if v == "pass"}

        return {
            "compatible": len(failures) == 0 and opt.get("category") != CATEGORY_EXPERIMENTAL,
            "category": opt.get("category", CATEGORY_SAFE),
            "compatibility": compatibility,
            "failures": failures,
            "passes": passes,
            "admin_required": opt.get("admin_required", False),
            "risks": opt.get("risks", ""),
            "description": opt.get("description", ""),
        }

    def check_multiple(self, optimization_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Checks compatibility for multiple optimizations."""
        return {oid: self.check(oid) for oid in optimization_ids}

    def filter_compatible(self, optimization_ids: List[str], category_filter: Optional[str] = None) -> List[str]:
        """Filters to only compatible optimizations, optionally by category."""
        result = []
        for oid in optimization_ids:
            opt = OPTIMIZATIONS.get(oid)
            if not opt:
                continue
            if category_filter and opt.get("category") != category_filter:
                continue
            check_result = self.check(oid)
            if check_result["compatible"] or check_result["category"] == CATEGORY_SAFE:
                result.append(oid)
        return result
