import subprocess
import time
from typing import Dict, Any, List
from core.base import OptimizerBase


class StartupTimerOptimizer(OptimizerBase):
    name = "Boot Timer & Analysis"
    category = "safe"
    admin_required = False
    requirements = {}

    def run(self) -> List[Dict[str, Any]]:
        boot_seconds = None
        durations = []
        startup_apps = 0

        try:
            from core.system_repair import StartupTimer
            st = StartupTimer()
            data = st.get_startup_times()
            if "error" not in data:
                startup_apps = data.get("total_startup_processes", 0)
                if data.get("uptime_seconds"):
                    boot_seconds = data["uptime_seconds"]
        except Exception:
            pass

        if boot_seconds is None:
            try:
                r = subprocess.run([
                    "powershell", "-NoProfile", "-Command",
                    "(Get-CimInstance -ClassName Win32_OperatingSystem).LastBootUpTime"
                ], capture_output=True, text=True, timeout=10)
                if r.stdout.strip():
                    boot_time = r.stdout.strip()
                    boot_ts = time.mktime(time.strptime(boot_time.split(".")[0], "%Y%m%d%H%M%S"))
                    boot_seconds = int(time.time() - boot_ts)
            except Exception:
                pass

        if boot_seconds is None:
            try:
                import psutil
                boot_seconds = int(time.time() - psutil.boot_time())
            except Exception:
                pass

        try:
            r = subprocess.run([
                "powershell", "-NoProfile", "-Command",
                "Get-WinEvent -FilterHashtable @{LogName='System'; ID=100} -MaxEvents 5 "
                "| ForEach-Object { [math]::Round($_.Properties[2].Value / 1000) }"
            ], capture_output=True, text=True, timeout=15)
            for line in r.stdout.strip().splitlines():
                line = line.strip()
                if line.isdigit():
                    durations.append(int(line))
        except Exception:
            pass

        if boot_seconds is not None:
            if boot_seconds < 30:
                health = "great"
            elif boot_seconds < 60:
                health = "ok"
            else:
                health = "slow"

            avg_duration = int(sum(durations) / len(durations)) if durations else boot_seconds

            self.add_result(
                True,
                f"Last boot: {boot_seconds}s | Average (last {len(durations) or 1} boots): {avg_duration}s | Status: {health} | Startup apps: {startup_apps}",
                last_boot_seconds=boot_seconds,
                average_boot_seconds=avg_duration,
                health=health,
                startup_apps=startup_apps,
                boot_durations=durations,
            )
        else:
            self.add_result(False, "Could not determine boot time - ensure this is Windows")

        return [r.to_dict() for r in self.results]
