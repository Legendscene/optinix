import subprocess
import platform
import json
import psutil
from typing import Dict, List, Any, Optional

class NetworkPriority:
    def __init__(self, os_type: str):
        self.os_type = os_type
        self.adapters = self._get_adapters()
    
    def _get_adapters(self) -> List[Dict[str, Any]]:
        adapters = []
        if self.os_type == "windows":
            try:
                r = subprocess.run([
                    "powershell", "-Command",
                    "Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | "
                    "Select-Object Name,InterfaceDescription,MacAddress,LinkSpeed,Status | ConvertTo-Json"
                ], capture_output=True, text=True, timeout=10)
                if r.stdout.strip():
                    data = json.loads(r.stdout)
                    if isinstance(data, dict):
                        data = [data]
                    for d in data:
                        adapters.append({
                            "name": d.get("Name", ""),
                            "description": d.get("InterfaceDescription", ""),
                            "mac": d.get("MacAddress", ""),
                            "speed": d.get("LinkSpeed", 0),
                            "status": d.get("Status", "")
                        })
            except Exception:
                pass
        
        if not adapters:
            for name, stats in psutil.net_if_stats().items():
                if stats.isup:
                    adapters.append({
                        "name": name,
                        "description": name,
                        "speed": stats.speed,
                        "status": "Up"
                    })
        
        return adapters
    
    def get_adapters(self) -> List[Dict[str, Any]]:
        return self.adapters
    
    def enable_qos(self) -> Dict[str, Any]:
        if self.os_type != "windows":
            return {"success": False, "message": "Windows only"}
        
        results = []
        
        try:
            subprocess.run([
                "reg", "add", "HKLM\\SYSTEM\\CurrentControlSet\\Services\\TCPIP\\QoS",
                "/v", "Do not use NLA", "/t", "REG_DWORD", "/d", "1", "/f"
            ], capture_output=True, timeout=5)
            results.append({"success": True, "message": "QoS enabled"})
        except Exception as e:
            results.append({"success": False, "message": f"QoS enable: {e}"})
        
        try:
            subprocess.run([
                "netsh", "int", "tcp", "set", "global", "qos=enable"
            ], capture_output=True, timeout=5)
            results.append({"success": True, "message": "TCP QoS enabled"})
        except Exception as e:
            results.append({"success": False, "message": f"TCP QoS: {e}"})
        
        return {"success": True, "results": results}
    
    def disable_qos(self) -> Dict[str, Any]:
        if self.os_type != "windows":
            return {"success": False, "message": "Windows only"}
        
        results = []
        
        try:
            subprocess.run([
                "netsh", "int", "tcp", "set", "global", "qos=disable"
            ], capture_output=True, timeout=5)
            results.append({"success": True, "message": "QoS disabled"})
        except Exception as e:
            results.append({"success": False, "message": f"QoS disable: {e}"})
        
        return {"success": True, "results": results}
    
    def prioritize_game_traffic(self, game_exe: str) -> Dict[str, Any]:
        if self.os_type != "windows":
            return {"success": False, "message": "Windows only"}
        
        results = []
        
        try:
            subprocess.run([
                "powershell", "-Command",
                f"New-NetQosPolicy -Name 'GamePriority_{game_exe}' -AppPathNameMatchCondition '{game_exe}' -PriorityValue 7 -NetworkProfile All"
            ], capture_output=True, timeout=10)
            results.append({"success": True, "message": f"QoS policy created for {game_exe}"})
        except Exception as e:
            results.append({"success": False, "message": f"QoS policy: {e}"})
        
        return {"success": True, "results": results}
    
    def remove_qos_policy(self, name: str) -> Dict[str, Any]:
        if self.os_type != "windows":
            return {"success": False, "message": "Windows only"}
        
        try:
            subprocess.run([
                "powershell", "-Command",
                f"Remove-NetQosPolicy -Name '{name}' -Confirm:$false"
            ], capture_output=True, timeout=10)
            return {"success": True, "message": f"QoS policy {name} removed"}
        except Exception as e:
            return {"success": False, "message": f"Remove QoS: {e}"}

class BufferBloatControl:
    def __init__(self, os_type: str):
        self.os_type = os_type
        self.current_preset = "balanced"
    
    def get_presets(self) -> Dict[str, Dict[str, Any]]:
        return {
            "low_latency": {
                "name": "Low Latency (Gaming)",
                "description": "Optimize for minimum ping and jitter",
                "tcp_autotuning": "disabled",
                "ecn": "disabled",
                "rsc": "disabled",
                "rss": "enabled",
                "tcp_timestamps": "disabled",
                "pacing": "enabled",
                "bbr": "enabled",
                "target": "gaming"
            },
            "high_throughput": {
                "name": "High Throughput (Downloads/Streaming)",
                "description": "Optimize for maximum bandwidth",
                "tcp_autotuning": "normal",
                "ecn": "enabled",
                "rsc": "enabled",
                "rss": "enabled",
                "tcp_timestamps": "enabled",
                "pacing": "disabled",
                "bbr": "enabled",
                "target": "throughput"
            },
            "balanced": {
                "name": "Balanced (General Use)",
                "description": "Good balance of latency and throughput",
                "tcp_autotuning": "normal",
                "ecn": "enabled",
                "rsc": "enabled",
                "rss": "enabled",
                "tcp_timestamps": "enabled",
                "pacing": "enabled",
                "bbr": "enabled",
                "target": "balanced"
            }
        }
    
    def apply_preset(self, preset: str) -> Dict[str, Any]:
        if self.os_type != "windows":
            return {"success": False, "message": "Windows only"}
        
        presets = self.get_presets()
        if preset not in presets:
            return {"success": False, "message": f"Unknown preset: {preset}"}
        
        p = presets[preset]
        results = []
        
        try:
            subprocess.run([
                "netsh", "int", "tcp", "set", "global",
                f"autotuninglevel={p['tcp_autotuning']}"
            ], capture_output=True, timeout=5)
            results.append({"success": True, "message": f"TCP autotuning: {p['tcp_autotuning']}"})
        except Exception as e:
            results.append({"success": False, "message": f"TCP autotuning: {e}"})
        
        try:
            subprocess.run([
                "netsh", "int", "tcp", "set", "global",
                f"ecncapability={p['ecn']}"
            ], capture_output=True, timeout=5)
            results.append({"success": True, "message": f"ECN: {p['ecn']}"})
        except Exception as e:
            results.append({"success": False, "message": f"ECN: {e}"})
        
        try:
            subprocess.run([
                "netsh", "int", "tcp", "set", "global",
                f"rsc={p['rsc']}"
            ], capture_output=True, timeout=5)
            results.append({"success": True, "message": f"RSC: {p['rsc']}"})
        except Exception as e:
            results.append({"success": False, "message": f"RSC: {e}"})
        
        try:
            subprocess.run([
                "netsh", "int", "tcp", "set", "global",
                f"rss={p['rss']}"
            ], capture_output=True, timeout=5)
            results.append({"success": True, "message": f"RSS: {p['rss']}"})
        except Exception as e:
            results.append({"success": False, "message": f"RSS: {e}"})
        
        try:
            subprocess.run([
                "netsh", "int", "tcp", "set", "global",
                f"timestamps={p['tcp_timestamps']}"
            ], capture_output=True, timeout=5)
            results.append({"success": True, "message": f"Timestamps: {p['tcp_timestamps']}"})
        except Exception as e:
            results.append({"success": False, "message": f"Timestamps: {e}"})
        
        self.current_preset = preset
        
        return {"success": True, "preset": preset, "results": results}
    
    def get_current_settings(self) -> Dict[str, Any]:
        if self.os_type != "windows":
            return {"success": False, "message": "Windows only"}
        
        settings = {}
        try:
            for key in ["autotuninglevel", "ecncapability", "rsc", "rss", "timestamps"]:
                r = subprocess.run([
                    "netsh", "int", "tcp", "show", "global"
                ], capture_output=True, text=True, timeout=5)
                settings[key] = r.stdout
        except Exception:
            pass
        
        return {"success": True, "settings": settings}

class AdapterTuner:
    def __init__(self, os_type: str):
        self.os_type = os_type
    
    def get_adapters(self) -> List[Dict[str, Any]]:
        adapters = []
        if self.os_type == "windows":
            try:
                r = subprocess.run([
                    "powershell", "-Command",
                    "Get-NetAdapterAdvancedProperty | "
                    "Select-Object Name,DisplayName,DisplayValue,ValidDisplayValues | ConvertTo-Json"
                ], capture_output=True, text=True, timeout=15)
                if r.stdout.strip():
                    data = json.loads(r.stdout)
                    if isinstance(data, dict):
                        data = [data]
                    for d in data:
                        adapters.append({
                            "name": d.get("Name", ""),
                            "property": d.get("DisplayName", ""),
                            "value": d.get("DisplayValue", ""),
                            "valid_values": d.get("ValidDisplayValues", "")
                        })
            except Exception:
                pass
        
        if not adapters:
            for name, stats in psutil.net_if_stats().items():
                if stats.isup:
                    adapters.append({"name": name, "speed": stats.speed})
        
        return adapters
    
    def optimize_adapter(self, adapter_name: str, preset: str = "gaming") -> Dict[str, Any]:
        if self.os_type != "windows":
            return {"success": False, "message": "Windows only"}
        
        results = []
        
        settings_map = {
            "gaming": {
                "Interrupt Moderation": "Disabled",
                "Receive Side Scaling": "Enabled",
                "Receive Segment Coalescing": "Disabled",
                "Large Send Offload": "Disabled",
                "Checksum Offload": "Enabled",
                "Jumbo Frames": "Disabled",
                "Flow Control": "Disabled",
                "Priority & VLAN": "Disabled"
            },
            "streaming": {
                "Interrupt Moderation": "Enabled",
                "Receive Side Scaling": "Enabled",
                "Receive Segment Coalescing": "Enabled",
                "Large Send Offload": "Enabled",
                "Checksum Offload": "Enabled",
                "Jumbo Frames": "9014 Bytes",
                "Flow Control": "Rx & Tx Enabled",
                "Priority & VLAN": "Enabled"
            },
            "balanced": {
                "Interrupt Moderation": "Enabled",
                "Receive Side Scaling": "Enabled",
                "Receive Segment Coalescing": "Enabled",
                "Large Send Offload": "Enabled",
                "Checksum Offload": "Enabled",
                "Jumbo Frames": "Disabled",
                "Flow Control": "Rx & Tx Enabled",
                "Priority & VLAN": "Disabled"
            }
        }
        
        settings = settings_map.get(preset, settings_map["gaming"])
        
        for setting_name, value in settings.items():
            try:
                subprocess.run([
                    "powershell", "-Command",
                    f"Set-NetAdapterAdvancedProperty -Name '{adapter_name}' -DisplayName '{setting_name}' -DisplayValue '{value}'"
                ], capture_output=True, timeout=10)
                results.append({"success": True, "message": f"{setting_name}: {value}"})
            except Exception as e:
                results.append({"success": False, "message": f"{setting_name}: {e}"})
        
        return {"success": True, "preset": preset, "results": results}
    
    def reset_adapter(self, adapter_name: str) -> Dict[str, Any]:
        if self.os_type != "windows":
            return {"success": False, "message": "Windows only"}
        
        try:
            subprocess.run([
                "powershell", "-Command",
                f"Reset-NetAdapterAdvancedProperty -Name '{adapter_name}'"
            ], capture_output=True, timeout=10)
            return {"success": True, "message": f"Adapter {adapter_name} reset to defaults"}
        except Exception as e:
            return {"success": False, "message": f"Reset adapter: {e}"}

if __name__ == "__main__":
    np = NetworkPriority("windows")
    print("Adapters:", json.dumps(np.get_adapters(), indent=2))
    
    bb = BufferBloatControl("windows")
    print("Presets:", json.dumps(bb.get_presets(), indent=2))