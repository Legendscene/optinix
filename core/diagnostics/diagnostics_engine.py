import os
import re
import json
import glob
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import psutil

from ..config import CONFIG
from ..logger import get_logger

logger = get_logger("diagnostics_engine")

_KNOWN_BUGCHECKS: Dict[str, str] = {
    "0x0000001a": "MEMORY_MANAGEMENT",
    "0x0000003b": "SYSTEM_SERVICE_EXCEPTION",
    "0x00000050": "PAGE_FAULT_IN_NONPAGED_AREA",
    "0x0000007e": "SYSTEM_THREAD_EXCEPTION_NOT_HANDLED",
    "0x0000007f": "UNEXPECTED_KERNEL_MODE_TRAP",
    "0x0000009f": "DRIVER_POWER_STATE_FAILURE",
    "0x000000d1": "DRIVER_IRQL_NOT_LESS_OR_EQUAL",
    "0x000000ea": "THREAD_STUCK_IN_DEVICE_DRIVER",
    "0x00000109": "CRITICAL_STRUCTURE_CORRUPTION",
    "0x00000113": "VIDEO_DXGKRNL_FATAL_ERROR",
    "0x00000116": "VIDEO_TDR_FAILURE",
    "0x00000133": "DPC_WATCHDOG_VIOLATION",
    "0x00000139": "KERNEL_SECURITY_CHECK_FAILURE",
    "0x00000141": "VIDEO_ENGINE_TIMEOUT_DETECTED",
    "0x00000144": "BUGCODE_USB_DRIVER",
    "0x00000154": "UNEXPECTED_STORE_EXCEPTION",
    "0x00000158": "THREAD_STUCK_IN_DEVICE_DRIVER",
    "0x00000193": "PAGE_FAULT_IN_NONPAGED_AREA",
    "0xc000021a": "STATUS_SYSTEM_PROCESS_TERMINATED",
    "0xc0000221": "STATUS_IMAGE_CHECKSUM_MISMATCH",
}

_PROBLEM_CODE_DESC: Dict[int, str] = {
    1: "Device not configured",
    3: "Driver not installed",
    10: "Device cannot start",
    12: "Out of memory/resources",
    14: "Device cannot work properly until reboot",
    18: "Reinstall drivers",
    21: "Device removed",
    22: "Device is disabled",
    24: "Device not present/not working",
    28: "Drivers not installed",
    29: "Device is disabled (firmware)",
    31: "Device not working (driver issues)",
    32: "Driver not started (service disabled)",
    33: "Driver cannot load",
    34: "Driver cannot load (too old)",
    35: "Driver conflicts with firmware",
    36: "Device requests interrupt",
    37: "Driver not properly configured",
    38: "Driver corrupted memory",
    39: "Driver corrupted memory",
    40: "Invalid information",
    41: "Must reinstall drivers",
    42: "Driver caused system lockup",
    43: "Driver reported failure",
    44: "Application or service shut down hardware",
    45: "Device not connected",
    46: "Failed to start (shutdown)",
    47: "Cannot use device (safe mode)",
    48: "Driver blocked (software restriction)",
    49: "Cannot start (memory pages)",
    50: "Device not supported (Windows 11)",
}


class DiagnosticsEngine:
    def __init__(self):
        self._previous_memory: Dict[int, float] = {}
        self.results: Dict[str, Dict] = {}

    def _run_powershell(self, command: str, timeout: int = 15) -> str:
        full_cmd = [
            "powershell", "-NoProfile", "-NonInteractive",
            "-Command", command,
        ]
        try:
            r = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
            )
            return r.stdout.strip()
        except subprocess.TimeoutExpired:
            logger.warning("PowerShell timed out (%ss): %.80s", timeout, command)
            return ""
        except FileNotFoundError:
            logger.error("PowerShell not found")
            return ""
        except Exception as e:
            logger.debug("PowerShell error: %s", e)
            return ""

    def _parse_json_output(self, output: str) -> List[Dict]:
        if not output:
            return []
        try:
            data = json.loads(output)
            if isinstance(data, list):
                return data
            return [data]
        except json.JSONDecodeError:
            return []

    def _evtx_query(
        self,
        log_name: str,
        level: Optional[int] = None,
        event_id: Optional[int] = None,
        provider: Optional[str] = None,
        max_events: int = 50,
    ) -> str:
        filter_entries = [f"LogName='{log_name}'"]
        if level is not None:
            filter_entries.append(f"Level={level}")
        if event_id is not None:
            filter_entries.append(f"Id={event_id}")
        filter_str = "@{" + ";".join(filter_entries) + "}"

        select_props = (
            "Id,LevelDisplayName,TimeCreated,"
            "ProviderName,Message"
        )

        cmd = (
            f"$e = @(Get-WinEvent -FilterHashtable {filter_str} "
            f"-MaxEvents {max_events} -ErrorAction SilentlyContinue); "
            f"if ($e.Count) {{ "
            f"$e | Select-Object {select_props} | "
            f"ConvertTo-Json -Compress "
            f"}} else {{ '[]' }}"
        )
        return self._run_powershell(cmd)

    # ── Public API ──────────────────────────────────────────────────────

    def run_all(self) -> Dict[str, Dict]:
        methods = [
            self.analyze_event_viewer,
            self.analyze_reliability,
            self.analyze_crash_dumps,
            self.analyze_bsod,
            self.analyze_driver_conflicts,
            self.analyze_memory_leaks,
            self.analyze_startup_delays,
            self.analyze_windows_errors,
        ]
        for method in methods:
            try:
                name = method.__name__
                logger.info("Running diagnostic: %s", name)
                self.results[name] = method()
            except Exception:
                logger.exception("Diagnostic %s crashed", method.__name__)
                self.results[method.__name__] = {
                    "status": "warning",
                    "summary": f"Diagnostic {method.__name__} crashed unexpectedly",
                    "details": [],
                    "issues_count": 0,
                }
        return self.results

    def get_summary(self) -> Dict[str, Any]:
        total_issues = 0
        severity: Dict[str, int] = {"good": 0, "warning": 0, "critical": 0}
        summaries: List[Dict] = []

        for name, result in self.results.items():
            s = result.get("status", "unknown")
            if s in severity:
                severity[s] += 1
            total_issues += result.get("issues_count", 0)
            summaries.append({
                "test": name,
                "status": s,
                "summary": result.get("summary", ""),
                "issues_count": result.get("issues_count", 0),
            })

        return {
            "total_issues": total_issues,
            "severity_breakdown": severity,
            "test_count": len(self.results),
            "summaries": summaries,
            "timestamp": datetime.now().isoformat(),
        }

    # ── Diagnostics ─────────────────────────────────────────────────────

    def analyze_event_viewer(self) -> Dict[str, Any]:
        system_output = self._evtx_query("System", level=2, max_events=50)
        app_output = self._evtx_query("Application", level=2, max_events=50)

        events = self._parse_json_output(system_output)
        app_events = self._parse_json_output(app_output)
        events.extend(app_events)

        sources: Dict[str, int] = {}
        details = []
        for ev in events:
            provider = ev.get("ProviderName", "Unknown")
            sources[provider] = sources.get(provider, 0) + 1
            msg = ev.get("Message", "") or ""
            details.append({
                "id": ev.get("Id"),
                "level": ev.get("LevelDisplayName"),
                "time": ev.get("TimeCreated"),
                "provider": provider,
                "message": msg[:300],
            })

        critical_count = sum(
            1 for d in details if d.get("level") == "Error"
        )

        top_sources = sorted(sources.items(), key=lambda x: -x[1])[:5]

        status = "good"
        if critical_count > 20:
            status = "critical"
        elif critical_count > 5:
            status = "warning"

        return {
            "status": status,
            "summary": (
                f"{critical_count} critical events across "
                f"{len(sources)} sources | Top: "
                + ", ".join(f"{s} ({c})" for s, c in top_sources)
            ),
            "details": details[:30],
            "issues_count": critical_count,
        }

    def analyze_reliability(self) -> Dict[str, Any]:
        output = self._evtx_query(
            "Microsoft-Windows-Diagnostics-Performance/Operational",
            max_events=30,
        )
        events = self._parse_json_output(output)

        boot_issues = 0
        shutdown_issues = 0
        slow_events = []
        details = []

        for ev in events:
            eid = ev.get("Id")
            msg = ev.get("Message", "") or ""
            details.append({
                "id": eid,
                "level": ev.get("LevelDisplayName"),
                "time": ev.get("TimeCreated"),
                "provider": ev.get("ProviderName"),
                "message": msg[:250],
            })

            if eid == 100:
                boot_issues += 1
                slow_events.append("boot")
            elif eid == 200:
                shutdown_issues += 1
                slow_events.append("shutdown")

        total_issues = boot_issues + shutdown_issues
        status = "good"
        if total_issues > 10:
            status = "critical"
        elif total_issues > 3:
            status = "warning"

        return {
            "status": status,
            "summary": (
                f"{boot_issues} boot events, {shutdown_issues} shutdown events "
                f"in the last {len(events)} performance records"
            ),
            "details": details,
            "issues_count": total_issues,
        }

    def analyze_crash_dumps(self) -> Dict[str, Any]:
        dump_dirs = [
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "CrashDumps"),
            os.path.join(os.environ.get("WINDIR", ""), "MiniDump"),
        ]

        now = datetime.now()
        seven_days_ago = now - timedelta(days=7)
        thirty_days_ago = now - timedelta(days=30)

        all_dumps: List[Dict] = []
        for d in dump_dirs:
            if not os.path.isdir(d):
                continue
            for fpath in glob.glob(os.path.join(d, "*.dmp")):
                try:
                    mtime = os.path.getmtime(fpath)
                    mdt = datetime.fromtimestamp(mtime)
                    all_dumps.append({
                        "name": os.path.basename(fpath),
                        "size": os.path.getsize(fpath),
                        "date": mdt.isoformat(),
                        "path": fpath,
                        "_mtime": mtime,
                    })
                except OSError:
                    continue

        all_dumps.sort(key=lambda x: x["_mtime"], reverse=True)

        recent_7 = sum(1 for d in all_dumps if d["_mtime"] >= seven_days_ago.timestamp())
        recent_30 = sum(1 for d in all_dumps if d["_mtime"] >= thirty_days_ago.timestamp())

        for d in all_dumps:
            d.pop("_mtime", None)

        total = len(all_dumps)
        status = "good"
        if recent_7 > 5 or recent_30 > 20:
            status = "critical"
        elif recent_7 > 1 or recent_30 > 5:
            status = "warning"

        dump_details = [
            {
                "name": d["name"],
                "size": d["size"],
                "size_mb": round(d["size"] / (1024 * 1024), 2),
                "date": d["date"],
            }
            for d in all_dumps[:15]
        ]

        return {
            "status": status,
            "summary": (
                f"{total} crash dumps found "
                f"({recent_7} in 7d, {recent_30} in 30d)"
            ),
            "details": dump_details,
            "issues_count": total,
        }

    def analyze_bsod(self) -> Dict[str, Any]:
        output = self._evtx_query("System", event_id=1001, max_events=20)
        events = self._parse_json_output(output)

        cutoff = (datetime.now() - timedelta(days=30)).isoformat()
        recent_bsods = []
        details = []

        for ev in events:
            msg = ev.get("Message", "") or ""
            match = re.search(r"(0x[0-9a-fA-F]{8})", msg)
            code = match.group(1).lower() if match else "unknown"
            display_code = match.group(1) if match else "Unknown"
            description = _KNOWN_BUGCHECKS.get(code, "Unknown bug check")

            entry = {
                "time": ev.get("TimeCreated"),
                "bug_check_code": display_code,
                "bug_check_name": description,
                "message": msg[:300],
            }
            details.append(entry)
            if ev.get("TimeCreated", "") >= cutoff:
                recent_bsods.append(entry)

        count_30d = len(recent_bsods)
        status = "good"
        if count_30d > 5:
            status = "critical"
        elif count_30d > 0:
            status = "warning"

        return {
            "status": status,
            "summary": (
                f"{count_30d} BSODs in last 30 days"
                if count_30d > 0
                else "No recent BSODs found"
            ),
            "details": details,
            "issues_count": count_30d,
        }

    def analyze_driver_conflicts(self) -> Dict[str, Any]:
        details: List[Dict] = []
        issues = 0

        # ── PnP events ──────────────────────────────────────────────
        pnp_output = self._run_powershell(
            "$e = @(Get-WinEvent -FilterHashtable "
            "@{LogName='System';ProviderName='Microsoft-Windows-Kernel-PnP'} "
            "-MaxEvents 30 -ErrorAction SilentlyContinue); "
            "if ($e.Count) { "
            "$e | Select-Object Id,LevelDisplayName,TimeCreated,Message "
            "| ConvertTo-Json -Compress } else { '[]' }"
        )
        pnp_events = self._parse_json_output(pnp_output)
        for ev in pnp_events:
            msg = ev.get("Message", "") or ""
            details.append({
                "type": "pnp_event",
                "id": ev.get("Id"),
                "level": ev.get("LevelDisplayName"),
                "time": ev.get("TimeCreated"),
                "message": msg[:250],
            })
            level = ev.get("LevelDisplayName", "")
            if level in ("Error", "Warning"):
                issues += 1

        # ── Unsigned drivers ────────────────────────────────────────
        unsig_out = self._run_powershell(
            "$d = @(Get-WmiObject -Class Win32_PnPSignedDriver "
            "-ErrorAction SilentlyContinue | "
            "Where-Object { $_.IsSigned -eq $false }); "
            "if ($d.Count) { "
            "$d | Select-Object DeviceName,DriverVersion,DriverDate "
            "| ConvertTo-Json -Compress } else { '[]' }",
            timeout=15,
        )
        unsig_drivers = self._parse_json_output(unsig_out)
        for drv in unsig_drivers:
            details.append({
                "type": "unsigned",
                "device": drv.get("DeviceName", "Unknown"),
                "version": drv.get("DriverVersion", ""),
                "date": drv.get("DriverDate", ""),
            })
            issues += 1

        # ── Problem devices ─────────────────────────────────────────
        prob_out = self._run_powershell(
            "$d = @(Get-WmiObject -Class Win32_PnPEntity "
            "-ErrorAction SilentlyContinue | "
            "Where-Object { $_.ConfigManagerErrorCode -ne 0 }); "
            "if ($d.Count) { "
            "$d | Select-Object Name,DeviceID,ConfigManagerErrorCode "
            "| ConvertTo-Json -Compress } else { '[]' }",
            timeout=15,
        )
        prob_devices = self._parse_json_output(prob_out)
        for dev in prob_devices:
            code = dev.get("ConfigManagerErrorCode", 0)
            details.append({
                "type": "problem_device",
                "device": dev.get("Name", "Unknown"),
                "device_id": dev.get("DeviceID", ""),
                "error_code": code,
                "error_description": _PROBLEM_CODE_DESC.get(code, f"Code {code}"),
            })
            issues += 1

        status = "good"
        if issues > 10:
            status = "critical"
        elif issues > 2:
            status = "warning"

        return {
            "status": status,
            "summary": (
                f"{issues} driver issues found: "
                f"{len(pnp_events)} PnP events, "
                f"{len(unsig_drivers)} unsigned, "
                f"{len(prob_devices)} problem devices"
            ),
            "details": details,
            "issues_count": issues,
        }

    def analyze_memory_leaks(self) -> Dict[str, Any]:
        details: List[Dict] = []
        high_mem_processes = 0
        very_high_mem_processes = 0

        try:
            for proc in psutil.process_iter(
                ["pid", "name", "memory_info"]
            ):
                try:
                    pid = proc.info["pid"]
                    mem_bytes = proc.info["memory_info"].rss
                    mem_mb = mem_bytes / (1024 * 1024)
                except (psutil.AccessDenied, TypeError, KeyError):
                    continue

                if mem_mb > 500:
                    name = proc.info.get("name", f"PID:{pid}")
                    prev = self._previous_memory.get(pid)
                    growth = round(mem_mb - prev, 1) if prev else 0

                    details.append({
                        "name": name,
                        "pid": pid,
                        "memory_mb": round(mem_mb, 1),
                        "growth_mb": growth,
                    })

                    if mem_mb > 1000:
                        very_high_mem_processes += 1
                    high_mem_processes += 1

                if mem_mb > 100:
                    self._previous_memory[pid] = mem_mb

        except Exception as e:
            logger.warning("psutil memory scan failed: %s", e)

        details.sort(key=lambda x: x["memory_mb"], reverse=True)
        details = details[:20]

        total_issues = very_high_mem_processes
        status = "good"
        if very_high_mem_processes > 0:
            status = "critical"
        elif high_mem_processes > 0:
            status = "warning"

        return {
            "status": status,
            "summary": (
                f"{high_mem_processes} processes >500MB "
                f"({very_high_mem_processes} >1GB)"
            ),
            "details": details,
            "issues_count": total_issues,
        }

    def analyze_startup_delays(self) -> Dict[str, Any]:
        output = self._evtx_query(
            "Microsoft-Windows-Diagnostics-Performance/Operational",
            event_id=100,
            max_events=10,
        )
        events = self._parse_json_output(output)

        details = []
        slow_count = 0
        total_boot_ms = 0

        for ev in events:
            msg = ev.get("Message", "") or ""
            boot_match = re.search(
                r"Boot Duration[:\s]+(\d+)\s*ms",
                msg,
                re.IGNORECASE,
            )
            boot_ms = int(boot_match.group(1)) if boot_match else None

            is_slow = False
            if boot_ms is not None:
                total_boot_ms += boot_ms
                is_slow = boot_ms > 30000
                if is_slow:
                    slow_count += 1

            details.append({
                "boot_time_ms": boot_ms,
                "time": ev.get("TimeCreated"),
                "is_slow": is_slow,
                "message": msg[:200],
            })

        avg_boot = (
            round(total_boot_ms / len(events), 1)
            if events else None
        )

        status = "good"
        if slow_count > 3:
            status = "critical"
        elif slow_count > 0:
            status = "warning"

        summary_parts = []
        if avg_boot is not None:
            summary_parts.append(f"avg boot {avg_boot}ms")
        summary_parts.append(f"{slow_count} slow boots (>30s)")
        if not events:
            summary_parts.append("no boot performance data available")

        return {
            "status": status,
            "summary": " | ".join(summary_parts),
            "details": details,
            "issues_count": slow_count,
        }

    def analyze_windows_errors(self) -> Dict[str, Any]:
        output = self._evtx_query("Application", level=2, max_events=50)
        events = self._parse_json_output(output)

        provider_groups: Dict[str, List[Dict]] = {}
        for ev in events:
            provider = ev.get("ProviderName", "Unknown")
            provider_groups.setdefault(provider, []).append(ev)

        details = []
        for provider, group in sorted(
            provider_groups.items(), key=lambda x: -len(x[1])
        ):
            first = group[0]
            msg = first.get("Message", "") or ""
            details.append({
                "provider": provider,
                "count": len(group),
                "latest_time": first.get("TimeCreated"),
                "message": msg[:250],
            })

        total_errors = len(events)
        status = "good"
        if total_errors > 30:
            status = "critical"
        elif total_errors > 10:
            status = "warning"

        top = details[:3]
        top_str = ", ".join(
            f"{d['provider']} ({d['count']})" for d in top
        )

        return {
            "status": status,
            "summary": (
                f"{total_errors} application errors across "
                f"{len(provider_groups)} sources | Top: {top_str}"
            ),
            "details": details,
            "issues_count": total_errors,
        }
