import subprocess
import os


class LinuxPlatform:
    name = "Linux"

    def __init__(self):
        self.distro = self._detect_distro()

    def _detect_distro(self):
        try:
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("ID="):
                        return line.strip().split("=")[1].strip('"')
        except Exception:
            return "unknown"

    def get_services(self):
        try:
            r = subprocess.run(
                ["systemctl", "list-units", "--type=service", "--state=running", "--no-pager"],
                capture_output=True, text=True, timeout=10
            )
            services = []
            for line in r.stdout.split("\n")[1:]:
                if ".service" in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        services.append({"name": parts[0], "active": parts[2], "sub": parts[3]})
            return services
        except Exception:
            return []

    def disable_service(self, service_name):
        try:
            subprocess.run(["sudo", "systemctl", "stop", service_name], capture_output=True, timeout=10)
            subprocess.run(["sudo", "systemctl", "disable", service_name], capture_output=True, timeout=10)
            return True
        except Exception:
            return False

    def get_package_manager(self):
        managers = {
            "ubuntu": "apt", "debian": "apt", "fedora": "dnf",
            "arch": "pacman", "manjaro": "pacman", "centos": "yum"
        }
        return managers.get(self.distro, "unknown")
