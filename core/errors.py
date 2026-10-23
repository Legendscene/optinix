from typing import Dict, Any, Optional


class OptinixError(Exception):
    code = 500
    message = "Internal error"

    def __init__(self, message: Optional[str] = None, code: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        self.message = message or self.message
        self.code = code or self.code
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {"error": self.message, "code": self.code, **self.details}


class ConfigError(OptinixError):
    code = 500
    message = "Configuration error"


class AdminRequiredError(OptinixError):
    code = 403
    message = "Administrator privileges required"


class CompatibilityError(OptinixError):
    code = 400
    message = "Optimization not compatible with this system"


class SnapshotError(OptinixError):
    code = 500
    message = "Failed to create or restore snapshot"


class OptimizerError(OptinixError):
    code = 500
    message = "Optimization failed"


class TimeoutError(OptinixError):
    code = 504
    message = "Operation timed out"


class RegistryError(OptinixError):
    code = 500
    message = "Registry operation failed"


def handle_error(e: Exception) -> Dict[str, Any]:
    if isinstance(e, OptinixError):
        return e.to_dict()
    return {"error": str(e), "code": 500}
