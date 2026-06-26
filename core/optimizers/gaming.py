import subprocess


class GamingOptimizer:
    name = "Gaming Optimization"

    def __init__(self, os_type):
        self.os_type = os_type
        self.results = []

    def run(self):
        self.results = []
        if self.os_type == "windows":
            self._enable_game_mode()
            self._disable_game_dvr()
            self._disable_fullscreen_opt()
            self._optimize_gpu_priority()
            self._disable_game_bar()
            self._disable_mouse_accel()
            self._optimize_shader_cache()
            self._disable_visual_effects()
        elif self.os_type == "linux":
            self._linux_gaming()
        elif self.os_type == "macos":
            self._macos_gaming()
        return self.results

    def _enable_game_mode(self):
        try:
            cmds = [
                'reg add "HKCU\\Software\\Microsoft\\GameBar" /v AllowAutoGameMode /t REG_DWORD /d 1 /f',
                'reg add "HKCU\\Software\\Microsoft\\GameBar" /v AutoGameModeEnabled /t REG_DWORD /d 1 /f'
            ]
            for cmd in cmds:
                subprocess.run(cmd.split(), capture_output=True, timeout=10)
            self.results.append({"success": True, "message": "Game Mode enabled"})
        except Exception as e:
            self.results.append({"success": False, "message": f"Game Mode failed: {e}"})

    def _disable_game_dvr(self):
        try:
            cmds = [
                'reg add "HKCU\\System\\GameConfigStore" /v GameDVR_Enabled /t REG_DWORD /d 0 /f',
                'reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\GameDVR" /v AppCaptureEnabled /t REG_DWORD /d 0 /f',
                'reg add "HKCU\\Software\\Microsoft\\GameBar" /v UseNexusForGameBarEnabled /t REG_DWORD /d 0 /f'
            ]
            for cmd in cmds:
                subprocess.run(cmd.split(), capture_output=True, timeout=10)
            self.results.append({"success": True, "message": "Game DVR disabled (no recording overhead)"})
        except Exception as e:
            self.results.append({"success": False, "message": f"Game DVR failed: {e}"})

    def _disable_fullscreen_opt(self):
        try:
            cmds = [
                'reg add "HKCU\\System\\GameConfigStore" /v GameDVR_FSEBehaviorMode /t REG_DWORD /d 2 /f',
                'reg add "HKCU\\System\\GameConfigStore" /v GameDVR_HonorUserFSEBehaviorMode /t REG_DWORD /d 1 /f',
                'reg add "HKCU\\System\\GameConfigStore" /v GameDVR_FSEBehavior /t REG_DWORD /d 2 /f',
                'reg add "HKCU\\System\\GameConfigStore" /v GameDVR_DXGIHonorFSEWindowsCompatible /t REG_DWORD /d 1 /f'
            ]
            for cmd in cmds:
                subprocess.run(cmd.split(), capture_output=True, timeout=10)
            self.results.append({"success": True, "message": "Fullscreen optimizations disabled (lower input lag)"})
        except Exception as e:
            self.results.append({"success": False, "message": f"Fullscreen opt failed: {e}"})

    def _optimize_gpu_priority(self):
        try:
            cmds = [
                'reg add "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Multimedia\\SystemProfile\\Tasks\\Games" /v "GPU Priority" /t REG_DWORD /d 8 /f',
                'reg add "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Multimedia\\SystemProfile\\Tasks\\Games" /v Priority /t REG_DWORD /d 6 /f',
                'reg add "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Multimedia\\SystemProfile\\Tasks\\Games" /v "Scheduling Category" /t REG_SZ /d "High" /f',
                'reg add "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Multimedia\\SystemProfile" /v SystemResponsiveness /t REG_DWORD /d 0 /f',
                'reg add "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Multimedia\\SystemProfile" /v "NetworkThrottlingIndex" /t REG_DWORD /d 4294967295 /f'
            ]
            for cmd in cmds:
                subprocess.run(cmd.split(), capture_output=True, timeout=10)
            self.results.append({"success": True, "message": "GPU priority optimized for gaming"})
        except Exception as e:
            self.results.append({"success": False, "message": f"GPU priority failed: {e}"})

    def _disable_game_bar(self):
        try:
            cmds = [
                'reg add "HKCU\\Software\\Microsoft\\GameBar" /v UseNexusForGameBarEnabled /t REG_DWORD /d 0 /f',
                'reg add "HKCU\\Software\\Microsoft\\GameBar" /v ShowStartupPanel /t REG_DWORD /d 0 /f',
                'reg add "HKCU\\Software\\Microsoft\\GameBar" /v OpenAtGameHiveLaunch /t REG_DWORD /d 0 /f'
            ]
            for cmd in cmds:
                subprocess.run(cmd.split(), capture_output=True, timeout=10)
            self.results.append({"success": True, "message": "Game Bar overlay disabled"})
        except Exception as e:
            self.results.append({"success": False, "message": f"Game Bar failed: {e}"})

    def _disable_mouse_accel(self):
        try:
            cmds = [
                'reg add "HKCU\\Control Panel\\Mouse" /v MouseSpeed /t REG_SZ /d "0" /f',
                'reg add "HKCU\\Control Panel\\Mouse" /v MouseThreshold1 /t REG_SZ /d "0" /f',
                'reg add "HKCU\\Control Panel\\Mouse" /v MouseThreshold2 /t REG_SZ /d "0" /f'
            ]
            for cmd in cmds:
                subprocess.run(cmd.split(), capture_output=True, timeout=10)
            self.results.append({"success": True, "message": "Mouse acceleration disabled (raw input)"})
        except Exception as e:
            self.results.append({"success": False, "message": f"Mouse accel failed: {e}"})

    def _optimize_shader_cache(self):
        try:
            cmds = [
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\GraphicsDrivers" /v HwSchMode /t REG_DWORD /d 2 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\GraphicsDrivers" /v TdrDelay /t REG_DWORD /d 10 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\GraphicsDrivers" /v TdrDdiDelay /t REG_DWORD /d 10 /f'
            ]
            for cmd in cmds:
                subprocess.run(cmd.split(), capture_output=True, timeout=10)
            self.results.append({"success": True, "message": "GPU scheduler and shader cache optimized"})
        except Exception as e:
            self.results.append({"success": False, "message": f"Shader cache failed: {e}"})

    def _disable_visual_effects(self):
        try:
            cmds = [
                'reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\VisualEffects" /v VisualFXSetting /t REG_DWORD /d 2 /f',
                'reg add "HKCU\\Control Panel\\Desktop" /v UserPreferencesMask /t REG_BINARY /d 9012038010000000 /f'
            ]
            for cmd in cmds:
                subprocess.run(cmd.split(), capture_output=True, timeout=10)
            self.results.append({"success": True, "message": "Visual effects reduced for performance"})
        except Exception as e:
            self.results.append({"success": False, "message": f"Visual effects failed: {e}"})

    def _linux_gaming(self):
        try:
            settings = {"vm.swappiness": "10", "kernel.sched_autogroup_enabled": "0"}
            for k, v in settings.items():
                subprocess.run(["sudo", "sysctl", "-w", f"{k}={v}"], capture_output=True, timeout=5)
            self.results.append({"success": True, "message": "Linux gaming parameters optimized"})
        except Exception as e:
            self.results.append({"success": False, "message": f"Linux gaming failed: {e}"})

    def _macos_gaming(self):
        self.results.append({"success": True, "message": "macOS: Close background apps for best gaming performance"})
