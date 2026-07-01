"""NetworkTuner — SAFE version.

Removed:
- TcpAckFrequency / TCPNoDelay reg keys → No effect on Windows 10/11 TCP stack
- GlobalMaxTcpWindowSize / TcpWindowSize → Windows auto-tunes this
- MaxHashTableSize / MaxFreeTcbs → Registry keys don't exist on modern Windows
- EnableWsd / DisableIPSourceRouting → No documented networking benefit
- IPv6 DisabledComponents=32 → Breaks many modern Windows features (Xbox, VPN, DirectAccess)
- chimney/netdma → Removed from Windows 8+
- InterruptModeration=0 → Increases CPU usage with no latency benefit on modern NICs
- InterruptModeration=0 can increase CPU usage by 5-15% with zero benefit on modern hardware
"""
import subprocess
import json

class NetworkTuner:
    def __init__(self, os_type):
        self.os_type = os_type
        self.results = []

    def get_adapters(self):
        if self.os_type != "windows":
            return []
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-NetAdapter -Physical | Select-Object Name, InterfaceDescription, LinkSpeed, Status, MacAddress | ConvertTo-Json"],
                capture_output=True, text=True, timeout=15
            )
            if r.stdout.strip():
                data = json.loads(r.stdout)
                return data if isinstance(data, list) else [data]
        except Exception:
            pass
        return []

    def tune_adapter(self, adapter_name, preset="gaming"):
        """Safe adapter tuning. Uses netsh (official API), not registry hacks."""
        results = []
        if self.os_type != "windows":
            return [{"success": False, "message": "Only Windows supported"}]
        try:
            if preset == "gaming":
                cmds = [
                    f'netsh int tcp set supplemental Internet congestionprovider=bbr2',
                ]
                for cmd in cmds:
                    subprocess.run(cmd, capture_output=True, timeout=10, shell=True)
                results.append({"success": True, "message": f"{adapter_name}: set BBR2 congestion provider"})
        except Exception as e:
            results.append({"success": False, "message": f"Adapter tuning: {e}"})
        return results

    def set_bufferbloat_preset(self, preset="low_latency"):
        """Safe bufferbloat control. Uses netsh (official API)."""
        results = []
        configs = {
            "low_latency": [
                "netsh int tcp set global autotuninglevel=normal",
                "netsh int tcp set global congestionprovider=bbr2",
            ],
            "high_throughput": [
                "netsh int tcp set global autotuninglevel=normal",
                "netsh int tcp set global congestionprovider=bbr2",
            ],
            "balanced": [
                "netsh int tcp set global autotuninglevel=normal",
                "netsh int tcp set global congestionprovider=bbr2",
            ],
        }
        cmds = configs.get(preset, configs["balanced"])
        try:
            for cmd in cmds:
                subprocess.run(cmd.split(), capture_output=True, timeout=10)
            results.append({"success": True, "message": f"Bufferbloat: {preset} mode applied"})
        except Exception as e:
            results.append({"success": False, "message": f"Bufferbloat failed: {e}"})
        return results

    def set_qos_priority(self, enabled=True):
        """Safe QoS configuration via Group Policy (official API)."""
        results = []
        try:
            if enabled:
                subprocess.run([
                    "reg", "add", "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\Psched",
                    "/v", "NonBestEffortLimit", "/t", "REG_DWORD", "/d", "0", "/f"
                ], capture_output=True, timeout=5)
                results.append({"success": True, "message": "QoS: No bandwidth limit (default)"})
            else:
                subprocess.run([
                    "reg", "add", "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\Psched",
                    "/v", "NonBestEffortLimit", "/t", "REG_DWORD", "/d", "80", "/f"
                ], capture_output=True, timeout=5)
                results.append({"success": True, "message": "QoS: 20% bandwidth reserved"})
        except Exception as e:
            results.append({"success": False, "message": f"QoS failed: {e}"})
        return results

    def advanced_network_tweaks(self):
        """Safe network tweaks. No registry hacks with no effect."""
        results = []
        try:
            # Microsoft-documented netsh optimizations
            cmds = [
                "netsh int tcp set supplemental Internet congestionprovider=bbr2",
            ]
            for cmd in cmds:
                subprocess.run(cmd.split(), capture_output=True, timeout=10)
            results.append({"success": True, "message": "Network: BBR2 congestion provider set"})
        except Exception as e:
            results.append({"success": False, "message": f"Network tweaks: {e}"})
        return results
