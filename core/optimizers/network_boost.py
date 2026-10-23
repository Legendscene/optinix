import subprocess
from typing import Dict, Any, List
from core.base import OptimizerBase, OPTIMIZER_CATEGORY_ADVANCED
from core.config import CONFIG
from core.network_tuner import NetworkTuner
from core.network_priority import NetworkPriority, BufferBloatControl


class NetworkBoostOptimizer(OptimizerBase):
    name = "Network Boost Optimizer"
    description = "Advanced network boost with bufferbloat control, BBR2, QoS, and Nagle's algorithm disable"
    category = OPTIMIZER_CATEGORY_ADVANCED
    benefit = "Lower ping, reduced bufferbloat, optimized traffic prioritization"
    risks = "Registry changes to TCP parameters; admin rights required"
    admin_required = True
    requirements = {}

    def __init__(self):
        super().__init__()
        self.os_type = CONFIG.os_type

    def run(self) -> List[Dict[str, Any]]:
        self.results = []
        self.logger.info("Starting network boost optimization")

        tuner = NetworkTuner(self.os_type)
        priority = NetworkPriority(self.os_type)
        bbc = BufferBloatControl(self.os_type)

        adapters = tuner.get_adapters()
        if not adapters:
            adapters = priority.get_adapters()

        adapter_count = len(adapters)
        self.add_result(True, f"Found {adapter_count} network adapter(s)", adapters=adapter_count)

        self._apply_bufferbloat_preset(bbc)
        self._set_bbr2(tuner)
        self._enable_qos(priority)
        self._disable_nagle()

        self.add_result(True, f"Tuned {adapter_count} adapter(s)", tuned=adapter_count)

        return [r.to_dict() for r in self.results]

    def _apply_bufferbloat_preset(self, bbc: BufferBloatControl):
        try:
            result = bbc.apply_preset("low_latency")
            if result.get("success"):
                self.add_result(True, "Bufferbloat: low-latency preset applied")
            else:
                self.add_result(False, result.get("message", "Bufferbloat preset failed"))
        except Exception as e:
            self.logger.error(f"Bufferbloat preset failed: {e}")
            self.add_result(False, f"Bufferbloat preset failed: {e}")

    def _set_bbr2(self, tuner: NetworkTuner):
        try:
            subprocess.run(
                "netsh int tcp set supplemental Internet congestionprovider=bbr2",
                capture_output=True, timeout=10, shell=True
            )
            self.add_result(True, "BBR2 congestion provider enabled")
        except Exception as e:
            self.logger.error(f"BBR2 failed: {e}")
            self.add_result(False, f"BBR2 failed: {e}")

    def _enable_qos(self, priority: NetworkPriority):
        try:
            result = priority.enable_qos()
            if result.get("success"):
                self.add_result(True, "QoS enabled")
            else:
                self.add_result(False, result.get("message", "QoS enable failed"))
        except Exception as e:
            self.logger.error(f"QoS failed: {e}")
            self.add_result(False, f"QoS failed: {e}")

    def _disable_nagle(self):
        try:
            subprocess.run(
                'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters" '
                "/v TCPNoDelay /t REG_DWORD /d 1 /f",
                capture_output=True, timeout=10, shell=True
            )
            self.add_result(True, "Nagle's algorithm disabled (TCPNoDelay=1)")
        except Exception as e:
            self.logger.error(f"TCPNoDelay failed: {e}")
            self.add_result(False, f"TCPNoDelay failed: {e}")
