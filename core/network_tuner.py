import subprocess
import re


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
                 "Get-NetAdapter -Physical | Select-Object Name, InterfaceDescription, LinkSpeed, Status, MacAddress, DriverInformation | ConvertTo-Json"],
                capture_output=True, text=True, timeout=15
            )
            import json
            if r.stdout.strip():
                data = json.loads(r.stdout)
                if isinstance(data, dict):
                    data = [data]
                return data
        except Exception:
            pass
        return []

    def tune_adapter(self, adapter_name, preset="gaming"):
        results = []
        if self.os_type != "windows":
            return [{"success": False, "message": "Only Windows supported"}]

        try:
            if preset == "gaming":
                cmds = [
                    f'netsh int ip set interface "{adapter_name}" weakhostreceive=enabled',
                    f'netsh int ip set interface "{adapter_name}" weakhostsend=enabled',
                    f'netsh int tcp set supplemental Internet congestionprovider=bbr2',
                ]
                for cmd in cmds:
                    subprocess.run(cmd, capture_output=True, timeout=10, shell=True)
                results.append({"success": True, "message": f"{adapter_name}: Gaming preset applied (weak host, BBR2)"})
        except Exception as e:
            results.append({"success": False, "message": f"Adapter tuning failed: {e}"})

        try:
            int_name = adapter_name.replace(" ", "")
            reg_path = f"HKLM\\SYSTEM\\CurrentControlSet\\Control\\Class\\{{4d36e972-e325-11ce-bfc1-08002be10318}}"
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"Get-ChildItem 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Class\\{{4d36e972-e325-11ce-bfc1-08002be10318}}' | "
                 f"ForEach-Object {{ $path = $_.PSPath; $name = (Get-ItemProperty $path -Name DriverDesc -EA 0).DriverDesc; "
                 f"if ($name -eq '{adapter_name}') {{ Write-Output $_.PSChildName }} }}"],
                capture_output=True, text=True, timeout=10
            )
            subkey = r.stdout.strip()
        except Exception:
            subkey = ""

        try:
            adv_paths = [
                f"HKLM\\SYSTEM\\CurrentControlSet\\Control\\Class\\{{4d36e972-e325-11ce-bfc1-08002be10318}}\\{subkey}",
            ]
            for path in adv_paths:
                if subkey:
                    offload_cmds = [
                        f'reg add "{path}" /v *PriorityVLANeg /t REG_SZ /d "0" /f',
                        f'reg add "{path}" /v *IPChecksumOffloadIPv4 /t REG_SZ /d "3" /f',
                        f'reg add "{path}" /v *TCPChecksumOffloadIPv4 /t REG_SZ /d "3" /f',
                        f'reg add "{path}" /v *TCPChecksumOffloadIPv6 /t REG_SZ /d "3" /f',
                        f'reg add "{path}" /v *UDPChecksumOffloadIPv4 /t REG_SZ /d "3" /f',
                        f'reg add "{path}" /v *UDPChecksumOffloadIPv6 /t REG_SZ /d "3" /f',
                        f'reg add "{path}" /v *LsoV2IPv4 /t REG_SZ /d "1" /f',
                        f'reg add "{path}" /v *LsoV2IPv6 /t REG_SZ /d "1" /f',
                        f'reg add "{path}" /v *RSS /t REG_SZ /d "1" /f',
                        f'reg add "{path}" /v *NumRssQueues /t REG_SZ /d "2" /f',
                        f'reg add "{path}" /v *RssProfile /t REG_DWORD /d 3 /f',
                        f'reg add "{path}" /v *InterruptModeration /t REG_SZ /d "0" /f',
                        f'reg add "{path}" /v *PacketCoalescing /t REG_SZ /d "0" /f',
                    ]
                    for cmd in offload_cmds:
                        subprocess.run(cmd, capture_output=True, timeout=10, shell=True)
                    results.append({"success": True, "message": f"{adapter_name}: Offload/RSS/coalescing optimized"})
        except Exception:
            pass

        return results

    def set_bufferbloat_preset(self, preset="low_latency"):
        results = []
        if preset == "low_latency":
            cmds = [
                "netsh int tcp set global autotuninglevel=disabled",
                "netsh int tcp set global congestionprovider=bbr2",
                "netsh int tcp set global ecncapability=disabled",
                "netsh int tcp set global timestamps=disabled",
                "netsh int tcp set global nonsackrttresiliency=disabled",
                "netsh int tcp set global maxsynretransmissions=2",
                "netsh int tcp set global rsc=disabled",
                "netsh int ip set global icmpredirect=disabled",
            ]
            try:
                for cmd in cmds:
                    subprocess.run(cmd.split(), capture_output=True, timeout=10)
                results.append({"success": True, "message": "Bufferbloat: Low Latency mode (auto-tune off, BBR2)"})
            except Exception as e:
                results.append({"success": False, "message": f"Bufferbloat preset failed: {e}"})

        elif preset == "high_throughput":
            cmds = [
                "netsh int tcp set global autotuninglevel=normal",
                "netsh int tcp set global congestionprovider=bbr2",
                "netsh int tcp set global ecncapability=disabled",
                "netsh int tcp set global timestamps=enabled",
                "netsh int tcp set global nonsackrttresiliency=disabled",
                "netsh int tcp set global rsc=enabled",
            ]
            try:
                for cmd in cmds:
                    subprocess.run(cmd.split(), capture_output=True, timeout=10)
                results.append({"success": True, "message": "Bufferbloat: High Throughput mode (auto-tune on, RSC on)"})
            except Exception as e:
                results.append({"success": False, "message": f"Bufferbloat preset failed: {e}"})

        elif preset == "balanced":
            cmds = [
                "netsh int tcp set global autotuninglevel=normal",
                "netsh int tcp set global congestionprovider=bbr2",
                "netsh int tcp set global ecncapability=disabled",
                "netsh int tcp set global timestamps=disabled",
                "netsh int tcp set global rsc=disabled",
            ]
            try:
                for cmd in cmds:
                    subprocess.run(cmd.split(), capture_output=True, timeout=10)
                results.append({"success": True, "message": "Bufferbloat: Balanced mode"})
            except Exception as e:
                results.append({"success": False, "message": f"Bufferbloat preset failed: {e}"})

        return results

    def set_qos_priority(self, enabled=True):
        results = []
        try:
            if enabled:
                cmds = [
                    'reg add "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\Psched" /v NonBestEffortLimit /t REG_DWORD /d 0 /f',
                    'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Psched" /v Start /t REG_DWORD /d 1 /f',
                ]
                msg = "QoS: Network priority enabled (no limit)"
            else:
                cmds = [
                    'reg add "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\Psched" /v NonBestEffortLimit /t REG_DWORD /d 100 /f',
                ]
                msg = "QoS: Default limits restored"
            for cmd in cmds:
                subprocess.run(cmd, capture_output=True, timeout=10, shell=True)
            results.append({"success": True, "message": msg})
        except Exception as e:
            results.append({"success": False, "message": f"QoS failed: {e}"})
        return results

    def advanced_network_tweaks(self):
        results = []
        try:
            cmds = [
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters" /v TcpAckFrequency /t REG_DWORD /d 1 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters" /v TCPNoDelay /t REG_DWORD /d 1 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters" /v DefaultTTL /t REG_DWORD /d 64 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters" /v MaxUserPort /t REG_DWORD /d 65534 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters" /v TcpTimedWaitDelay /t REG_DWORD /d 30 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters" /v MaxHashTableSize /t REG_DWORD /d 65536 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters" /v MaxFreeTcbs /t REG_DWORD /d 65536 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters" /v TcpMaxDupAcks /t REG_DWORD /d 2 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters" /v SackOpts /t REG_DWORD /d 1 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters" /v EnableWsd /t REG_DWORD /d 0 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters" /v EnableICMPRedirect /t REG_DWORD /d 0 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters" /v DisableIPSourceRouting /t REG_DWORD /d 2 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters" /v GlobalMaxTcpWindowSize /t REG_DWORD /d 65536 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters" /v TcpWindowSize /t REG_DWORD /d 65536 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters\\Interfaces" /v TCPNoDelay /t REG_DWORD /d 1 /f',
            ]
            for cmd in cmds:
                subprocess.run(cmd, capture_output=True, timeout=10, shell=True)

            netsh_cmds = [
                "netsh int tcp set supplemental Internet congestionprovider=bbr2",
                "netsh int tcp set global chimney=disabled",
                "netsh int tcp set global netdma=disabled",
            ]
            for cmd in netsh_cmds:
                subprocess.run(cmd.split(), capture_output=True, timeout=10)

            results.append({"success": True, "message": "Advanced network: TCP window, SACK, WSD, ICMP redirect, BBR2 configured"})
        except Exception as e:
            results.append({"success": False, "message": f"Advanced network tweaks failed: {e}"})

        try:
            disable_ipv6_cmds = [
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip6\\Parameters" /v DisabledComponents /t REG_DWORD /d 32 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\TCPIP6" /v Start /t REG_DWORD /d 4 /f',
            ]
            for cmd in disable_ipv6_cmds:
                subprocess.run(cmd, capture_output=True, timeout=10, shell=True)
            results.append({"success": True, "message": "IPv6 transition services disabled (IPv4 preferred)"})
        except Exception:
            pass

        return results
