import subprocess


class PeripheralOptimizer:
    name = "Peripheral & USB Optimization"

    def __init__(self, os_type):
        self.os_type = os_type
        self.results = []

    def run(self):
        self.results = []
        if self.os_type == "windows":
            self._optimize_mouse()
            self._optimize_usb()
            self._optimize_keyboard()
            self._disable_filter_keys()
            self._optimize_nvme()
        return self.results

    def _optimize_mouse(self):
        try:
            cmds = [
                'reg add "HKCU\\Control Panel\\Mouse" /v MouseSpeed /t REG_SZ /d "0" /f',
                'reg add "HKCU\\Control Panel\\Mouse" /v MouseThreshold1 /t REG_SZ /d "0" /f',
                'reg add "HKCU\\Control Panel\\Mouse" /v MouseThreshold2 /t REG_SZ /d "0" /f',
                'reg add "HKCU\\Control Panel\\Mouse" /v MouseSensitivity /t REG_SZ /d "10" /f',
                'reg add "HKCU\\Control Panel\\Mouse" /v SmoothMouseXCurve /t REG_BINARY /d 0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000 /f',
                'reg add "HKCU\\Control Panel\\Mouse" /v SmoothMouseYCurve /t REG_BINARY /d 0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000 /f',
            ]
            for cmd in cmds:
                subprocess.run(cmd, capture_output=True, timeout=10, shell=True)
            self.results.append({"success": True, "message": "Mouse: acceleration off, precision curves zeroed"})
        except Exception as e:
            self.results.append({"success": False, "message": f"Mouse optimization failed: {e}"})

    def _optimize_usb(self):
        try:
            cmds = [
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\USB" /v DisableSelectiveSuspend /t REG_DWORD /d 1 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\USB" /v SelectiveSuspendEnabled /t REG_DWORD /d 0 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\USB" /v DisableResetOnResume /t REG_DWORD /d 1 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\USB" /v DisableSelectiveSuspend /t REG_DWORD /d 1 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Enum\\USB" /v DisableSelectiveSuspend /t REG_DWORD /d 1 /f',
            ]
            for cmd in cmds:
                subprocess.run(cmd, capture_output=True, timeout=10, shell=True)

            subprocess.run(
                ["powercfg", "/setacvalueindex", "SCHEME_CURRENT",
                 "USB", "USB_SETTING", "0"],
                capture_output=True, timeout=10
            )
            subprocess.run(
                ["powercfg", "/setactive", "SCHEME_CURRENT"],
                capture_output=True, timeout=10
            )
            self.results.append({"success": True, "message": "USB: selective suspend disabled, no power saving"})
        except Exception as e:
            self.results.append({"success": False, "message": f"USB optimization failed: {e}"})

    def _optimize_keyboard(self):
        try:
            cmds = [
                'reg add "HKCU\\Control Panel\\Accessibility\\Keyboard Response" /v AutoRepeatDelay /t REG_SZ /d "0" /f',
                'reg add "HKCU\\Control Panel\\Accessibility\\Keyboard Response" /v AutoRepeatRate /t REG_SZ /d "0" /f',
                'reg add "HKCU\\Control Panel\\Accessibility\\Keyboard Response" /v DelayBeforeAcceptance /t REG_SZ /d "0" /f',
                'reg add "HKCU\\Control Panel\\Accessibility\\Keyboard Response" /v Flags /t REG_SZ /d "120" /f',
                'reg add "HKCU\\Control Panel\\Accessibility\\ToggleKeys" /v Flags /t REG_SZ /d "58" /f',
            ]
            for cmd in cmds:
                subprocess.run(cmd, capture_output=True, timeout=10, shell=True)
            self.results.append({"success": True, "message": "Keyboard: minimum delay, fastest repeat rate"})
        except Exception as e:
            self.results.append({"success": False, "message": f"Keyboard optimization failed: {e}"})

    def _disable_filter_keys(self):
        try:
            cmds = [
                'reg add "HKCU\\Control Panel\\Accessibility\\StickyKeys" /v Flags /t REG_SZ /d "58" /f',
                'reg add "HKCU\\Control Panel\\Accessibility\\FilterKeys" /v Flags /t REG_SZ /d "58" /f',
                'reg add "HKCU\\Control Panel\\Accessibility\\ToggleKeys" /v Flags /t REG_SZ /d "58" /f',
            ]
            for cmd in cmds:
                subprocess.run(cmd, capture_output=True, timeout=10, shell=True)
            self.results.append({"success": True, "message": "Filter Keys, Sticky Keys, Toggle Keys disabled"})
        except Exception as e:
            self.results.append({"success": False, "message": f"Filter keys failed: {e}"})

    def _optimize_nvme(self):
        try:
            cmds = [
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Memory Management\\PrefetchParameters" /v EnablePrefetcher /t REG_DWORD /d 0 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Memory Management\\PrefetchParameters" /v EnableSuperfetch /t REG_DWORD /d 0 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\stornvme\\Parameters\\Device" /v EnableMSI /t REG_DWORD /d 1 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\stornvme\\Parameters\\Device" /v QueueDepth /t REG_DWORD /d 256 /f',
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\stornvme\\Parameters\\Device" /v ThreadPriority /t REG_DWORD /d 7 /f',
            ]
            for cmd in cmds:
                subprocess.run(cmd, capture_output=True, timeout=10, shell=True)
            self.results.append({"success": True, "message": "NVMe: MSI enabled, queue depth 256, thread priority 7"})
        except Exception as e:
            self.results.append({"success": False, "message": f"NVMe optimization failed: {e}"})
