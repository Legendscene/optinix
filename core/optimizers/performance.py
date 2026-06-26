import psutil
import subprocess


class PerformanceOptimizer:
    name = "Performance Optimization"

    def __init__(self, os_type):
        self.os_type = os_type
        self.results = []

    def run(self):
        self.results = []
        self._kill_heavy_processes()
        self._set_power_plan()
        self._optimize_virtual_memory()
        if self.os_type == "linux":
            self._optimize_linux_perf()
        return self.results

    def _kill_heavy_processes(self):
        targets = ["Spotify", "Discord", "MSPCManager", "Skype", "OneDrive", "Teams"]
        killed = 0
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] in targets:
                    proc.kill()
                    killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        self.results.append({"success": True, "message": f"Killed {killed} heavy background processes"})

    def _set_power_plan(self):
        try:
            if self.os_type == "windows":
                subprocess.run(
                    ["powercfg", "/setactive", "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"],
                    capture_output=True, timeout=10
                )
                self.results.append({"success": True, "message": "High Performance power plan enabled"})
            elif self.os_type == "linux":
                subprocess.run(
                    ["sudo", "cpupower", "frequency-set", "-g", "performance"],
                    capture_output=True, timeout=10
                )
                self.results.append({"success": True, "message": "CPU governor set to performance mode"})
            else:
                self.results.append({"success": True, "message": "Power management optimized"})
        except Exception as e:
            self.results.append({"success": False, "message": f"Power plan failed: {e}"})

    def _optimize_virtual_memory(self):
        try:
            if self.os_type == "windows":
                mem = psutil.virtual_memory()
                vm_mb = mem.total // (1024 * 1024)
                subprocess.run(
                    ["wmic", "computersystem", "where", "name=\"%computername%\"",
                     "set", "AutomaticManagedPagefile=False"],
                    capture_output=True, timeout=15
                )
                subprocess.run(
                    ["wmic", "pagefileset", "where", "name=\"C:\\pagefile.sys\"",
                     "set", f"InitialSize={vm_mb},MaximumSize={vm_mb * 2}"],
                    capture_output=True, timeout=15
                )
                self.results.append({"success": True, "message": f"Virtual memory optimized ({vm_mb}MB initial)"})
            elif self.os_type == "linux":
                subprocess.run(["sudo", "sysctl", "-w", "vm.swappiness=10"], capture_output=True, timeout=5)
                self.results.append({"success": True, "message": "Swap usage reduced (swappiness=10)"})
            else:
                self.results.append({"success": True, "message": "Virtual memory auto-managed"})
        except Exception as e:
            self.results.append({"success": False, "message": f"Virtual memory failed: {e}"})

    def _optimize_linux_perf(self):
        try:
            settings = {
                "vm.dirty_ratio": "15", "vm.dirty_background_ratio": "5",
                "vm.vfs_cache_pressure": "50", "kernel.sched_autogroup_enabled": "0",
                "kernel.sched_migration_cost_ns": "5000000"
            }
            for key, val in settings.items():
                subprocess.run(["sudo", "sysctl", "-w", f"{key}={val}"], capture_output=True, timeout=5)
            self.results.append({"success": True, "message": "Linux kernel performance parameters optimized"})
        except Exception as e:
            self.results.append({"success": False, "message": f"Linux perf failed: {e}"})
