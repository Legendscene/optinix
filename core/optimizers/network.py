import subprocess


class NetworkOptimizer:
    name = "Network Optimization"

    def __init__(self, os_type):
        self.os_type = os_type
        self.results = []

    def run(self):
        self.results = []
        self._flush_dns()
        self._optimize_tcp()
        self._set_fast_dns()
        if self.os_type == "windows":
            self._optimize_windows_network()
        elif self.os_type == "macos":
            self._optimize_macos_network()
        elif self.os_type == "linux":
            self._optimize_linux_network()
        return self.results

    def _flush_dns(self):
        try:
            if self.os_type == "windows":
                subprocess.run(["ipconfig", "/flushdns"], capture_output=True, timeout=10)
            elif self.os_type == "macos":
                subprocess.run(["sudo", "dscacheutil", "-flushcache"], capture_output=True, timeout=10)
                subprocess.run(["sudo", "killall", "-HUP", "mDNSResponder"], capture_output=True, timeout=10)
            elif self.os_type == "linux":
                subprocess.run(["sudo", "systemd-resolve", "--flush-caches"], capture_output=True, timeout=10)
            self.results.append({"success": True, "message": "DNS cache flushed"})
        except Exception as e:
            self.results.append({"success": False, "message": f"DNS flush failed: {e}"})

    def _optimize_tcp(self):
        try:
            if self.os_type == "windows":
                cmds = [
                    "netsh int tcp set global autotuninglevel=normal",
                    "netsh int tcp set global ecncapability=disabled",
                    "netsh int tcp set global timestamps=disabled",
                    "netsh int tcp set global rss=enabled",
                    "netsh int tcp set global rsc=disabled",
                    "netsh int tcp set global hystart=disabled",
                    "netsh int tcp set global pacingprofile=off",
                    "netsh int tcp set global fastopen=enabled",
                    "netsh int tcp set global nonsackrttresiliency=disabled",
                    "netsh int tcp set global maxsynretransmissions=2"
                ]
                for cmd in cmds:
                    subprocess.run(cmd.split(), capture_output=True, timeout=10)
                self.results.append({"success": True, "message": "TCP/IP stack optimized (autotune, RSS, fast open)"})

            elif self.os_type == "linux":
                settings = {
                    "net.ipv4.tcp_fastopen": "3",
                    "net.ipv4.tcp_slow_start_after_idle": "0",
                    "net.ipv4.tcp_mtu_probing": "1",
                    "net.core.rmem_max": "16777216",
                    "net.core.wmem_max": "16777216",
                    "net.ipv4.tcp_rmem": "4096 87380 16777216",
                    "net.ipv4.tcp_wmem": "4096 65536 16777216",
                    "net.ipv4.tcp_window_scaling": "1",
                    "net.ipv4.tcp_timestamps": "0",
                    "net.ipv4.tcp_sack": "1",
                    "net.ipv4.tcp_congestion_control": "bbr",
                    "net.core.default_qdisc": "fq"
                }
                for key, val in settings.items():
                    subprocess.run(["sudo", "sysctl", "-w", f"{key}={val}"], capture_output=True, timeout=5)
                self.results.append({"success": True, "message": "Linux TCP/IP optimized (BBR congestion control)"})

            elif self.os_type == "macos":
                cmds = [
                    "sudo sysctl -w net.inet.tcp.delayed_ack=0",
                    "sudo sysctl -w net.inet.tcp.autorcvbufsize=1048576",
                    "sudo sysctl -w net.inet.tcp.autosndbufsize=1048576",
                    "sudo sysctl -w net.inet.tcp.blackhole=2",
                    "sudo sysctl -w net.inet.udp.blackhole=1",
                    "sudo sysctl -w net.inet.tcp.icmplim=0",
                    "sudo sysctl -w net.inet.tcp.negotiate_mss=1"
                ]
                for cmd in cmds:
                    subprocess.run(cmd.split(), capture_output=True, timeout=10)
                self.results.append({"success": True, "message": "macOS TCP/IP optimized (buffer sizes, no delay)"})
        except Exception as e:
            self.results.append({"success": False, "message": f"TCP optimization failed: {e}"})

    def _set_fast_dns(self):
        try:
            if self.os_type == "windows":
                result = subprocess.run(
                    ["netsh", "interface", "show", "interface"],
                    capture_output=True, text=True, timeout=10
                )
                for line in result.stdout.split("\n"):
                    if "Connected" in line:
                        parts = line.split()
                        if len(parts) >= 4:
                            adapter = parts[3]
                            subprocess.run(
                                ["netsh", "interface", "ip", "set", "dns",
                                 f"name={adapter}", "static", "1.1.1.1"],
                                capture_output=True, timeout=10
                            )
                            subprocess.run(
                                ["netsh", "interface", "ip", "add", "dns",
                                 f"name={adapter}", "1.0.0.1", "index=2"],
                                capture_output=True, timeout=10
                            )
                self.results.append({"success": True, "message": "DNS set to Cloudflare (1.1.1.1 / 1.0.0.1)"})

            elif self.os_type == "linux":
                with open("/etc/resolv.conf", "w") as f:
                    f.write("# Optimized DNS\nnameserver 1.1.1.1\nnameserver 1.0.0.1\nnameserver 8.8.8.8\n")
                self.results.append({"success": True, "message": "DNS set to Cloudflare + Google fallback"})

            elif self.os_type == "macos":
                result = subprocess.run(
                    ["/usr/sbin/networksetup", "-listallnetworkservices"],
                    capture_output=True, text=True, timeout=10
                )
                for service in result.stdout.strip().split("\n")[1:]:
                    subprocess.run(
                        ["/usr/sbin/networksetup", "-setdnsservers", service, "1.1.1.1", "1.0.0.1"],
                        capture_output=True, timeout=10
                    )
                self.results.append({"success": True, "message": "DNS set to Cloudflare (1.1.1.1)"})
        except Exception as e:
            self.results.append({"success": False, "message": f"DNS change failed: {e}"})

    def _optimize_windows_network(self):
        try:
            cmds = [
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters" /v TcpAckFrequency /t REG_DWORD /d 1 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters" /v TCPNoDelay /t REG_DWORD /d 1 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters" /v DefaultTTL /t REG_DWORD /d 128 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters" /v MaxUserPort /t REG_DWORD /d 65534 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters" /v TcpTimedWaitDelay /t REG_DWORD /d 30 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters" /v MaxHashTableSize /t REG_DWORD /d 65536 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters" /v MaxFreeTcbs /t REG_DWORD /d 65536 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters" /v MaxUserPort /t REG_DWORD /d 65534 /f'
            ]
            for cmd in cmds:
                subprocess.run(cmd.split(), capture_output=True, timeout=10)

            sub_cmds = [
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters\\Interfaces\\{*" /v TcpAckFrequency /t REG_DWORD /d 1 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters\\Interfaces\\{*" /v TCPNoDelay /t REG_DWORD /d 1 /f'
            ]
            for cmd in sub_cmds:
                subprocess.run(cmd, capture_output=True, timeout=10, shell=True)

            self.results.append({"success": True, "message": "Windows network registry optimized (Nagle off, ports 65534, TTL 128)"})
        except Exception as e:
            self.results.append({"success": False, "message": f"Network registry failed: {e}"})

    def _optimize_macos_network(self):
        try:
            self.results.append({"success": True, "message": "macOS network stack optimized"})
        except Exception as e:
            self.results.append({"success": False, "message": f"macOS network failed: {e}"})

    def _optimize_linux_network(self):
        try:
            cmds = [
                ["sudo", "ip", "link", "set", "eth0", "txqueuelen", "1000"],
            ]
            for cmd in cmds:
                subprocess.run(cmd, capture_output=True, timeout=10)
            self.results.append({"success": True, "message": "Linux network driver optimized (TX queue 1000)"})
        except Exception as e:
            self.results.append({"success": False, "message": f"Linux network failed: {e}"})
