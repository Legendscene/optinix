from core.base import OptimizerBase
from core.config import CONFIG
from core.scanner import SystemScanner
from core.hardware_detection import HardwareDetector
from core.smart_detect import SmartDetector


class SystemReportOptimizer(OptimizerBase):
    name = "System Health Report"
    description = "Generates a comprehensive read-only system health report covering CPU, memory, disks, network, GPU, and recommendations."
    category = "safe"
    benefit = "Provides a full picture of system health, resource usage, and actionable recommendations."
    risks = "None — read-only information gathering."
    admin_required = False
    requires_reboot = False
    requirements = {}
    rollback_supported = False

    def run(self):
        scanner = SystemScanner(CONFIG.os_type)
        hardware = HardwareDetector()
        smart = SmartDetector(CONFIG.os_type)

        scan = scanner.full_scan()
        hw_info = hardware.detect_all()
        recommendations = smart.get_recommendations()

        sys_info = scan.get("system", {})
        self.add_result(True, "System Information", **{
            "section": "System",
            "os": sys_info.get("os", "Unknown"),
            "platform": sys_info.get("platform", "Unknown"),
            "uptime": sys_info.get("uptime", "N/A"),
            "uptime_seconds": sys_info.get("uptime_seconds", 0),
            "machine": sys_info.get("machine", "Unknown"),
            "processor": sys_info.get("processor", "Unknown"),
            "is_laptop": hw_info.get("system", {}).get("is_laptop", False),
            "is_vm": hw_info.get("system", {}).get("is_vm", False),
            "windows_build": hw_info.get("system", {}).get("os", {}).get("build", "N/A"),
            "power_plan": hw_info.get("power_plan", {}).get("name", "Unknown"),
            "is_high_performance": hw_info.get("power_plan", {}).get("is_high_performance", False),
        })

        cpu = scan.get("cpu", {})
        freq = cpu.get("freq") or {}
        self.add_result(True, "CPU Information", **{
            "section": "CPU",
            "usage_percent": cpu.get("percent", 0),
            "logical_cores": cpu.get("logical", 0),
            "physical_cores": cpu.get("physical", 0),
            "frequency_current_mhz": freq.get("current"),
            "frequency_max_mhz": freq.get("max"),
            "frequency_min_mhz": freq.get("min"),
            "temperature_celsius": cpu.get("temperature"),
            "vendor": hw_info.get("cpu", {}).get("vendor", "Unknown"),
            "brand": hw_info.get("cpu", {}).get("brand", "Unknown"),
        })

        mem = scan.get("memory", {})
        self.add_result(True, "Memory Information", **{
            "section": "Memory",
            "total_gb": mem.get("total_gb", 0),
            "used_gb": mem.get("used_gb", 0),
            "available_gb": mem.get("available_gb", 0),
            "used_percent": mem.get("percent", 0),
            "total_bytes": mem.get("total", 0),
            "used_bytes": mem.get("used", 0),
            "available_bytes": mem.get("available", 0),
            "swap_total": mem.get("swap_total", 0),
            "swap_used": mem.get("swap_used", 0),
            "swap_percent": mem.get("swap_percent", 0),
        })

        disks = scan.get("disk", [])
        for i, disk in enumerate(disks):
            self.add_result(True, f"Disk {disk.get('device', '?')}", **{
                "section": "Disks",
                "index": i,
                "device": disk.get("device", "Unknown"),
                "mountpoint": disk.get("mountpoint", ""),
                "filesystem": disk.get("fstype", ""),
                "total_bytes": disk.get("total", 0),
                "used_bytes": disk.get("used", 0),
                "free_bytes": disk.get("free", 0),
                "used_percent": disk.get("percent", 0),
                "total_gb": round(disk.get("total", 0) / (1024**3), 1),
                "used_gb": round(disk.get("used", 0) / (1024**3), 1),
                "free_gb": round(disk.get("free", 0) / (1024**3), 1),
            })

        net = scan.get("network", {})
        self.add_result(True, "Network Information", **{
            "section": "Network",
            "bytes_sent": net.get("bytes_sent", 0),
            "bytes_received": net.get("bytes_recv", 0),
            "speed_up_bps": net.get("speed_up", 0),
            "speed_down_bps": net.get("speed_down", 0),
            "interface_count": len(net.get("interfaces", [])),
        })

        gpu = scan.get("gpu", {})
        self.add_result(True, "GPU Information", **{
            "section": "GPU",
            "name": gpu.get("name", "N/A"),
            "usage_percent": gpu.get("usage", 0),
            "memory_total": gpu.get("memory_total", 0),
            "memory_used": gpu.get("memory_used", 0),
            "temperature_celsius": gpu.get("temperature", 0),
            "driver": gpu.get("driver", "N/A"),
            "vendor": hw_info.get("gpu", {}).get("vendor", "Unknown"),
        })

        for rec in recommendations:
            self.add_result(True, rec.get("message", "Recommendation"), **{
                "section": "Recommendations",
                "type": rec.get("type", "general"),
                "priority": rec.get("priority", "low"),
            })

        return [r.to_dict() for r in self.results]
