import os
import platform
from dataclasses import dataclass, field
from typing import Dict, Any, List


@dataclass
class AppConfig:
    port: int = 5420
    debug: bool = False
    base_dir: str = field(default_factory=lambda: os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ui_dir: str = ""
    log_dir: str = ""
    log_level: str = "INFO"
    log_retention_days: int = 30
    rollback_dir: str = ""
    snapshot_limit: int = 50
    ws_gpu_cache_seconds: int = 10
    ws_emit_seconds: int = 3
    system_poll_seconds: int = 5
    gpu_poll_seconds: int = 10
    max_optimizer_timeout: int = 120
    os_type: str = ""
    cors_origins: str = "*"

    def __post_init__(self):
        if not self.ui_dir:
            d = os.path.join(self.base_dir, "desktop", "dist")
            self.ui_dir = d if os.path.isdir(d) else os.path.join(self.base_dir, "ui")
        if not self.log_dir:
            self.log_dir = os.path.join(os.environ.get("TEMP", self.base_dir), "optinix_logs")
        if not self.rollback_dir:
            self.rollback_dir = os.path.join(os.environ.get("TEMP", self.base_dir), "optinix_rollback")
        if not self.os_type:
            self.os_type = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(platform.system(), "unknown")
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.rollback_dir, exist_ok=True)


CONFIG = AppConfig()
