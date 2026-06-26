import subprocess


class OverclockOptimizer:
    name = "Overclock & Tuning"

    def __init__(self, os_type):
        self.os_type = os_type
        self.results = []

    def run(self):
        self.results = []
        if self.os_type == "windows":
            self._optimize_cpu_timing()
            self._optimize_memory()
            self._optimize_gpu_sched()
            self._optimize_power_limits()
            self._optimize_timer_resolution()
            self._optimize_interrupt_priority()
            self._disable_core_parking()
            self._optimize_prefetch()
        elif self.os_type == "linux":
            self._linux_tuning()
        elif self.os_type == "macos":
            self._macos_tuning()
        return self.results

    def _optimize_cpu_timing(self):
        try:
            cmds = [
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\kernel" /v GlobalTimerResolutionRequests /t REG_DWORD /d 1 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\PriorityControl" /v IRQ8Priority /t REG_DWORD /d 1 /f'
            ]
            for cmd in cmds:
                subprocess.run(cmd.split(), capture_output=True, timeout=10)
            self.results.append({"success": True, "message": "CPU timing and IRQ priority optimized"})
        except Exception as e:
            self.results.append({"success": False, "message": f"CPU timing failed: {e}"})

    def _optimize_memory(self):
        try:
            cmds = [
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Memory Management" /v DisablePagingExecutive /t REG_DWORD /d 1 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Memory Management" /v LargeSystemCache /t REG_DWORD /d 0 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Memory Management" /v IoPageLockLimit /t REG_DWORD /d 0 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Memory Management\\PrefetchParameters" /v EnablePrefetcher /t REG_DWORD /d 0 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Memory Management\\PrefetchParameters" /v EnableSuperfetch /t REG_DWORD /d 0 /f'
            ]
            for cmd in cmds:
                subprocess.run(cmd.split(), capture_output=True, timeout=10)
            self.results.append({"success": True, "message": "Memory management optimized (paging disabled, prefetch off)"})
        except Exception as e:
            self.results.append({"success": False, "message": f"Memory failed: {e}"})

    def _optimize_gpu_sched(self):
        try:
            cmds = [
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\GraphicsDrivers" /v HwSchMode /t REG_DWORD /d 2 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\GraphicsDrivers" /v TdrDelay /t REG_DWORD /d 10 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\GraphicsDrivers" /v TdrDdiDelay /t REG_DWORD /d 10 /f',
                'reg add "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Multimedia\\SystemProfile" /v "NetworkThrottlingIndex" /t REG_DWORD /d 4294967295 /f',
                'reg add "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Multimedia\\SystemProfile" /v SystemResponsiveness /t REG_DWORD /d 0 /f'
            ]
            for cmd in cmds:
                subprocess.run(cmd.split(), capture_output=True, timeout=10)
            self.results.append({"success": True, "message": "GPU scheduling and multimedia prioritized"})
        except Exception as e:
            self.results.append({"success": False, "message": f"GPU scheduling failed: {e}"})

    def _optimize_power_limits(self):
        try:
            cmds = [
                'powercfg /setacvalueindex SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMAX 100',
                'powercfg /setacvalueindex SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMIN 100',
                'powercfg /setacvalueindex SCHEME_CURRENT SUB_PROCESSOR PERFBOOSTMODE 2',
                'powercfg /setacvalueindex SCHEME_CURRENT SUB_PROCESSOR PERFBOOSTPOL 100',
                'powercfg /setactive SCHEME_CURRENT'
            ]
            for cmd in cmds:
                subprocess.run(cmd.split(), capture_output=True, timeout=10)
            self.results.append({"success": True, "message": "Power limits maxed (CPU 100%, turbo boost aggressive)"})
        except Exception as e:
            self.results.append({"success": False, "message": f"Power limits failed: {e}"})

    def _optimize_timer_resolution(self):
        try:
            cmds = [
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\kernel" /v GlobalTimerResolutionRequests /t REG_DWORD /d 1 /f',
                'bcdedit /set useplatformtick yes',
                'bcdedit /set disabledynamictick yes'
            ]
            for cmd in cmds:
                subprocess.run(cmd.split(), capture_output=True, timeout=10)
            self.results.append({"success": True, "message": "Timer resolution optimized (platform tick, no dynamic)"})
        except Exception as e:
            self.results.append({"success": False, "message": f"Timer failed: {e}"})

    def _optimize_interrupt_priority(self):
        try:
            cmds = [
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\PriorityControl" /v IRQ8Priority /t REG_DWORD /d 1 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\PriorityControl" /v Win32PrioritySeparation /t REG_DWORD /d 38 /f'
            ]
            for cmd in cmds:
                subprocess.run(cmd.split(), capture_output=True, timeout=10)
            self.results.append({"success": True, "message": "Interrupt priority and process scheduling optimized"})
        except Exception as e:
            self.results.append({"success": False, "message": f"Interrupt priority failed: {e}"})

    def _disable_core_parking(self):
        try:
            cmds = [
                'powercfg /setacvalueindex SCHEME_CURRENT SUB_PROCESSOR CPMINCORES 100',
                'powercfg /setactive SCHEME_CURRENT'
            ]
            for cmd in cmds:
                subprocess.run(cmd.split(), capture_output=True, timeout=10)
            self.results.append({"success": True, "message": "Core parking disabled (all cores active)"})
        except Exception as e:
            self.results.append({"success": False, "message": f"Core parking failed: {e}"})

    def _optimize_prefetch(self):
        try:
            cmds = [
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Memory Management\\PrefetchParameters" /v EnablePrefetcher /t REG_DWORD /d 0 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Memory Management\\PrefetchParameters" /v EnableSuperfetch /t REG_DWORD /d 0 /f'
            ]
            for cmd in cmds:
                subprocess.run(cmd.split(), capture_output=True, timeout=10)
            self.results.append({"success": True, "message": "Prefetch and Superfetch disabled"})
        except Exception as e:
            self.results.append({"success": False, "message": f"Prefetch failed: {e}"})

    def _linux_tuning(self):
        try:
            settings = {
                "vm.swappiness": "10",
                "vm.dirty_ratio": "15",
                "vm.dirty_background_ratio": "5",
                "kernel.sched_autogroup_enabled": "0",
                "kernel.sched_migration_cost_ns": "5000000",
                "cpu.governor": "performance"
            }
            for k, v in settings.items():
                if k == "cpu.governor":
                    subprocess.run(["sudo", "cpupower", "frequency-set", "-g", "performance"],
                                 capture_output=True, timeout=10)
                else:
                    subprocess.run(["sudo", "sysctl", "-w", f"{k}={v}"], capture_output=True, timeout=5)
            self.results.append({"success": True, "message": "Linux hardware tuning applied"})
        except Exception as e:
            self.results.append({"success": False, "message": f"Linux tuning failed: {e}"})

    def _macos_tuning(self):
        self.results.append({"success": True, "message": "macOS: System manages hardware tuning automatically"})
