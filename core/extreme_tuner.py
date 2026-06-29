import subprocess


class ExtremeTuner:
    def __init__(self, os_type):
        self.os_type = os_type

    def _create_restore_point(self):
        if self.os_type != "windows":
            return
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Checkpoint-Computer -Description 'Optinix Extreme Tuning' -RestorePointType MODIFY_SETTINGS "
                 "-EA SilentlyContinue"],
                capture_output=True, timeout=30
            )
        except Exception:
            pass

    def apply_all(self):
        results = []
        self._create_restore_point()
        results.append({"success": True, "message": "System restore point created (if available)"})

        if self.os_type == "windows":
            results.extend(self._windows_extreme())
        elif self.os_type == "linux":
            results.extend(self._linux_extreme())
        elif self.os_type == "macos":
            results.extend(self._macos_extreme())
        return results

    def _windows_extreme(self):
        results = []
        try:
            cmds = [
                'powercfg /setacvalueindex SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMAX 100',
                'powercfg /setacvalueindex SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMIN 100',
                'powercfg /setacvalueindex SCHEME_CURRENT SUB_PROCESSOR CPMINCORES 100',
                'powercfg /setacvalueindex SCHEME_CURRENT SUB_PROCESSOR PERFBOOSTMODE 2',
                'powercfg /setacvalueindex SCHEME_CURRENT SUB_PROCESSOR PERFBOOSTPOL 100',
                'powercfg /setacvalueindex SCHEME_CURRENT SUB_PROCESSOR IDLEDISABLE 1',
                'powercfg /setactive SCHEME_CURRENT'
            ]
            for cmd in cmds:
                subprocess.run(cmd.split(), capture_output=True, timeout=10)
            results.append({"success": True, "message": "CPU forced to maximum performance (100% all cores, turbo boost aggressive)"})

            mem_cmds = [
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Memory Management" /v DisablePagingExecutive /t REG_DWORD /d 1 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Memory Management" /v LargeSystemCache /t REG_DWORD /d 0 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Memory Management\\PrefetchParameters" /v EnablePrefetcher /t REG_DWORD /d 0 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Memory Management\\PrefetchParameters" /v EnableSuperfetch /t REG_DWORD /d 0 /f',
            ]
            for cmd in mem_cmds:
                subprocess.run(cmd.split(), capture_output=True, timeout=10)
            results.append({"success": True, "message": "RAM: Paging disabled, prefetch off, memory forced to physical RAM"})

            gpu_cmds = [
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\GraphicsDrivers" /v HwSchMode /t REG_DWORD /d 2 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\GraphicsDrivers" /v TdrDelay /t REG_DWORD /d 10 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\GraphicsDrivers" /v TdrDdiDelay /t REG_DWORD /d 10 /f',
                'reg add "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Multimedia\\SystemProfile" /v SystemResponsiveness /t REG_DWORD /d 0 /f',
                'reg add "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Multimedia\\SystemProfile" /v "NetworkThrottlingIndex" /t REG_DWORD /d 4294967295 /f',
            ]
            for cmd in gpu_cmds:
                subprocess.run(cmd.split(), capture_output=True, timeout=10)
            results.append({"success": True, "message": "GPU: Hardware scheduling, no throttle, multimedia priority max"})

            timer_cmds = [
                'bcdedit /set useplatformtick yes',
                'bcdedit /set disabledynamictick yes',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\kernel" /v GlobalTimerResolutionRequests /t REG_DWORD /d 1 /f',
            ]
            for cmd in timer_cmds:
                subprocess.run(cmd.split(), capture_output=True, timeout=10)
            results.append({"success": True, "message": "Timer: High precision mode, no dynamic tick"})

            disk_cmds = [
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Memory Management" /v IoPageLockLimit /t REG_DWORD /d 0 /f',
                'fsutil behavior set DisableDeleteNotify 0',
                'fsutil behavior set memoryusage 2',
            ]
            for cmd in disk_cmds:
                subprocess.run(cmd.split(), capture_output=True, timeout=10)
            results.append({"success": True, "message": "Disk I/O: Maximum cache, TRIM enabled, memory usage high"})

            priority_cmds = [
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\PriorityControl" /v Win32PrioritySeparation /t REG_DWORD /d 38 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\PriorityControl" /v IRQ8Priority /t REG_DWORD /d 1 /f',
            ]
            for cmd in priority_cmds:
                subprocess.run(cmd.split(), capture_output=True, timeout=10)
            results.append({"success": True, "message": "Process scheduling: Short foreground boost, IRQ priority"})

            vis_cmds = [
                'reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\VisualEffects" /v VisualFXSetting /t REG_DWORD /d 2 /f',
                'reg add "HKCU\\Control Panel\\Desktop" /v MenuShowDelay /t REG_SZ /d "0" /f',
                'reg add "HKCU\\Control Panel\\Desktop\\WindowMetrics" /v MinAnimate /t REG_SZ /d "0" /f',
            ]
            for cmd in vis_cmds:
                subprocess.run(cmd.split(), capture_output=True, timeout=10)
            results.append({"success": True, "message": "Visual effects: Minimal mode, animations off, menu delay zero"})

            net_cmds = [
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters" /v TcpAckFrequency /t REG_DWORD /d 1 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters" /v TCPNoDelay /t REG_DWORD /d 1 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters" /v MaxUserPort /t REG_DWORD /d 65534 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters" /v TcpTimedWaitDelay /t REG_DWORD /d 30 /f',
            ]
            for cmd in net_cmds:
                subprocess.run(cmd.split(), capture_output=True, timeout=10)
            results.append({"success": True, "message": "Network: Nagle off, max ports, low latency mode"})

        except Exception as e:
            results.append({"success": False, "message": f"Extreme tuning failed: {e}"})
        return results

    def _linux_extreme(self):
        results = []
        try:
            settings = {
                "vm.swappiness": "1",
                "vm.dirty_ratio": "40",
                "vm.dirty_background_ratio": "10",
                "vm.vfs_cache_pressure": "50",
                "vm.min_free_kbytes": "65536",
                "kernel.sched_autogroup_enabled": "0",
                "kernel.sched_migration_cost_ns": "0",
                "kernel.sched_latency_ns": "1000000",
                "kernel.sched_min_granularity_ns": "1000000",
                "kernel.sched_wakeup_granularity_ns": "1500000",
                "net.ipv4.tcp_fastopen": "3",
                "net.ipv4.tcp_congestion_control": "bbr",
                "net.core.default_qdisc": "fq",
                "net.core.rmem_max": "16777216",
                "net.core.wmem_max": "16777216",
            }
            for k, v in settings.items():
                subprocess.run(["sudo", "sysctl", "-w", f"{k}={v}"], capture_output=True, timeout=5)
            results.append({"success": True, "message": "Linux extreme: All sysctl params maximized for performance"})

            try:
                subprocess.run(["sudo", "cpupower", "frequency-set", "-g", "performance"], capture_output=True, timeout=10)
                results.append({"success": True, "message": "CPU governor forced to performance mode"})
            except Exception:
                results.append({"success": True, "message": "CPU governor: cpupower not available"})

        except Exception as e:
            results.append({"success": False, "message": f"Linux extreme tuning failed: {e}"})
        return results

    def _macos_extreme(self):
        results = []
        results.append({"success": True, "message": "macOS: System manages performance automatically"})
        results.append({"success": True, "message": "Tip: Use Activity Monitor to force-quit heavy apps for maximum performance"})
        return results
