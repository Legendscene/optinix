import subprocess
import os
import platform
import json
import re
from typing import Dict, List, Any, Optional
from core.base import OptimizerBase, OPTIMIZER_CATEGORY_ADVANCED, OPTIMIZER_CATEGORY_SAFE
from core.config import CONFIG


_POWER_SUBGROUP_SCHEME = {
    "subsleep": "238c9fa8-0aad-41ed-83f4-97be242c8f20",
    "subvideo": "7516b95f-f776-4464-8c53-06167f40cc99",
    "subdisk": "0012ee47-9041-4b5d-9b77-535fba8b1442",
    "subprocessor": "54533251-82be-4824-96c1-47b60b740d00",
    "subusb": "2a737441-1930-4402-8d77-b2bebba308a3",
    "subpciexpress": "dea0b169-badb-4f1c-b0bd-6e1dc279a21a",
    "subsleep_n": "29f6c1db-86da-48c5-9fdb-f2b67b1f44da",
    "subhibernate": "dea0b169-badb-4f1c-b0bd-6e1dc279a21a",
    "subdisplay": "7516b95f-f776-4464-8c53-06167f40cc99",
    "subbattery": "e73a048d-bf27-4f12-9731-8b2076e8891f",
}

_SETTING_GUIDS = {
    "sleep_after_ac": "29f6c1db-86da-48c5-9fdb-f2b67b1f44da",
    "sleep_after_dc": "29f6c1db-86da-48c5-9fdb-f2b67b1f44da",
    "hibernate_timeout_ac": "9d7815a6-ee0a-4e21-9425-215121a6fb1c",
    "hibernate_timeout_dc": "9d7815a6-ee0a-4e21-9425-215121a6fb1c",
    "processor_min": "893dee8e-2bef-41e0-89c6-b55d0929964c",
    "processor_max": "bc5038f7-23e0-4960-96da-33abaf5935ec",
    "processor_throttle": "3b04d4fd-1b97-4a71-bf68-5d2bf8c0ad55",
    "usb_selective_suspend": "48e6b7a6-50f5-4782-a5d4-53bb8f07e226",
    "pcie_aspm": "ee12f906-d277-404b-b6da-e5fa1a576df5",
    "disk_timeout_ac": "6738e2c4-e8a5-42a3-b2e2-0a2e2b5a3c5d",
    "disk_timeout_dc": "6738e2c4-e8a5-42a3-b2e2-0a2e2b5a3c5d",
    "display_timeout_ac": "3c0bc021-c8a8-4e07-a973-6d1f8e0a7b5a",
    "display_timeout_dc": "3c0bc021-c8a8-4e07-a973-6d1f8e0a7b5a",
    "critical_battery_action": "8183ba9a-e910-48d2-ac03-e7d2d8f6c8e4",
    "low_battery_action": "8183ba9a-e910-48d2-ac03-e7d2d8f6c8e4",
    "lid_switch_ac": "5ca83367-6e45-459f-a27b-476b1d01c936",
    "lid_switch_dc": "5ca83367-6e45-459f-a27b-476b1d01c936",
}


def _run_powershell(script: str, timeout: int = 15) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True, text=True, timeout=timeout
    )


def _run_powercfg(args: str, timeout: int = 10) -> subprocess.CompletedProcess:
    return subprocess.run(
        f"powercfg {args}",
        capture_output=True, text=True, timeout=timeout, shell=True
    )


def _parse_powercfg_list(stdout: str) -> List[Dict[str, str]]:
    plans = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r'^Power Scheme GUID:\s*([a-fA-F0-9\-]+)\s+\((.+)\)', line)
        if m:
            plans.append({"guid": m.group(1).lower(), "name": m.group(2)})
    return plans


def _parse_powercfg_query(stdout: str) -> Dict[str, Any]:
    result = {}
    lines = stdout.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("Power Scheme GUID:"):
            m = re.match(r'Power Scheme GUID:\s*([a-fA-F0-9\-]+)\s+\((.+)\)', line)
            if m:
                result["scheme"] = {"guid": m.group(1).lower(), "name": m.group(2)}
        elif line.startswith("Subgroup GUID:"):
            m = re.match(r'Subgroup GUID:\s*([a-fA-F0-9\-]+)\s+\[(.+)\]', line)
            if m:
                sg_guid = m.group(1).lower()
                sg_name = m.group(2)
                if "settings" not in result:
                    result["settings"] = []
                j = i + 1
                while j < len(lines) and not lines[j].strip().startswith("Subgroup GUID:"):
                    sl = lines[j].strip()
                    if sl.startswith("Power Setting GUID:"):
                        sm = re.match(r'Power Setting GUID:\s*([a-fA-F0-9\-]+)\s+\[(.+)\]', sl)
                        if sm:
                            setting_item = {"subgroup": {"guid": sg_guid, "name": sg_name},
                                            "guid": sm.group(1).lower(), "name": sm.group(2),
                                            "ac": "", "dc": ""}
                            k = j + 1
                            while k < len(lines) and not lines[k].strip().startswith("Power Setting GUID:") and not lines[k].strip().startswith("Subgroup GUID:"):
                                kl = lines[k].strip()
                                if "Current AC Power Setting" in kl:
                                    mm = re.match(r'.*:\s*0x([0-9a-fA-F]+)', kl)
                                    if mm:
                                        setting_item["ac"] = str(int(mm.group(1), 16))
                                elif "Current DC Power Setting" in kl:
                                    mm = re.match(r'.*:\s*0x([0-9a-fA-F]+)', kl)
                                    if mm:
                                        setting_item["dc"] = str(int(mm.group(1), 16))
                                k += 1
                            result["settings"].append(setting_item)
                            j = k
                    else:
                        j += 1
                i = j
            else:
                i += 1
        else:
            i += 1
    return result


class PowerCenter:
    def __init__(self):
        self.os_type = CONFIG.os_type

    def _require_windows(self) -> None:
        if self.os_type != "windows":
            raise RuntimeError("PowerCenter requires Windows")

    def get_power_plans(self) -> List[Dict[str, str]]:
        self._require_windows()
        try:
            r = _run_powercfg("/list")
            if r.returncode != 0:
                return []
            return _parse_powercfg_list(r.stdout)
        except Exception:
            return []

    def get_active_power_plan(self) -> Dict[str, str]:
        self._require_windows()
        try:
            r = _run_powercfg("/getactivescheme")
            if r.returncode != 0:
                return {"guid": "", "name": "Unknown"}
            line = r.stdout.strip()
            m = re.match(r'Power Scheme GUID:\s*([a-fA-F0-9\-]+)\s+\((.+)\)', line)
            if m:
                return {"guid": m.group(1).lower(), "name": m.group(2)}
            return {"guid": "", "name": line}
        except Exception:
            return {"guid": "", "name": "Unknown"}

    def set_power_plan(self, guid: str) -> Dict[str, Any]:
        self._require_windows()
        try:
            r = _run_powercfg(f'/setactive {guid}')
            if r.returncode != 0:
                return {"success": False, "message": f"Failed to set power plan: {r.stderr.strip()}"}
            plan = self.get_active_power_plan()
            return {"success": True, "message": f"Power plan set to '{plan.get('name', guid)}'", "guid": guid}
        except subprocess.TimeoutExpired:
            return {"success": False, "message": "Timed out setting power plan"}
        except Exception as e:
            return {"success": False, "message": f"Error setting power plan: {e}"}

    def get_battery_info(self) -> Dict[str, Any]:
        self._require_windows()
        info: Dict[str, Any] = {
            "present": False, "status": "Unknown", "charge_percent": None,
            "estimated_runtime": None, "health": None, "cycles": None,
            "wear_level": None, "manufacturer": None, "chemistry": None,
            "design_capacity": None, "full_charge_capacity": None,
        }
        try:
            r = _run_powershell(
                "Get-CimInstance -ClassName Win32_Battery | "
                "Select-Object BatteryStatus, EstimatedChargeRemaining, "
                "EstimatedRunTime, Manufacturer, Chemistry, DesignCapacity, "
                "FullChargeCapacity | ConvertTo-Json"
            )
            if r.returncode == 0 and r.stdout.strip():
                data = json.loads(r.stdout)
                if isinstance(data, list):
                    data = data[0] if data else {}
                info["present"] = True
                status_map = {1: "Discharging", 2: "AC Power", 3: "Fully Charged",
                              4: "Low", 5: "Critical", 6: "Charging", 7: "Charging High",
                              8: "Charging Low", 9: "Undefined", 10: "Partially Charged"}
                bs = data.get("BatteryStatus")
                info["status"] = status_map.get(bs, f"Unknown ({bs})") if bs else "Unknown"
                info["charge_percent"] = data.get("EstimatedChargeRemaining")
                info["estimated_runtime"] = data.get("EstimatedRunTime")
                info["manufacturer"] = data.get("Manufacturer")
                info["chemistry"] = data.get("Chemistry")
                info["design_capacity"] = data.get("DesignCapacity")
                info["full_charge_capacity"] = data.get("FullChargeCapacity")
                if info["design_capacity"] and info["full_charge_capacity"]:
                    dcap = int(info["design_capacity"])
                    fcap = int(info["full_charge_capacity"])
                    if dcap > 0:
                        wear = ((dcap - fcap) / dcap) * 100
                        info["wear_level"] = round(wear, 1)
                        info["health"] = round(100 - wear, 1)
        except Exception:
            pass
        try:
            r2 = _run_powershell(
                "(Get-CimInstance -ClassName Win32_BatteryStaticData).CycleCount"
            )
            if r2.returncode == 0 and r2.stdout.strip():
                info["cycles"] = int(r2.stdout.strip())
        except Exception:
            pass
        return info

    def get_power_settings(self, plan_guid: Optional[str] = None) -> Dict[str, Any]:
        self._require_windows()
        try:
            cmd = f'/query {plan_guid}' if plan_guid else '/query'
            r = _run_powercfg(cmd)
            if r.returncode != 0:
                return {"scheme": {}, "settings": []}
            return _parse_powercfg_query(r.stdout)
        except Exception:
            return {"scheme": {}, "settings": []}

    def _set_setting_value(self, sub_guid: str, setting_guid: str, value: str, plan_guid: Optional[str] = None, acdc: str = "ac") -> Dict[str, Any]:
        self._require_windows()
        flag = "/setacvalueindex" if acdc == "ac" else "/setdcvalueindex"
        try:
            scheme = plan_guid or ""
            r = _run_powercfg(f'{flag} {scheme} {sub_guid} {setting_guid} {value}')
            if r.returncode != 0:
                return {"success": False, "message": f"Failed to set {acdc} value: {r.stderr.strip()}"}
            _run_powercfg(f'/setactive {scheme}' if scheme else '/setactive')
            return {"success": True, "message": f"Set {acdc} value for {setting_guid} to {value}"}
        except subprocess.TimeoutExpired:
            return {"success": False, "message": "Timed out setting power value"}
        except Exception as e:
            return {"success": False, "message": f"Error setting power value: {e}"}

    def set_power_setting(self, sub_guid: str, setting_guid: str, value: str, plan_guid: Optional[str] = None) -> Dict[str, Any]:
        results = []
        for acdc in ("ac", "dc"):
            res = self._set_setting_value(sub_guid, setting_guid, value, plan_guid, acdc)
            results.append(res)
        all_ok = all(r["success"] for r in results)
        return {"success": all_ok, "message": f"Set {setting_guid} to {value}",
                "results": results}

    def create_high_performance_plan(self) -> Dict[str, Any]:
        self._require_windows()
        try:
            r = _run_powercfg("/duplicatescheme 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c")
            if r.returncode != 0:
                return {"success": False, "message": f"Failed to create plan: {r.stderr.strip()}"}
            plans_before = {p["name"] for p in self.get_power_plans()}
            plans_after = self.get_power_plans()
            new_plans = [p for p in plans_after if p["name"] not in plans_before]
            if new_plans:
                guid = new_plans[0]["guid"]
                rename = _run_powercfg(f'/changename {guid} "Optinix High Performance"')
                return {"success": True, "message": "Created Optinix High Performance plan",
                        "guid": guid, "rename_ok": rename.returncode == 0}
            return {"success": False, "message": "Could not detect newly created plan"}
        except subprocess.TimeoutExpired:
            return {"success": False, "message": "Timed out creating plan"}
        except Exception as e:
            return {"success": False, "message": f"Error creating plan: {e}"}

    def set_sleep_settings(self, minutes_ac: int, minutes_dc: int) -> Dict[str, Any]:
        self._require_windows()
        results = []
        sg = _POWER_SUBGROUP_SCHEME["subsleep"]
        sg_standby = _POWER_SUBGROUP_SCHEME["subsleep_n"]
        sg_hibernate = _POWER_SUBGROUP_SCHEME["subhibernate"]
        sg_disk = _POWER_SUBGROUP_SCHEME["subdisk"]
        try:
            for acdc, minutes in [("ac", minutes_ac), ("dc", minutes_dc)]:
                flag = "/setacvalueindex" if acdc == "ac" else "/setdcvalueindex"
                if minutes <= 0:
                    r = _run_powercfg(f'{flag} {sg_standby} 29f6c1db-86da-48c5-9fdb-f2b67b1f44da 0')
                else:
                    r = _run_powercfg(f'{flag} {sg_standby} 29f6c1db-86da-48c5-9fdb-f2b67b1f44da {minutes}')
                results.append({"acdc": acdc, "ok": r.returncode == 0, "setting": "sleep_after"})
                r2 = _run_powercfg(f'{flag} {sg_disk} 6738e2c4-e8a5-42a3-b2e2-0a2e2b5a3c5d {minutes * 2}')
                results.append({"acdc": acdc, "ok": r2.returncode == 0, "setting": "disk_timeout"})
            _run_powercfg("/setactive")
            return {"success": True, "message": f"Sleep set to {minutes_ac}m AC / {minutes_dc}m DC",
                    "results": results}
        except Exception as e:
            return {"success": False, "message": f"Error setting sleep: {e}"}

    def set_hibernate(self, enable: bool) -> Dict[str, Any]:
        self._require_windows()
        try:
            cmd = "powercfg /hibernate on" if enable else "powercfg /hibernate off"
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=10, shell=True)
            if r.returncode != 0:
                return {"success": False, "message": f"Failed to {'enable' if enable else 'disable'} hibernate: {r.stderr.strip()}"}
            if not enable:
                subprocess.run("powercfg /h /type reduced", capture_output=True, text=True, timeout=10, shell=True)
            return {"success": True, "message": f"Hibernate {'enabled' if enable else 'disabled'}"}
        except subprocess.TimeoutExpired:
            return {"success": False, "message": "Timed out"}
        except Exception as e:
            return {"success": False, "message": f"Error setting hibernate: {e}"}

    def set_processor_power_management(self, min_percent: int, max_percent: int) -> Dict[str, Any]:
        self._require_windows()
        sg = _POWER_SUBGROUP_SCHEME["subprocessor"]
        min_guid = _SETTING_GUIDS["processor_min"]
        max_guid = _SETTING_GUIDS["processor_max"]
        results = []
        for acdc in ("ac", "dc"):
            r1 = self._set_setting_value(sg, min_guid, str(min_percent), None, acdc)
            results.append(r1)
            r2 = self._set_setting_value(sg, max_guid, str(max_percent), None, acdc)
            results.append(r2)
        all_ok = all(r["success"] for r in results)
        return {"success": all_ok, "message": f"Processor {min_percent}%-{max_percent}%",
                "results": results}

    def set_usb_selective_suspend(self, enable: bool) -> Dict[str, Any]:
        self._require_windows()
        sg = _POWER_SUBGROUP_SCHEME["subusb"]
        guid = _SETTING_GUIDS["usb_selective_suspend"]
        value = "0" if enable else "1"
        return self.set_power_setting(sg, guid, value)

    def set_pcie_link_state(self, state: str) -> Dict[str, Any]:
        self._require_windows()
        sg = _POWER_SUBGROUP_SCHEME["subpciexpress"]
        guid = _SETTING_GUIDS["pcie_aspm"]
        state_map = {"off": "0", "moderate": "1", "maximum": "2"}
        value = state_map.get(state.lower(), "0")
        return self.set_power_setting(sg, guid, value)

    def reset_plan_to_default(self, guid: str) -> Dict[str, Any]:
        self._require_windows()
        try:
            r = _run_powercfg(f'/restoredefaultscheme {guid}')
            if r.returncode != 0:
                return {"success": False, "message": f"Failed to reset plan: {r.stderr.strip()}"}
            return {"success": True, "message": f"Plan {guid} reset to defaults"}
        except subprocess.TimeoutExpired:
            return {"success": False, "message": "Timed out resetting plan"}
        except Exception as e:
            return {"success": False, "message": f"Error resetting plan: {e}"}


class BatteryOptimizer(OptimizerBase):
    name = "Battery Optimizer"
    description = "Optimizes power settings for battery life"
    category = OPTIMIZER_CATEGORY_SAFE
    benefit = "Extends battery life on laptops"
    risks = "May reduce performance on battery"
    admin_required = True
    requirements = {"laptop_only": True}

    def run(self) -> List[Dict[str, Any]]:
        pc = PowerCenter()
        battery = pc.get_battery_info()
        if not battery.get("present"):
            self.add_result(False, "No battery detected")
            return [r.to_dict() for r in self.results]
        self.add_result(True, "Battery detected", battery=battery)
        sleep_res = pc.set_sleep_settings(15, 10)
        self.add_result(sleep_res["success"], sleep_res["message"])
        proc_res = pc.set_processor_power_management(5, 100)
        self.add_result(proc_res["success"], proc_res["message"])
        usb_res = pc.set_usb_selective_suspend(True)
        self.add_result(usb_res["success"], usb_res["message"])
        pcie_res = pc.set_pcie_link_state("moderate")
        self.add_result(pcie_res["success"], pcie_res["message"])
        hibernate_res = pc.set_hibernate(True)
        self.add_result(hibernate_res["success"], hibernate_res["message"])
        return [r.to_dict() for r in self.results]


class PowerPlanOptimizer(OptimizerBase):
    name = "Power Plan Optimizer"
    description = "Creates and applies optimized power plans"
    category = OPTIMIZER_CATEGORY_ADVANCED
    benefit = "Balanced performance and power efficiency"
    risks = "May change system behavior"
    admin_required = True

    def run(self) -> List[Dict[str, Any]]:
        pc = PowerCenter()
        existing = pc.get_active_power_plan()
        self.add_result(True, f"Current plan: {existing.get('name')}", current=existing)
        create_res = pc.create_high_performance_plan()
        self.add_result(create_res["success"], create_res["message"])
        if create_res.get("success"):
            guid = create_res.get("guid")
            pc.set_processor_power_management(100, 100)
            pc.set_sleep_settings(60, 30)
            pc.set_usb_selective_suspend(False)
            pc.set_pcie_link_state("off")
            self.add_result(True, "Applied performance tuning to new plan")
            apply_res = pc.set_power_plan(guid)
            self.add_result(apply_res["success"], apply_res["message"])
        return [r.to_dict() for r in self.results]
