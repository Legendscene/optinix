import subprocess
import re
from typing import Dict, Any, List
from core.base import OptimizerBase, OPTIMIZER_CATEGORY_ADVANCED
from core.config import CONFIG


class GPUOptimizer(OptimizerBase):
    name = "GPU Optimizer"
    description = "Enables Hardware Accelerated GPU Scheduling, NVIDIA shader cache, high-performance GPU preference, and reports GPU/driver info"
    category = OPTIMIZER_CATEGORY_ADVANCED
    benefit = "Reduces input lag via HAGS, improves NVIDIA shader compilation, prefers discrete GPU for games"
    risks = "HAGS may cause issues on very old GPU drivers (requires reboot); shader cache uses more disk space"
    admin_required = True
    requires_reboot = False
    requirements = {}

    def __init__(self):
        super().__init__()
        self.os_type = CONFIG.os_type

    def run(self) -> List[Dict[str, Any]]:
        self.results = []
        self.logger.info("Starting GPU optimization")
        self._detect_gpu()
        self._enable_hags()
        self._nvidia_driver_check()
        self._nvidia_shader_cache()
        self._gpu_preference_mode()
        return [r.to_dict() for r in self.results]

    def _reg_query(self, key: str, value: str) -> str:
        try:
            r = subprocess.run(
                ["reg", "query", key, "/v", value],
                capture_output=True, text=True, timeout=5
            )
            if r.returncode != 0:
                return ""
            for line in r.stdout.splitlines():
                if value in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        return parts[-1]
            return ""
        except Exception:
            return ""

    def _detect_gpu(self):
        try:
            r = subprocess.run(
                ["wmic", "path", "win32_videocontroller", "get", "name,DriverVersion,DriverDate"],
                capture_output=True, text=True, timeout=10
            )
            lines = [l.strip() for l in r.stdout.split("\n") if l.strip() and "name" not in l.lower()]
            if lines:
                for gpu in lines:
                    self.add_result(True, f"Detected GPU: {gpu}")
            else:
                self.add_result(False, "No GPU detected via WMIC")
        except Exception as e:
            self.logger.error(f"GPU detection failed: {e}")
            self.add_result(False, f"GPU detection failed: {e}")

    def _enable_hags(self):
        try:
            key = r"HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers"
            current = self._reg_query(key, "HwSchMode")
            if current == "0x2":
                self.add_result(True, "HAGS: already enabled")
                return
            subprocess.run(
                ["reg", "add", key, "/v", "HwSchMode", "/t", "REG_DWORD", "/d", "2", "/f"],
                capture_output=True, timeout=5
            )
            self.add_result(True, "HAGS: enabled (requires reboot)")
        except Exception as e:
            self.logger.error(f"HAGS: {e}")
            self.add_result(False, f"HAGS: failed — {e}")

    def _nvidia_driver_check(self):
        try:
            r = subprocess.run(
                ["nvidia-smi", "--query-gpu=driver_version,name,pstate", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=10
            )
            if r.returncode != 0 or not r.stdout.strip():
                self.add_result(False, "NVIDIA driver: nvidia-smi unavailable (not NVIDIA or driver missing)")
                return
            for line in r.stdout.strip().split("\n"):
                line = line.strip()
                if line:
                    self.add_result(True, f"NVIDIA driver: {line}")
        except FileNotFoundError:
            self.add_result(False, "NVIDIA driver: nvidia-smi not found (not an NVIDIA GPU)")
        except Exception as e:
            self.logger.error(f"NVIDIA driver check: {e}")
            self.add_result(False, f"NVIDIA driver check failed: {e}")

    def _nvidia_shader_cache(self):
        try:
            gpu_class = r"HKLM\SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
            found_nvidia = False
            for i in range(10):
                sk = f"{gpu_class}\\{i:04d}"
                r = subprocess.run(["reg", "query", sk], capture_output=True, timeout=5)
                if r.returncode != 0:
                    continue
                driver = self._reg_query(sk, "DriverDesc")
                if driver and "nvidia" in driver.lower():
                    found_nvidia = True
                    current = self._reg_query(sk, "ProfileAmount")
                    if current == "0x1":
                        self.add_result(True, f"NVIDIA Shader Cache: already maximum ({driver})")
                    else:
                        subprocess.run(
                            ["reg", "add", sk, "/v", "ProfileAmount", "/t", "REG_DWORD", "/d", "1", "/f"],
                            capture_output=True, timeout=5
                        )
                        self.add_result(True, f"NVIDIA Shader Cache: set to maximum ({driver})")
            if not found_nvidia:
                self.add_result(False, "NVIDIA Shader Cache: no NVIDIA GPU found in registry")
        except Exception as e:
            self.logger.error(f"NVIDIA Shader Cache: {e}")
            self.add_result(False, f"NVIDIA Shader Cache: failed — {e}")

    def _gpu_preference_mode(self):
        try:
            key = r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games"
            subprocess.run(["reg", "add", key, "/f"], capture_output=True, timeout=5)
            current = self._reg_query(key, "GPU Priority")
            if current == "0x8":
                self.add_result(True, "GPU Preference: already High Performance for games")
                return
            subprocess.run(
                ["reg", "add", key, "/v", "GPU Priority", "/t", "REG_DWORD", "/d", "8", "/f"],
                capture_output=True, timeout=5
            )
            self.add_result(True, "GPU Preference: set to High Performance for games")
        except Exception as e:
            self.logger.error(f"GPU Preference: {e}")
            self.add_result(False, f"GPU Preference: failed — {e}")
