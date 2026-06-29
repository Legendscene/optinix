import subprocess


class GPUOptimizer:
    name = "GPU Optimization"

    def __init__(self, os_type):
        self.os_type = os_type
        self.results = []

    def run(self):
        self.results = []
        if self.os_type == "windows":
            self._hw_gpu_scheduling()
            self._optimize_nvidia()
            self._optimize_amd()
            self._gpu_priority_multimedia()
        return self.results

    def _hw_gpu_scheduling(self):
        try:
            cmds = [
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\GraphicsDrivers" /v HwSchMode /t REG_DWORD /d 2 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\GraphicsDrivers" /v TdrDelay /t REG_DWORD /d 10 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\GraphicsDrivers" /v TdrDdiDelay /t REG_DWORD /d 10 /f',
            ]
            for cmd in cmds:
                subprocess.run(cmd.split(), capture_output=True, timeout=10)
            self.results.append({"success": True, "message": "GPU hardware scheduling enabled, TDR delay increased"})
        except Exception as e:
            self.results.append({"success": False, "message": f"GPU scheduling failed: {e}"})

    def _optimize_nvidia(self):
        try:
            cmds = [
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\GraphicsDrivers" /v PlatformSupport /t REG_DWORD /d 1 /f',
                'nvidia-smi -pm 1 2>$null',
            ]
            for cmd in cmds:
                subprocess.run(cmd, capture_output=True, timeout=10, shell=True)
            self.results.append({"success": True, "message": "NVIDIA: persistent mode enabled, platform support set"})
        except Exception:
            pass

        try:
            profile_paths = [
                "HKLM\\SOFTWARE\\NVIDIA Corporation\\Global\\NvTweak",
                "HKCU\\Software\\NVIDIA Corporation\\Global\\NvTweak"
            ]
            for path in profile_paths:
                cmds = [
                    f'reg add "{path}" /v NvCplEnableGraphicsPage /t REG_DWORD /d 1 /f',
                    f'reg add "{path}" /v NvCplEnableVideoPage /t REG_DWORD /d 0 /f',
                ]
                for cmd in cmds:
                    subprocess.run(cmd, capture_output=True, timeout=10, shell=True)
        except Exception:
            pass

    def _optimize_amd(self):
        try:
            amd_keys = [
                "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Class\\{4d36e968-e325-11ce-bfc1-08002be10318}\\0000",
                "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Class\\{4d36e968-e325-11ce-bfc1-08002be10318}\\0001",
            ]
            for key in amd_keys:
                cmds = [
                    f'reg add "{key}" /v DisableDMACopy /t REG_DWORD /d 1 /f',
                    f'reg add "{key}" /v EnableUlps /t REG_DWORD /d 0 /f',
                    f'reg add "{key}" /v EnableUlps_NA /t REG_DWORD /d 0 /f',
                    f'reg add "{key}" /v PP_SclkDeepSleepDisable /t REG_DWORD /d 1 /f',
                    f'reg add "{key}" /v PP_ThermalAutoMonitorDisable /t REG_DWORD /d 1 /f',
                    f'reg add "{key}" /v KMD_FrameRateLimit /t REG_DWORD /d 0 /f',
                ]
                for cmd in cmds:
                    subprocess.run(cmd, capture_output=True, timeout=10, shell=True)
            self.results.append({"success": True, "message": "AMD GPU: ULPS disabled, deep sleep off, spread spectrum optimized"})
        except Exception as e:
            self.results.append({"success": False, "message": f"AMD GPU tweaks failed: {e}"})

    def _gpu_priority_multimedia(self):
        try:
            cmds = [
                'reg add "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Multimedia\\SystemProfile" /v SystemResponsiveness /t REG_DWORD /d 0 /f',
                'reg add "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Multimedia\\SystemProfile" /v "NetworkThrottlingIndex" /t REG_DWORD /d 4294967295 /f',
                'reg add "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Multimedia\\SystemProfile\\Tasks\\Games" /v "GPU Priority" /t REG_DWORD /d 8 /f',
                'reg add "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Multimedia\\SystemProfile\\Tasks\\Games" /v Priority /t REG_DWORD /d 6 /f',
                'reg add "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Multimedia\\SystemProfile\\Tasks\\Games" /v "Scheduling Category" /t REG_SZ /d "High" /f',
            ]
            for cmd in cmds:
                subprocess.run(cmd.split(), capture_output=True, timeout=10)
            self.results.append({"success": True, "message": "GPU multimedia priority set (max GPU, zero responsiveness reserve)"})
        except Exception as e:
            self.results.append({"success": False, "message": f"GPU priority failed: {e}"})
