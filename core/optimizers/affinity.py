"""AffinityOptimizer — Configures Windows CPU affinity and scheduling policies."""

import subprocess
import psutil
from core.base import OptimizerBase
from core.config import CONFIG


class AffinityOptimizer(OptimizerBase):
    name = "CPU Affinity Optimizer"
    description = "Configures Windows CPU scheduling policies for optimal process distribution and throughput"
    category = "advanced"
    benefit = "Improves CPU scheduling efficiency by configuring Windows to better distribute processes across cores and prioritize foreground performance"
    risks = "Registry changes affect global CPU scheduling. Reboot may be required for full effect."
    admin_required = True
    requirements = {}

    def run(self):
        if CONFIG.os_type == "windows":
            self._report_cpu_config()
            self._set_perf_increase_policy()
            self._set_priority_separation()
        return [r.to_dict() for r in self.results]

    def _report_cpu_config(self):
        """Inspect and report current CPU topology and affinity settings."""
        try:
            logical = psutil.cpu_count(logical=True)
            physical = psutil.cpu_count(logical=False)
            freq = psutil.cpu_freq()
            freq_str = f"{freq.current:.0f} MHz" if freq else "unknown"

            proc_info = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-CimInstance Win32_Processor).Name"],
                capture_output=True, text=True, timeout=10
            )
            cpu_name = proc_info.stdout.strip() if proc_info.returncode == 0 else "unknown"

            ps_query = subprocess.run(
                ["reg", "query", r"HKLM\SYSTEM\CurrentControlSet\Control\PriorityControl",
                 "/v", "Win32PrioritySeparation"],
                capture_output=True, text=True, timeout=5
            )
            current_wps = ps_query.stdout.strip() if ps_query.returncode == 0 else "default (not set)"

            self.add_result(
                True,
                f"CPU: {cpu_name} — {physical} physical / {logical} logical cores, {freq_str}",
                details={
                    "cpu_name": cpu_name,
                    "physical_cores": physical,
                    "logical_processors": logical,
                    "frequency_mhz": freq.current if freq else None,
                    "Win32PrioritySeparation_current": current_wps,
                }
            )
        except Exception as e:
            self.add_result(False, f"CPU config report failed: {e}")

    def _set_perf_increase_policy(self):
        """Configure Windows scheduler to aggressively distribute processes across best cores.

        Sets Processor Performance Increase Policy to 'Rocket' (2) on the active power scheme.
        This tells the scheduler to prefer the most performant cores when placing threads,
        improving distribution across available CPUs.
        """
        try:
            subprocess.run(
                ["powercfg", "-setacvalueindex", "SCHEME_CURRENT",
                 "SUB_PROCESSOR", "PERFINCPOL", "2"],
                capture_output=True, text=True, timeout=10
            )
            subprocess.run(
                ["powercfg", "-setdcvalueindex", "SCHEME_CURRENT",
                 "SUB_PROCESSOR", "PERFINCPOL", "2"],
                capture_output=True, text=True, timeout=10
            )
            apply = subprocess.run(
                ["powercfg", "-s", "SCHEME_CURRENT"],
                capture_output=True, text=True, timeout=10
            )
            if apply.returncode == 0:
                self.add_result(
                    True,
                    "Processor performance increase policy set to Rocket (aggressive core distribution)",
                    details={
                        "setting": "PERFINCPOL=2",
                        "scheme": "SCHEME_CURRENT",
                        "description": "Scheduler aggressively distributes threads across best-performing cores",
                    }
                )
            else:
                self.add_result(False, f"PERFINCPOL: powercfg apply failed ({apply.returncode})")
        except Exception as e:
            self.add_result(False, f"Processor perf policy: {e}")

    def _set_priority_separation(self):
        """Set Win32PrioritySeparation to 38 (0x26) for throughput-optimized scheduling.

        0x26 = short quantum, variable length — favors foreground responsiveness
        while maintaining good background throughput.
        """
        key = r"HKLM\SYSTEM\CurrentControlSet\Control\PriorityControl"
        try:
            query = subprocess.run(
                ["reg", "query", key, "/v", "Win32PrioritySeparation"],
                capture_output=True, text=True, timeout=5
            )
            old_val = "not set"
            if query.returncode == 0:
                for line in query.stdout.splitlines():
                    if "Win32PrioritySeparation" in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            old_val = parts[-1]

            result = subprocess.run(
                ["reg", "add", key, "/v", "Win32PrioritySeparation",
                 "/t", "REG_DWORD", "/d", "38", "/f"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                self.add_result(
                    True,
                    "Win32PrioritySeparation set to 38 (0x26): short quantum, variable length",
                    details={
                        "key": f"{key}\\Win32PrioritySeparation",
                        "old_value": old_val,
                        "new_value": "0x26 (38)",
                        "description": "Short quantum, variable length — favors throughput and foreground responsiveness",
                    }
                )
            else:
                self.add_result(False, f"Win32PrioritySeparation reg add failed ({result.returncode})")
        except Exception as e:
            self.add_result(False, f"Win32PrioritySeparation: {e}")
