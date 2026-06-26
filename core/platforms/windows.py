import subprocess
import os


class WindowsPlatform:
    name = "Windows"

    def get_registry_value(self, key_path, value_name):
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path)
            value, _ = winreg.QueryValueEx(key, value_name)
            winreg.CloseKey(key)
            return value
        except Exception:
            return None

    def set_registry_value(self, key_path, value_name, value):
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, value_name, 0, winreg.REG_DWORD, value)
            winreg.CloseKey(key)
            return True
        except Exception:
            return False

    def disable_service(self, service_name):
        try:
            subprocess.run(
                ["powershell", "-Command",
                 f"Stop-Service -Name '{service_name}' -Force -EA SilentlyContinue; "
                 f"Set-Service -Name '{service_name}' -StartupType Disabled -EA SilentlyContinue"],
                capture_output=True, timeout=15
            )
            return True
        except Exception:
            return False

    def get_installed_apps(self):
        try:
            r = subprocess.run(
                ["powershell", "-Command",
                 "Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* | "
                 "Select-Object DisplayName, DisplayVersion, Publisher | ConvertTo-Json"],
                capture_output=True, text=True, timeout=30
            )
            import json
            return json.loads(r.stdout) if r.stdout.strip() else []
        except Exception:
            return []
