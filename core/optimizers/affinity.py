import subprocess
import psutil


class AffinityOptimizer:
    name = "CPU Affinity & Core Management"

    def __init__(self, os_type):
        self.os_type = os_type
        self.results = []

    def run(self):
        self.results = []
        if self.os_type == "windows":
            self._disable_core_parking()
            self._optimize_cpu_priority()
            self._set_high_performance_scheme()
        return self.results

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

    def _optimize_cpu_priority(self):
        try:
            cmds = [
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\PriorityControl" /v Win32PrioritySeparation /t REG_DWORD /d 38 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\PriorityControl" /v IRQ8Priority /t REG_DWORD /d 1 /f',
            ]
            for cmd in cmds:
                subprocess.run(cmd.split(), capture_output=True, timeout=10)
            self.results.append({"success": True, "message": "CPU priority separation and IRQ priority optimized"})
        except Exception as e:
            self.results.append({"success": False, "message": f"CPU priority failed: {e}"})

    def _set_high_performance_scheme(self):
        try:
            subprocess.run(
                ['powercfg', '/setactive', '8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c'],
                capture_output=True, timeout=10
            )
            self.results.append({"success": True, "message": "High performance power scheme active"})
        except Exception:
            pass

    def set_game_affinity(self, pid, cores="performance"):
        try:
            logical = psutil.cpu_count(logical=True)
            if cores == "first_half":
                mask = (1 << (logical // 2)) - 1
            elif cores == "second_half":
                mask = ((1 << logical) - 1) ^ ((1 << (logical // 2)) - 1)
            elif cores == "all":
                mask = (1 << logical) - 1
            else:
                mask = (1 << logical) - 1
            subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"$p = Get-Process -Id {pid} -EA SilentlyContinue; "
                 f"if ($p) {{ $p.ProcessorAffinity = {mask} }}"],
                capture_output=True, timeout=10
            )
            return {"success": True, "message": f"Affinity set for PID {pid} ({cores})"}
        except Exception as e:
            return {"success": False, "message": f"Affinity failed: {e}"}
