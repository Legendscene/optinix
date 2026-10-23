import os
import re
import json
import subprocess
import psutil
import platform
from datetime import datetime
from typing import Dict, List, Optional, Any
from ..config import CONFIG
from ..logger import get_logger
from ..hardware_detection import HardwareDetector
from ..scanner import SystemScanner

logger = get_logger(__name__)
_CREATE_NO_WINDOW = 0x08000000


def _run_pwsh(script: str, timeout: int = 15) -> str:
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True, text=True, timeout=timeout,
            creationflags=_CREATE_NO_WINDOW
        )
        return r.stdout.strip() if r.returncode == 0 else ""
    except subprocess.TimeoutExpired:
        logger.warning(f"PowerShell command timed out after {timeout}s")
        return ""
    except Exception as e:
        logger.debug(f"PowerShell command failed: {e}")
        return ""


def _parse_json(raw: str):
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _ensure_list(data):
    if data is None:
        return []
    if isinstance(data, list):
        return data
    return [data]


def _parse_int(val, default=0):
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def _parse_float(val, default=0.0):
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _format_bytes(val: int) -> str:
    if val >= 1073741824:
        return f"{val / 1073741824:.1f} GB"
    if val >= 1048576:
        return f"{val / 1048576:.1f} MB"
    if val >= 1024:
        return f"{val / 1024:.1f} KB"
    return f"{val} B"


def _format_size_gb(val: int) -> float:
    return round(val / (1024 ** 3), 1)


def _format_date(val: str) -> str:
    if not val:
        return ""
    val = val.strip()
    for fmt in ["%Y%m%d", "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"]:
        try:
            return datetime.strptime(val[:10].replace("-", ""), fmt.replace("-", "")).strftime("%Y-%m-%d")
        except (ValueError, IndexError):
            continue
    return val[:10] if len(val) >= 10 else val


class DeviceInfoProvider:
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._cache_time: Dict[str, datetime] = {}
        self._cache_ttl: int = 60
        self._detector = HardwareDetector()
        self._scanner = SystemScanner(CONFIG.os_type)

    def _cached(self, key: str, ttl: Optional[int] = None) -> bool:
        if key in self._cache and key in self._cache_time:
            age = (datetime.now() - self._cache_time[key]).total_seconds()
            if age < (ttl or self._cache_ttl):
                return True
        return False

    def _get(self, key: str):
        return self._cache.get(key)

    def _set(self, key: str, value: Any) -> Any:
        self._cache[key] = value
        self._cache_time[key] = datetime.now()
        return value

    def get_cpu_info(self) -> Dict:
        key = "cpu"
        if self._cached(key):
            return self._get(key)

        result: Dict[str, Any] = {
            "name": "Unknown",
            "architecture": platform.machine() or "Unknown",
            "cores_physical": psutil.cpu_count(logical=False) or 1,
            "cores_logical": psutil.cpu_count(logical=True) or 1,
            "base_clock_ghz": 0.0,
            "max_clock_ghz": 0.0,
            "current_clock_ghz": 0.0,
            "cache_l1": "Unknown",
            "cache_l2": "Unknown",
            "cache_l3": "Unknown",
            "socket": "Unknown",
            "manufacturer": "Unknown",
            "temperature_c": None,
            "load_percent": 0,
            "features": [],
            "virtualization": False,
            "driver_provider": "Unknown",
            "driver_version": "Unknown",
            "uptime_days": 0.0,
        }

        data = _parse_json(_run_pwsh(
            "Get-CimInstance -ClassName Win32_Processor | "
            "Select-Object Name,MaxClockSpeed,CurrentClockSpeed,L2CacheSize,"
            "L3CacheSize,SocketDesignation,Manufacturer,NumberOfCores,"
            "NumberOfLogicalProcessors,VirtualizationFirmwareEnabled | "
            "ConvertTo-Json -Compress"
        ))
        proc = data[0] if isinstance(data, list) and data else (data or {})
        if isinstance(proc, dict):
            result["name"] = proc.get("Name") or result["name"]
            max_clk = _parse_int(proc.get("MaxClockSpeed"))
            if max_clk:
                result["max_clock_ghz"] = round(max_clk / 1000, 2)
            cur_clk = _parse_int(proc.get("CurrentClockSpeed"))
            if cur_clk:
                result["current_clock_ghz"] = round(cur_clk / 1000, 2)
            l2 = _parse_int(proc.get("L2CacheSize"))
            if l2:
                result["cache_l2"] = f"{l2 // 1024} MB" if l2 >= 1024 else f"{l2} KB"
            l3 = _parse_int(proc.get("L3CacheSize"))
            if l3:
                result["cache_l3"] = f"{l3 // 1024} MB" if l3 >= 1024 else f"{l3} KB"
            result["socket"] = proc.get("SocketDesignation") or result["socket"]
            result["manufacturer"] = proc.get("Manufacturer") or result["manufacturer"]
            result["cores_physical"] = _parse_int(proc.get("NumberOfCores"), result["cores_physical"])
            result["cores_logical"] = _parse_int(proc.get("NumberOfLogicalProcessors"), result["cores_logical"])
            vfe = proc.get("VirtualizationFirmwareEnabled")
            if vfe is not None:
                result["virtualization"] = bool(vfe)

        try:
            freq = psutil.cpu_freq()
            if freq:
                if freq.min:
                    result["base_clock_ghz"] = round(freq.min / 1000, 2)
                if freq.max:
                    result["max_clock_ghz"] = round(freq.max / 1000, 2)
                if freq.current:
                    result["current_clock_ghz"] = round(freq.current / 1000, 2)
        except Exception:
            pass

        try:
            result["load_percent"] = psutil.cpu_percent(interval=None)
        except Exception:
            pass

        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for entries in temps.values():
                    if entries:
                        result["temperature_c"] = entries[0].current
                        break
        except Exception:
            pass

        l1_data = _parse_json(_run_pwsh(
            "Get-CimInstance -ClassName Win32_CacheMemory | "
            "Where-Object { $_.CacheType -eq 3 } | "
            "Select-Object -First 1 -Property MaxCacheSize | ConvertTo-Json -Compress"
        ))
        l1_obj = l1_data if isinstance(l1_data, dict) else None
        if l1_obj:
            l1_sz = _parse_int(l1_obj.get("MaxCacheSize"))
            if l1_sz:
                result["cache_l1"] = f"{l1_sz // 1024} MB" if l1_sz >= 1024 else f"{l1_sz} KB"

        result["features"] = self._detect_cpu_features()

        drv_data = _parse_json(_run_pwsh(
            "Get-CimInstance -ClassName Win32_PnPSignedDriver | "
            "Where-Object { $_.DeviceName -like '*Intel*' -or "
            "$_.DeviceName -like '*AMD*' -or "
            "$_.DeviceName -like '*Processor*' } | "
            "Select-Object -First 1 DeviceName,DriverProviderName,"
            "DriverVersion | ConvertTo-Json -Compress"
        ))
        drv = drv_data if isinstance(drv_data, dict) else None
        if drv:
            result["driver_provider"] = drv.get("DriverProviderName") or result["driver_provider"]
            result["driver_version"] = drv.get("DriverVersion") or result["driver_version"]

        try:
            bt = psutil.boot_time()
            result["uptime_days"] = round((datetime.now() - datetime.fromtimestamp(bt)).total_seconds() / 86400, 1)
        except Exception:
            pass

        return self._set(key, result)

    def _detect_cpu_features(self) -> List[str]:
        features = []
        try:
            output = _run_pwsh(
                "$a=Get-CimInstance Win32_Processor | Select-Object -ExpandProperty Caption; "
                "if($a -match '(\d+)'){ $matches[1] }"
            )
        except Exception:
            output = ""
        machine = platform.machine()
        if "64" in machine:
            features.extend(["SSE4.1", "SSE4.2", "AVX2", "VT-x"])
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "$p=(Get-ItemProperty "
                 "'HKLM:\\HARDWARE\\DESCRIPTION\\System\\CentralProcessor\\0' "
                 "-EA SilentlyContinue); "
                 "if($p){ $p.Flags -join ',' }"],
                capture_output=True, text=True, timeout=5,
                creationflags=_CREATE_NO_WINDOW
            )
            flags_str = r.stdout.strip()
            if flags_str:
                flags = set(f.strip() for f in flags_str.split(",") if f.strip())
                flag_map = {
                    "SSE3": "SSE3", "SSSE3": "SSSE3",
                    "SSE4_1": "SSE4.1", "SSE4_2": "SSE4.2",
                    "AVX": "AVX", "AVX2": "AVX2",
                    "AVX512": "AVX-512", "FMA": "FMA3",
                    "AES": "AES-NI", "SHA": "SHA",
                    "VTX": "VT-x", "AMD_V": "AMD-V",
                }
                for flag in flags:
                    mapped = flag_map.get(flag.upper())
                    if mapped and mapped not in features:
                        features.append(mapped)
        except Exception:
            pass
        return list(dict.fromkeys(features))

    def get_gpu_info(self) -> Dict:
        key = "gpu"
        if self._cached(key):
            return self._get(key)

        result: Dict[str, Any] = {
            "name": "Unknown",
            "manufacturer": "Unknown",
            "memory_total_mb": 0,
            "memory_used_mb": 0,
            "core_clock_mhz": 0,
            "memory_clock_mhz": 0,
            "driver_version": "Unknown",
            "driver_date": "Unknown",
            "temperature_c": None,
            "load_percent": 0,
            "is_dedicated": True,
            "adapter_ram": 0,
            "resolution": "Unknown",
            "refresh_rate": 0,
            "directx_support": "Unknown",
            "vulkan_support": False,
            "video_memory_type": "Unknown",
        }

        data = _parse_json(_run_pwsh(
            "Get-CimInstance -ClassName Win32_VideoController | "
            "Select-Object Name,AdapterCompatibility,AdapterRAM,"
            "DriverVersion,DriverDate,CurrentHorizontalResolution,"
            "CurrentVerticalResolution,CurrentRefreshRate,"
            "VideoMemoryType,VideoModeDescription | "
            "ConvertTo-Json -Compress"
        ))
        gpus = _ensure_list(data)
        if gpus:
            gpu = gpus[0]
            result["name"] = gpu.get("Name") or result["name"]
            result["manufacturer"] = gpu.get("AdapterCompatibility") or result["manufacturer"]
            ram = _parse_int(gpu.get("AdapterRAM"))
            if ram:
                result["adapter_ram"] = ram
                result["memory_total_mb"] = ram // (1024 * 1024)
            drv_date = gpu.get("DriverDate") or ""
            result["driver_date"] = _format_date(drv_date.split(".")[0] if "." in drv_date else drv_date)
            result["driver_version"] = gpu.get("DriverVersion") or result["driver_version"]
            h_res = _parse_int(gpu.get("CurrentHorizontalResolution"))
            v_res = _parse_int(gpu.get("CurrentVerticalResolution"))
            if h_res and v_res:
                result["resolution"] = f"{h_res}x{v_res}"
            refr = _parse_int(gpu.get("CurrentRefreshRate"))
            if refr:
                result["refresh_rate"] = refr
            vmt = _parse_int(gpu.get("VideoMemoryType"))
            mem_types = {1: "Other", 2: "VRAM", 3: "DRAM", 4: "SRAM",
                         5: "WRAM", 6: "EDO RAM", 7: "Burst Synchronous DRAM",
                         8: "Pipelined Burst SRAM", 9: "CDRAM", 10: "3DRAM",
                         11: "SDRAM", 12: "SGRAM", 13: "WRAM",
                         14: "HBM", 15: "HBM2", 16: "DDR", 17: "DDR2",
                         18: "DDR3", 19: "DDR4", 20: "DDR5",
                         21: "GDDR4", 22: "GDDR5", 23: "GDDR5X",
                         24: "GDDR6", 25: "GDDR6X"}
            result["video_memory_type"] = mem_types.get(vmt, "Unknown")
            desc = (gpu.get("VideoModeDescription") or "").upper()
            if "VULKAN" in desc:
                result["vulkan_support"] = True
            result["directx_support"] = self._detect_directx_version()

        try:
            r = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,"
                 "temperature.gpu,clocks.current.graphics,clocks.current.memory",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=3,
                creationflags=_CREATE_NO_WINDOW
            )
            if r.returncode == 0 and r.stdout.strip():
                parts = [p.strip() for p in r.stdout.split(", ")]
                if len(parts) >= 5:
                    result["load_percent"] = _parse_int(parts[0])
                    result["memory_used_mb"] = _parse_int(parts[1])
                    tc = _parse_int(parts[2])
                    if tc:
                        result["temperature_c"] = tc
                    result["core_clock_mhz"] = _parse_int(parts[3])
                    result["memory_clock_mhz"] = _parse_int(parts[4])
                result["is_dedicated"] = True
        except Exception:
            try:
                r = subprocess.run(
                    ["nvidia-smi", "--query-gpu=name,driver_version",
                     "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=3,
                    creationflags=_CREATE_NO_WINDOW
                )
                if r.returncode == 0 and r.stdout.strip():
                    result["is_dedicated"] = True
            except Exception:
                pass

        name_lower = result["name"].lower()
        if "microsoft" in name_lower and "basic" in name_lower:
            result["is_dedicated"] = False

        if not result.get("load_percent"):
            try:
                import GPUtil
                gpus_gpu = GPUtil.getGPUs()
                if gpus_gpu:
                    g = gpus_gpu[0]
                    result["load_percent"] = int(g.load * 100)
                    result["memory_used_mb"] = int(g.memoryUsed)
                    result["memory_total_mb"] = int(g.memoryTotal)
                    result["temperature_c"] = int(g.temperature) if g.temperature else result["temperature_c"]
            except ImportError:
                pass
            except Exception:
                pass

        return self._set(key, result)

    def _detect_directx_version(self) -> str:
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-ItemProperty "
                 "'HKLM:\\SOFTWARE\\Microsoft\\DirectX' -EA SilentlyContinue).Version"],
                capture_output=True, text=True, timeout=5,
                creationflags=_CREATE_NO_WINDOW
            )
            ver = r.stdout.strip()
            if ver:
                return ver
        except Exception:
            pass
        try:
            r = subprocess.run(
                ["dxdiag", "/t", os.devnull],
                capture_output=True, text=True, timeout=5,
                creationflags=_CREATE_NO_WINDOW
            )
        except Exception:
            pass
        os_ver = platform.version()
        major = int(os_ver.split(".")[0]) if "." in os_ver else 0
        if major >= 10:
            return "12.2"
        return "11.0"

    def get_motherboard_info(self) -> Dict:
        key = "motherboard"
        if self._cached(key):
            return self._get(key)

        result: Dict[str, Any] = {
            "manufacturer": "Unknown",
            "product": "Unknown",
            "version": "Unknown",
            "serial": "Unknown",
            "chipset": "Unknown",
            "form_factor": "Unknown",
            "bios_vendor": "Unknown",
            "bios_version": "Unknown",
            "bios_date": "Unknown",
            "uefi": False,
            "slots": {"pcie": [], "memory": []},
        }

        bb_data = _parse_json(_run_pwsh(
            "Get-CimInstance -ClassName Win32_BaseBoard | "
            "Select-Object Manufacturer,Product,Version,SerialNumber | "
            "ConvertTo-Json -Compress"
        ))
        bb = bb_data if isinstance(bb_data, dict) else None
        if bb:
            result["manufacturer"] = bb.get("Manufacturer") or result["manufacturer"]
            result["product"] = bb.get("Product") or result["product"]
            result["version"] = bb.get("Version") or result["version"]
            result["serial"] = bb.get("SerialNumber") or result["serial"]

        bios_data = _parse_json(_run_pwsh(
            "Get-CimInstance -ClassName Win32_BIOS | "
            "Select-Object Manufacturer,SMBIOSBIOSVersion,ReleaseDate,"
            "SerialNumber | ConvertTo-Json -Compress"
        ))
        bios = bios_data if isinstance(bios_data, dict) else None
        if bios:
            result["bios_vendor"] = bios.get("Manufacturer") or result["bios_vendor"]
            result["bios_version"] = bios.get("SMBIOSBIOSVersion") or result["bios_version"]
            rd = bios.get("ReleaseDate") or ""
            if rd:
                try:
                    dt = rd.split(".")[0]
                    result["bios_date"] = datetime.strptime(dt, "%Y%m%d%H%M%S").strftime("%m/%d/%Y")
                except (ValueError, IndexError):
                    result["bios_date"] = rd[:10]

        uefi_raw = _run_pwsh(
            "$m = Get-CimInstance -ClassName Win32_ComputerSystem; "
            "if ($m.FirmwareType -eq 2) { 'True' } else { 'False' }"
        )
        result["uefi"] = "True" in uefi_raw

        result["chipset"] = self._detect_chipset(result["product"])

        pcie_slots = _parse_json(_run_pwsh(
            "Get-CimInstance -ClassName Win32_SystemSlot | "
            "Where-Object { $_.SlotDesignation -match 'PCI|PEG|SLOT' } | "
            "Select-Object SlotDesignation,CurrentUsage,SlotLength,"
            "SlotDataBusWidth | ConvertTo-Json -Compress"
        ))
        for slot in _ensure_list(pcie_slots):
            desig = slot.get("SlotDesignation", "")
            if not desig:
                continue
            width = _parse_int(slot.get("SlotDataBusWidth"), 0)
            gen = "Unknown"
            if width >= 16:
                gen = "x16"
            elif width >= 8:
                gen = "x8"
            elif width >= 4:
                gen = "x4"
            elif width >= 1:
                gen = "x1"
            occupied = _parse_int(slot.get("CurrentUsage"), 0) > 0
            result["slots"]["pcie"].append({
                "slot": desig.strip() + f" {gen}" if gen != "Unknown" else desig.strip(),
                "occupied": occupied,
            })

        mem_slots = _parse_json(_run_pwsh(
            "Get-CimInstance -ClassName Win32_PhysicalMemory | "
            "Select-Object BankLabel,Capacity | ConvertTo-Json -Compress"
        ))
        for mod in _ensure_list(mem_slots):
            cap = _parse_int(mod.get("Capacity", 0))
            result["slots"]["memory"].append({
                "slot": mod.get("BankLabel", "Unknown"),
                "size_gb": cap // (1024 ** 3) if cap else 0,
            })

        return self._set(key, result)

    def _detect_chipset(self, product: str) -> str:
        known = {
            "Z790": "Intel Z790", "Z690": "Intel Z690",
            "B760": "Intel B760", "B660": "Intel B660",
            "H610": "Intel H610", "X670": "AMD X670",
            "B650": "AMD B650", "X570": "AMD X570",
            "B550": "AMD B550", "A520": "AMD A520",
            "TRX40": "AMD TRX40", "WRX80": "AMD WRX80",
            "X299": "Intel X299", "X99": "Intel X99",
            "Z590": "Intel Z590", "Z490": "Intel Z490",
            "H510": "Intel H510", "B560": "Intel B560",
        }
        for key, val in known.items():
            if key in product.upper():
                return val
        return product or "Unknown"

    def get_ram_info(self) -> Dict:
        key = "ram"
        if self._cached(key):
            return self._get(key)

        result: Dict[str, Any] = {
            "total_gb": 0,
            "used_gb": 0,
            "available_gb": 0,
            "percent_used": 0,
            "speed_mhz": 0,
            "form_factor": "DIMM",
            "type": "Unknown",
            "manufacturer": "Unknown",
            "slots_used": 0,
            "slots_total": 4,
            "modules": [],
        }

        try:
            mem = psutil.virtual_memory()
            result["total_gb"] = round(mem.total / (1024 ** 3), 1)
            result["used_gb"] = round(mem.used / (1024 ** 3), 1)
            result["available_gb"] = round(mem.available / (1024 ** 3), 1)
            result["percent_used"] = int(mem.percent)
        except Exception:
            pass

        modules = _parse_json(_run_pwsh(
            "Get-CimInstance -ClassName Win32_PhysicalMemory | "
            "Select-Object Capacity,Speed,Manufacturer,PartNumber,"
            "BankLabel,FormFactor,MemoryType | ConvertTo-Json -Compress"
        ))
        mod_list = _ensure_list(modules)
        result["slots_used"] = len(mod_list)
        mem_type_names = {
            0: "Unknown", 1: "Other", 2: "DRAM", 3: "Synchronous DRAM",
            4: "Cache DRAM", 5: "EDO", 6: "EDRAM", 7: "VRAM",
            8: "SRAM", 9: "RAM", 10: "ROM", 11: "Flash",
            12: "EEPROM", 13: "FEPROM", 14: "EPROM", 15: "CDRAM",
            16: "3DRAM", 17: "SDRAM", 18: "SGRAM", 19: "RDRAM",
            20: "DDR", 21: "DDR2", 22: "DDR2 FB-DIMM",
            24: "DDR3", 25: "FBD2", 26: "DDR4", 27: "LPDDR",
            28: "LPDDR2", 29: "LPDDR3", 30: "LPDDR4",
            31: "DDR5", 32: "LPDDR5", 33: "LPDDR6",
            34: "DDR5 NIO", 35: "DDR5 NIO 2",
        }
        ff_names = {0: "Unknown", 1: "Other", 2: "SIP", 3: "DIP",
                    4: "ZIP", 5: "SOJ", 6: "Proprietary", 7: "SIMM",
                    8: "DIMM", 9: "TSOP", 10: "PGA", 11: "RIMM",
                    12: "SODIMM", 13: "SRIMM", 14: "SMD", 15: "SSMP",
                    16: "QFP", 17: "TQFP", 18: "SOIC", 19: "LCC",
                    20: "PLCC", 21: "BGA", 22: "FPBGA", 23: "LGA",
                    24: "FB-DIMM", 25: "LR-DIMM", 26: "NVDIMM"}

        for mod in mod_list:
            cap = _parse_int(mod.get("Capacity", 0))
            speed = _parse_int(mod.get("Speed", 0))
            mt = _parse_int(mod.get("MemoryType"))
            ff = _parse_int(mod.get("FormFactor"))

            if speed > result["speed_mhz"]:
                result["speed_mhz"] = speed
            if mt and mem_type_names.get(mt, "Unknown") != "Unknown":
                result["type"] = mem_type_names[mt]
            if ff and ff_names.get(ff, "Unknown") != "Unknown":
                result["form_factor"] = ff_names[ff]

            mfr = mod.get("Manufacturer") or ""
            if mfr and mfr.upper() not in ("UNKNOWN", "(STANDARD UNKNOWN)", "") and result["manufacturer"] == "Unknown":
                result["manufacturer"] = mfr

            result["modules"].append({
                "capacity_gb": cap // (1024 ** 3) if cap else 0,
                "speed_mhz": speed,
                "manufacturer": mfr,
                "part_number": (mod.get("PartNumber") or "").strip(),
                "bank_label": mod.get("BankLabel") or "Unknown",
            })

        try:
            total_slots = _run_pwsh(
                "(Get-CimInstance -ClassName Win32_PhysicalMemoryArray -EA SilentlyContinue | "
                "Select-Object -First 1 -ExpandProperty MemoryDevices)"
            )
            if total_slots.isdigit():
                result["slots_total"] = int(total_slots)
        except Exception:
            pass

        return self._set(key, result)

    def get_storage_info(self) -> Dict:
        key = "storage"
        if self._cached(key):
            return self._get(key)

        result: Dict[str, Any] = {"drives": []}

        phys_disks = _parse_json(_run_pwsh(
            "Get-PhysicalDisk | Select-Object FriendlyName,MediaType,BusType,"
            "SerialNumber,Size,HealthStatus,OperationalStatus | "
            "ConvertTo-Json -Compress"
        ))
        phys_map = {}
        media_types = {0: "HDD", 3: "HDD", 4: "SSD"}
        bus_types = {0: "Unknown", 1: "SCSI", 2: "ATAPI", 3: "ATA",
                     4: "1394", 5: "SSA", 6: "Fibre Channel", 7: "USB",
                     8: "RAID", 9: "iSCSI", 10: "SAS", 11: "SATA",
                     12: "SD", 13: "MMC", 14: "Virtual", 15: "NVMe"}

        for pd in _ensure_list(phys_disks):
            # WMI happily returns a key with a null value, so a dict default
            # does not protect against None here.
            sn = str(pd.get("SerialNumber") or "").strip()
            phys_map[sn] = pd

        win_disks = _parse_json(_run_pwsh(
            "Get-CimInstance -ClassName Win32_DiskDrive | "
            "Select-Object Model,SerialNumber,Size,InterfaceType,BootDrive,"
            "Partitions | ConvertTo-Json -Compress"
        ))
        disk_partitions = psutil.disk_partitions()
        boot_drive = os.environ.get("SystemDrive", "C:") + "\\"

        for wd in _ensure_list(win_disks):
            sn = str(wd.get("SerialNumber") or "").strip()
            phys = phys_map.get(sn, {})
            model = wd.get("Model") or phys.get("FriendlyName") or "Unknown"
            total = _parse_int(wd.get("Size", 0))

            media_type = media_types.get(_parse_int(phys.get("MediaType")), "Unknown")
            bus_type = bus_types.get(_parse_int(phys.get("BusType")), "Unknown")
            serial = sn or wd.get("SerialNumber") or "Unknown"
            health = phys.get("HealthStatus", "Unknown")
            boot = (wd.get("BootDrive") is True) or (
                str(wd.get("BootDrive") or "").strip().lower() == "true"
            )

            interface = bus_type
            if bus_type == "NVMe" or "NVMe" in model:
                interface = "NVMe"
            elif bus_type == "SATA":
                interface = "SATA"
            elif bus_type == "SAS":
                interface = "SAS"

            drive_info: Dict[str, Any] = {
                "drive": "Unknown",
                "label": "",
                "filesystem": "Unknown",
                "total_gb": _format_size_gb(total) if total else 0,
                "used_gb": 0,
                "free_gb": 0,
                "percent_free": 0,
                "type": "SSD" if media_type == "SSD" or "SSD" in model else media_type,
                "model": model,
                "serial": serial,
                "interface": interface,
                "temperature_c": None,
                "health_percent": None,
                "is_boot": boot,
            }

            sn_lower = serial.lower()
            for part in disk_partitions:
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                except (PermissionError, OSError):
                    continue
                if sn_lower and sn_lower in part.device.lower():
                    drive_info["drive"] = part.device
                    drive_info["filesystem"] = part.fstype
                    drive_info["total_gb"] = round(usage.total / (1024 ** 3), 1)
                    drive_info["used_gb"] = round(usage.used / (1024 ** 3), 1)
                    drive_info["free_gb"] = round(usage.free / (1024 ** 3), 1)
                    drive_info["percent_free"] = round(
                        (usage.free / usage.total) * 100, 1) if usage.total else 0
                    if part.mountpoint == boot_drive.rstrip("\\"):
                        drive_info["is_boot"] = True
                    break
            else:
                for part in disk_partitions:
                    try:
                        usage = psutil.disk_usage(part.mountpoint)
                    except (PermissionError, OSError):
                        continue
                    if part.fstype and part.fstype.lower() != "fat":
                        d_total = round(usage.total / (1024 ** 3), 0)
                        if d_total == drive_info["total_gb"] or d_total >= drive_info["total_gb"] * 0.9:
                            drive_info["drive"] = part.device
                            drive_info["filesystem"] = part.fstype
                            drive_info["total_gb"] = round(usage.total / (1024 ** 3), 1)
                            drive_info["used_gb"] = round(usage.used / (1024 ** 3), 1)
                            drive_info["free_gb"] = round(usage.free / (1024 ** 3), 1)
                            drive_info["percent_free"] = round(
                                (usage.free / usage.total) * 100, 1) if usage.total else 0
                            if part.mountpoint == boot_drive.rstrip("\\"):
                                drive_info["is_boot"] = True
                            break

            temp_out = _run_pwsh(
                "Get-PhysicalDisk | Where-Object { $_.SerialNumber -eq '" +
                serial.replace("'", "''") + "' } | "
                "Select-Object @{N='Temp';E={$_.Temperature}} | "
                "ConvertTo-Json -Compress"
            )
            temp_data = _parse_json(temp_out)
            if temp_data and isinstance(temp_data, dict):
                tc = temp_data.get("Temp")
                if tc is not None:
                    try:
                        drive_info["temperature_c"] = int(tc)
                    except (ValueError, TypeError):
                        pass

            if health == "Healthy":
                drive_info["health_percent"] = 100
            elif health and "Warning" in health:
                drive_info["health_percent"] = 70
            elif health and "Unhealthy" in health:
                drive_info["health_percent"] = 30

            result["drives"].append(drive_info)

        if not result["drives"]:
            for part in disk_partitions:
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                except (PermissionError, OSError):
                    continue
                result["drives"].append({
                    "drive": part.device,
                    "label": "",
                    "filesystem": part.fstype,
                    "total_gb": round(usage.total / (1024 ** 3), 1),
                    "used_gb": round(usage.used / (1024 ** 3), 1),
                    "free_gb": round(usage.free / (1024 ** 3), 1),
                    "percent_free": round(
                        (usage.free / usage.total) * 100, 1) if usage.total else 0,
                    "type": "Unknown",
                    "model": "Unknown",
                    "serial": "Unknown",
                    "interface": "Unknown",
                    "temperature_c": None,
                    "health_percent": None,
                    "is_boot": part.mountpoint == boot_drive.rstrip("\\"),
                })

        return self._set(key, result)

    def get_battery_info(self) -> Dict:
        key = "battery"
        if self._cached(key):
            return self._get(key)

        result: Dict[str, Any] = {
            "present": False,
            "health_percent": None,
            "cycle_count": None,
            "design_capacity_mwh": None,
            "full_charge_capacity_mwh": None,
            "current_capacity_mwh": None,
            "voltage_mv": None,
            "temperature_c": None,
            "manufacturer": "Unknown",
            "chemistry": "Unknown",
            "estimated_runtime_minutes": None,
            "power_plan": "Unknown",
        }

        batt_data = _parse_json(_run_pwsh(
            "Get-CimInstance -ClassName Win32_Battery | "
            "Select-Object Manufacturer,Chemistry,DesignCapacity,"
            "FullChargeCapacity,EstimatedChargeRemaining,"
            "DesignVoltage,EstimatedRuntime,BatteryStatus | "
            "ConvertTo-Json -Compress"
        ))
        batt = batt_data if isinstance(batt_data, dict) else None
        if not batt:
            b_list = _ensure_list(batt_data)
            batt = b_list[0] if b_list else None
        if not batt:
            try:
                if psutil.sensors_battery():
                    result["present"] = True
            except Exception:
                pass
            return self._set(key, result)

        result["present"] = True
        result["manufacturer"] = batt.get("Manufacturer") or result["manufacturer"]
        chem = _parse_int(batt.get("Chemistry"))
        chem_names = {1: "Other", 2: "Unknown", 3: "Lead Acid", 4: "NiCd",
                      5: "NiMH", 6: "Li-ion", 7: "LiPo", 8: "LiFePO4",
                      9: "NiH2", 10: "NiMH", 11: "AgO", 12: "ZnMnO2",
                      13: "AgCl", 14: "AgZn", 15: "NiZn", 16: "AgCd",
                      17: "AgH", 18: "AgMn", 19: "AgMg", 20: "AgHg",
                      21: "AgPb", 22: "AgFe", 23: "NiFe",
                      24: "NiCo", 25: "NiAl", 26: "Li-SOCl2",
                      27: "Li-MnO2", 28: "Li-Ion Polymer"}
        result["chemistry"] = chem_names.get(chem, "Unknown")
        dc = _parse_int(batt.get("DesignCapacity"))
        if dc:
            result["design_capacity_mwh"] = dc
        fcc = _parse_int(batt.get("FullChargeCapacity"))
        if fcc:
            result["full_charge_capacity_mwh"] = fcc
        if dc and fcc:
            result["health_percent"] = round((fcc / dc) * 100, 1)

        dv = _parse_int(batt.get("DesignVoltage"))
        if dv:
            result["voltage_mv"] = dv

        est = _parse_int(batt.get("EstimatedRuntime"))
        if est:
            result["estimated_runtime_minutes"] = est

        try:
            sb = psutil.sensors_battery()
            if sb:
                if sb.secsleft and sb.secsleft > 0:
                    result["estimated_runtime_minutes"] = int(sb.secsleft / 60)
                if sb.power_plugged is not None:
                    result["voltage_mv"] = result.get("voltage_mv") or 0
        except Exception:
            pass

        fcc_raw = _run_pwsh(
            "Get-WmiObject -Namespace root\\wmi -Class BatteryFullChargedCapacity "
            "-EA SilentlyContinue | Select-Object -First 1 -ExpandProperty FullChargedCapacity"
        )
        if fcc_raw and fcc_raw.strip().isdigit():
            fcc2 = int(fcc_raw.strip())
            result["full_charge_capacity_mwh"] = fcc2
            if result.get("design_capacity_mwh") and fcc2:
                result["health_percent"] = round((fcc2 / result["design_capacity_mwh"]) * 100, 1)

        cc_raw = _run_pwsh(
            "Get-WmiObject -Namespace root\\wmi -Class BatteryCycleCount "
            "-EA SilentlyContinue | Select-Object -First 1 -ExpandProperty CycleCount"
        )
        if cc_raw and cc_raw.strip().isdigit():
            result["cycle_count"] = int(cc_raw.strip())

        temp_raw = _run_pwsh(
            "Get-WmiObject -Namespace root\\wmi -Class BatteryTemperature "
            "-EA SilentlyContinue | Select-Object -First 1 -ExpandProperty Temperature"
        )
        if temp_raw and temp_raw.strip():
            try:
                result["temperature_c"] = int(temp_raw.strip()) // 10
            except (ValueError, TypeError):
                pass

        plan = self._detector.detect_power_plan()
        result["power_plan"] = plan.get("name", "Unknown")

        return self._set(key, result)

    def get_network_info(self) -> Dict:
        key = "network"
        if self._cached(key):
            return self._get(key)

        result: Dict[str, Any] = {
            "adapters": [],
            "connections_active": 0,
            "total_sent_gb": 0.0,
            "total_received_gb": 0.0,
        }

        try:
            net_io = psutil.net_io_counters()
            result["total_sent_gb"] = round(net_io.bytes_sent / (1024 ** 3), 2)
            result["total_received_gb"] = round(net_io.bytes_recv / (1024 ** 3), 2)
        except Exception:
            pass

        try:
            cons = len(psutil.net_connections())
            result["connections_active"] = cons
        except Exception:
            pass

        net_adapters = _parse_json(_run_pwsh(
            "Get-NetAdapter | Select-Object Name,InterfaceDescription,"
            "LinkSpeed,Status,MacAddress,DriverVersion,DriverDate,"
            "MediaType,InterfaceType | ConvertTo-Json -Compress"
        ))

        if_addrs = {}
        try:
            if_addrs = psutil.net_if_addrs()
        except Exception:
            pass

        net_stats = {}
        try:
            net_stats = psutil.net_if_stats()
        except Exception:
            pass

        adapter_map = {}
        for adapter in _ensure_list(net_adapters):
            desc = adapter.get("InterfaceDescription") or adapter.get("Name", "")
            adapter_map[desc.lower().strip()] = adapter

        processed = set()
        for name, addrs in if_addrs.items():
            name_lower = name.lower().strip()
            if name_lower in processed:
                continue
            processed.add(name_lower)

            adapter_info = adapter_map.get(name_lower, {})
            if not adapter_info:
                for key_name, val in adapter_map.items():
                    if name_lower in key_name or key_name in name_lower:
                        adapter_info = val
                        break

            ipv4 = ""
            ipv6 = ""
            mac = ""
            for addr in addrs:
                if addr.family == 2:
                    ipv4 = addr.address
                elif addr.family == 23:
                    ipv6 = addr.address
                elif addr.family == -1:
                    mac = addr.address

            speed_raw = adapter_info.get("LinkSpeed", "0")
            speed_mbps = 0
            if speed_raw:
                try:
                    if "Gbps" in str(speed_raw):
                        speed_mbps = int(float(str(speed_raw).replace("Gbps", "").strip()) * 1000)
                    else:
                        speed_mbps = int(re.sub(r'[^0-9]', '', str(speed_raw)) or 0)
                except (ValueError, TypeError):
                    pass

            status_raw = adapter_info.get("Status", "")
            status = "Up" if "Up" in str(status_raw) else "Down" if "Down" in str(status_raw) else "Unknown"

            is_wifi = any(w in name_lower for w in ["wi-fi", "wireless", "wlan", "802.11"])

            drv_date_raw = adapter_info.get("DriverDate", "")
            result_adapter: Dict[str, Any] = {
                "name": adapter_info.get("Name") or adapter_info.get("InterfaceDescription") or name,
                "type": "WiFi" if is_wifi else "Ethernet",
                "mac": mac or adapter_info.get("MacAddress", ""),
                "ipv4": ipv4,
                "ipv6": ipv6,
                "gateway": "",
                "dns": [],
                "dhcp": False,
                "speed_mbps": speed_mbps,
                "rx_bytes": 0,
                "tx_bytes": 0,
                "is_wifi": is_wifi,
                "ssid": None,
                "signal_percent": None,
                "driver_version": adapter_info.get("DriverVersion", "Unknown"),
                "driver_date": _format_date(drv_date_raw),
                "status": status,
            }

            try:
                io_counters = psutil.net_io_counters(pernic=True)
                if name in io_counters:
                    result_adapter["rx_bytes"] = io_counters[name].bytes_recv
                    result_adapter["tx_bytes"] = io_counters[name].bytes_sent
            except Exception:
                pass

            result["adapters"].append(result_adapter)

        if not result["adapters"]:
            for adapter in _ensure_list(net_adapters):
                desc = adapter.get("InterfaceDescription") or adapter.get("Name", "Unknown")
                ipv4 = ""
                ipv6 = ""
                mac = adapter.get("MacAddress", "")
                for name, addrs in if_addrs.items():
                    for addr in addrs:
                        if addr.family == -1:
                            mac = addr.address
                    if mac and name.lower() in desc.lower():
                        for addr in addrs:
                            if addr.family == 2 and not ipv4:
                                ipv4 = addr.address
                            elif addr.family == 23 and not ipv6:
                                ipv6 = addr.address

                status_raw = adapter.get("Status", "")
                status = "Up" if "Up" in str(status_raw) else "Down"

                result["adapters"].append({
                    "name": desc,
                    "type": "Ethernet",
                    "mac": mac,
                    "ipv4": ipv4,
                    "ipv6": ipv6,
                    "gateway": "",
                    "dns": [],
                    "dhcp": False,
                    "speed_mbps": 0,
                    "rx_bytes": 0,
                    "tx_bytes": 0,
                    "is_wifi": "wi-fi" in desc.lower() or "wireless" in desc.lower(),
                    "ssid": None,
                    "signal_percent": None,
                    "driver_version": adapter.get("DriverVersion", "Unknown"),
                    "driver_date": _format_date(adapter.get("DriverDate", "")),
                    "status": status,
                })

        for adapter in result["adapters"]:
            if adapter["ipv4"]:
                gw_raw = _run_pwsh(
                    "Get-NetRoute -DestinationPrefix '0.0.0.0/0' -EA SilentlyContinue | "
                    "Select-Object -First 1 -ExpandProperty NextHop"
                )
                if gw_raw:
                    adapter["gateway"] = gw_raw.strip()
            dhcp_raw = _run_pwsh(
                "Get-NetIPInterface -InterfaceAlias '" +
                adapter["name"].replace("'", "''") +
                "' -EA SilentlyContinue | "
                "Select-Object -First 1 -ExpandProperty Dhcp"
            )
            adapter["dhcp"] = "Enabled" in dhcp_raw or "True" in dhcp_raw

        return self._set(key, result)

    def get_bios_info(self) -> Dict:
        key = "bios"
        if self._cached(key):
            return self._get(key)

        result: Dict[str, Any] = {
            "vendor": "Unknown",
            "version": "Unknown",
            "date": "Unknown",
            "uefi": False,
            "secure_boot": None,
            "tpm_present": False,
            "tpm_version": "",
            "tpm_manufacturer": "",
            "manufacturer_version": "",
        }

        bios_data = _parse_json(_run_pwsh(
            "Get-CimInstance -ClassName Win32_BIOS | "
            "Select-Object Manufacturer,SMBIOSBIOSVersion,ReleaseDate,"
            "SerialNumber | ConvertTo-Json -Compress"
        ))
        bios = bios_data if isinstance(bios_data, dict) else None
        if bios:
            result["vendor"] = bios.get("Manufacturer") or result["vendor"]
            result["version"] = bios.get("SMBIOSBIOSVersion") or result["version"]
            rd = bios.get("ReleaseDate") or ""
            if rd:
                try:
                    dt = rd.split(".")[0]
                    result["date"] = datetime.strptime(dt, "%Y%m%d%H%M%S").strftime("%m/%d/%Y")
                except (ValueError, IndexError):
                    result["date"] = rd[:10]

        uefi_raw = _run_pwsh(
            "$m = Get-CimInstance -ClassName Win32_ComputerSystem; "
            "if ($m.FirmwareType -eq 2) { 'True' } else { 'False' }"
        )
        result["uefi"] = "True" in uefi_raw

        sb_raw = _run_pwsh("Confirm-SecureBootUEFI -EA SilentlyContinue")
        if "True" in sb_raw:
            result["secure_boot"] = True
        elif "False" in sb_raw:
            result["secure_boot"] = False

        tpm_data = _parse_json(_run_pwsh(
            "Get-CimInstance -Namespace 'Root/CIMv2/Security/MicrosoftTpm' "
            "-ClassName Win32_Tpm -EA SilentlyContinue | "
            "Select-Object IsEnabled_InitialValue,IsActivated_InitialValue,"
            "ManufacturerID,ManufacturerVersion | "
            "ConvertTo-Json -Compress"
        ))
        tpm = tpm_data if isinstance(tpm_data, dict) else None
        if tpm:
            enabled = tpm.get("IsEnabled_InitialValue")
            if enabled is not None:
                result["tpm_present"] = bool(enabled)
            else:
                result["tpm_present"] = True
            mid = _parse_int(tpm.get("ManufacturerID"))
            tpm_mfrs = {
                1095585868: "Infineon", 1112687437: "Intel",
                1129462347: "IBM", 1145855563: "Microsoft",
                1163222859: "NTC", 1196376907: "Nuvoton",
                1202203467: "Qualcomm", 1229346827: "STMicroelectronics",
                1245857105: "Samsung", 1297300309: "Winbond",
            }
            result["tpm_manufacturer"] = tpm_mfrs.get(mid, "Unknown")
            result["tpm_version"] = tpm.get("ManufacturerVersion") or "Unknown"
            result["manufacturer_version"] = result["tpm_version"]

        tpm2_check = _run_pwsh(
            "(Get-CimInstance -Namespace 'Root/CIMv2/Security/MicrosoftTpm' "
            "-ClassName Win32_Tpm -EA SilentlyContinue).SpecVersion"
        )
        if tpm2_check and "2." in tpm2_check:
            result["tpm_version"] = "2.0"

        return self._set(key, result)

    def get_driver_info(self) -> Dict:
        key = "drivers"
        if self._cached(key):
            return self._get(key)

        result: Dict[str, Any] = {
            "total_drivers": 0,
            "outdated_drivers": 0,
            "unsigned_drivers": 0,
            "problem_drivers": 0,
            "drivers": [],
        }

        drv_data = _parse_json(_run_pwsh(
            "Get-CimInstance -ClassName Win32_PnPSignedDriver | "
            "Select-Object DeviceName,DriverProviderName,DriverVersion,"
            "DriverDate,IsSigned,DeviceID,DeviceClass | "
            "ConvertTo-Json -Compress",
            timeout=20
        ))
        for drv in _ensure_list(drv_data):
            name = (drv.get("DeviceName") or "").strip()
            if not name:
                continue
            provider = drv.get("DriverProviderName") or "Unknown"
            version = drv.get("DriverVersion") or "Unknown"
            drv_date = drv.get("DriverDate") or ""
            signed = drv.get("IsSigned")
            driver_entry = {
                "name": name,
                "provider": provider,
                "version": version,
                "date": _format_date(drv_date.split(".")[0] if "." in drv_date else drv_date),
                "signed": bool(signed) if signed is not None else True,
                "problem": 0,
            }
            if not driver_entry["signed"]:
                result["unsigned_drivers"] += 1
            result["drivers"].append(driver_entry)

        result["total_drivers"] = len(result["drivers"])

        problem_data = _parse_json(_run_pwsh(
            "Get-CimInstance -ClassName Win32_PnPEntity -EA SilentlyContinue | "
            "Where-Object { $_.ConfigManagerErrorCode -ne 0 } | "
            "Select-Object Name,ConfigManagerErrorCode,DeviceID | "
            "ConvertTo-Json -Compress"
        ))
        problem_devices = {}
        for p in _ensure_list(problem_data):
            pid = p.get("DeviceID", "")
            code = _parse_int(p.get("ConfigManagerErrorCode"))
            if pid and code:
                problem_devices[pid] = code

        for drv in result["drivers"]:
            did = drv.get("name", "")
            if did in problem_devices:
                drv["problem"] = problem_devices[did]
                result["problem_drivers"] += 1

        result["outdated_drivers"] = len([
            d for d in result["drivers"]
            if d["date"] and d["date"] < "2023-01-01" and d["date"] != "Unknown"
        ])

        return self._set(key, result)

    def get_all(self) -> Dict:
        return {
            "cpu": self.get_cpu_info(),
            "gpu": self.get_gpu_info(),
            "motherboard": self.get_motherboard_info(),
            "ram": self.get_ram_info(),
            "storage": self.get_storage_info(),
            "battery": self.get_battery_info(),
            "network": self.get_network_info(),
            "bios": self.get_bios_info(),
            "drivers": self.get_driver_info(),
        }

    def get_system_summary(self) -> Dict:
        cpu = self.get_cpu_info()
        gpu = self.get_gpu_info()
        ram = self.get_ram_info()
        storage = self.get_storage_info()
        battery = self.get_battery_info()
        bios = self.get_bios_info()
        mobo = self.get_motherboard_info()

        drives = storage.get("drives", [])
        boot_drive = next((d for d in drives if d.get("is_boot")), drives[0] if drives else {})

        memory_gb = ram.get("modules", [])
        ram_config = (
            f"{ram.get('total_gb', 0)} GB ({ram.get('slots_used', 0)}/"
            f"{ram.get('slots_total', 0)} slots) {ram.get('type', '')}"
            f" @ {ram.get('speed_mhz', 0)} MHz"
        )

        summary: Dict[str, Any] = {
            "os": f"{platform.system()} {platform.release()}",
            "hostname": platform.node(),
            "cpu": f"{cpu.get('name')} ({cpu.get('cores_physical')}C/"
                   f"{cpu.get('cores_logical')}T @ {cpu.get('max_clock_ghz', 0)} GHz)",
            "gpu": gpu.get("name"),
            "ram": ram_config,
            "storage": (
                f"{boot_drive.get('drive', 'Unknown')} "
                f"{boot_drive.get('total_gb', 0)} GB "
                f"{boot_drive.get('type', '')} "
                f"({boot_drive.get('free_gb', 0)} GB free)"
            ),
            "motherboard": f"{mobo.get('manufacturer')} {mobo.get('product')}",
            "bios": f"{bios.get('vendor')} v{bios.get('version')} ({bios.get('date')})",
            "architecture": cpu.get("architecture"),
            "uptime_days": cpu.get("uptime_days", 0),
            "has_battery": battery.get("present", False),
            "secure_boot": bios.get("secure_boot"),
            "tpm": f"{bios.get('tpm_version')}" if bios.get("tpm_present") else None,
        }
        return summary


device_info_provider = DeviceInfoProvider()
