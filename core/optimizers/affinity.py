"""AffinityOptimizer — SAFE version.

Removed:
- CPMINCORES 100 → Prevents core parking. Windows 11 manages this better.
- Win32PrioritySeparation 38 → Can cause system-wide responsiveness issues.
- IRQ8Priority → No effect since Windows XP.
- powercfg /setactive Ultimate Performance → Permanently changes user's power plan.
- wmic process setpriority 128 → REAL TIME priority can cause instability.
- PowerShell ProcessorAffinity → Affinity changes per-process should be user-initiated.
"""
import subprocess
import psutil

class AffinityOptimizer:
    name = "Safe System Optimization"

    def __init__(self, os_type):
        self.os_type = os_type
        self.results = []

    def run(self):
        self.results = []
        return self.results
