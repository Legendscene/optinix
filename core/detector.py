import platform
import sys


class OSDetector:
    def __init__(self):
        self.system = platform.system()
        self.release = platform.release()
        self.version = platform.version()
        self.machine = platform.machine()
        self.processor = platform.processor()

    def detect(self):
        return {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(self.system, "unknown")

    def get_info(self):
        return {
            "os": self.detect(),
            "os_name": self.system,
            "release": self.release,
            "version": self.version,
            "machine": self.machine,
            "processor": self.processor,
            "python": sys.version
        }
