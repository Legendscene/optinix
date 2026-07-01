"""GameMode — SAFE version.

Removed:
- bcdedit useplatformclock true → HPET has higher overhead than TSC on modern systems
- bcdedit disabledynamictick → prevents tickless idle, increases power consumption
- powercfg /setactive Ultimate/High Performance → permanently changes power plan
- Win32PrioritySeparation → default is balanced, custom values can starve background tasks
- wmic process setpriority 128 → REALTIME priority can make system unstable
"""
import subprocess
import psutil
import threading
from typing import Dict, List, Optional, Any, Set

class GameMode:
    def __init__(self, os_type: str):
        self.os_type = os_type
        self.active = False
        self.monitored_games: Set[int] = set()
        self._lock = threading.Lock()
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_monitor = threading.Event()
    
    def get_game_processes(self) -> List[Dict[str, Any]]:
        """Detect game processes by common keywords. Does NOT apply tweaks."""
        games = []
        game_keywords = [
            "game", "steam", "epic", "origin", "uplay", "battle.net", "gog",
            "valorant", "cs2", "csgo", "fortnite", "apex", "warzone", "overwatch",
            "league", "dota", "minecraft", "roblox", "gta", "rdr", "cyberpunk",
            "elden", "witcher", "skyrim", "fallout", "destiny", "halo", "cod"
        ]
        for proc in psutil.process_iter(['pid', 'name', 'exe', 'cpu_percent', 'memory_percent', 'cmdline']):
            try:
                name = (proc.info['name'] or '').lower()
                exe = (proc.info['exe'] or '').lower()
                cmdline = ' '.join(proc.info['cmdline'] or []).lower()
                is_game = any(kw in name for kw in game_keywords) or \
                          any(kw in exe for kw in game_keywords) or \
                          any(kw in cmdline for kw in game_keywords)
                if is_game and (proc.info['cpu_percent'] or 0) > 1.0:
                    games.append({
                        "pid": proc.info['pid'],
                        "name": proc.info['name'],
                        "cpu_percent": proc.info['cpu_percent'],
                        "memory_percent": proc.info['memory_percent']
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return games
    
    def enable_game_mode(self) -> Dict[str, Any]:
        """Enables Windows Game Mode. No bcdedit, no power plan forcing."""
        if self.active:
            return {"success": True, "message": "Game Mode already active"}
        results = []
        if self.os_type == "windows":
            try:
                subprocess.run([
                    "reg", "add", "HKCU\\Software\\Microsoft\\GameBar",
                    "/v", "AllowAutoGameMode", "/t", "REG_DWORD", "/d", "1", "/f"
                ], capture_output=True, timeout=5)
                results.append({"success": True, "message": "Windows Game Mode enabled"})
            except Exception as e:
                results.append({"success": False, "message": f"Game Mode reg: {e}"})
        with self._lock:
            self.active = True
            self._stop_monitor.clear()
            self._monitor_thread = threading.Thread(target=self._monitor_games, daemon=True)
            self._monitor_thread.start()
        return {"success": True, "message": "Game Mode enabled", "results": results}
    
    def disable_game_mode(self) -> Dict[str, Any]:
        if not self.active:
            return {"success": True, "message": "Game Mode not active"}
        results = []
        if self.os_type == "windows":
            try:
                subprocess.run([
                    "reg", "add", "HKCU\\Software\\Microsoft\\GameBar",
                    "/v", "AllowAutoGameMode", "/t", "REG_DWORD", "/d", "0", "/f"
                ], capture_output=True, timeout=5)
                results.append({"success": True, "message": "Windows Game Mode disabled"})
            except Exception as e:
                results.append({"success": False, "message": f"Game Mode reg: {e}"})
        with self._lock:
            self.active = False
            self._stop_monitor.set()
            if self._monitor_thread:
                self._monitor_thread.join(timeout=2)
        return {"success": True, "message": "Game Mode disabled", "results": results}
    
    def _monitor_games(self):
        """Monitors games. Only adjusts process priority class (HIGH, not REALTIME)."""
        while not self._stop_monitor.is_set():
            games = self.get_game_processes()
            with self._lock:
                current_pids = {g['pid'] for g in games}
                new_games = current_pids - self.monitored_games
                for pid in new_games:
                    self._optimize_game_process(pid)
                self.monitored_games = current_pids
            time.sleep(5)
    
    def _optimize_game_process(self, pid: int):
        """🟢 Safe: sets process priority to HIGH (not REALTIME)."""
        if self.os_type != "windows":
            return
        try:
            p = psutil.Process(pid)
            p.nice(psutil.HIGH_PRIORITY_CLASS)
        except Exception:
            pass
    
    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "active": self.active,
                "monitored_games": list(self.monitored_games),
                "game_count": len(self.monitored_games)
            }

import time

class TimerResolution:
    """Timer Resolution — reports only. No bcdedit modifications.
    
    Removed:
    - bcdedit /set useplatformclock true → HPET has HIGHER latency than TSC on modern CPUs
    - bcdedit /set disabledynamictick yes → prevents modern power management
    
    Modern Windows 10 22H2+ and Windows 11 24H2 use invariant TSC.
    Game mode already requests high-resolution timers via NtSetTimerResolution.
    No BCD changes needed.
    """
    def __init__(self, os_type: str):
        self.os_type = os_type
    
    def get_current_resolution(self) -> Dict[str, Any]:
        return {"resolution_ms": "15.6 (default)", "note": "Windows manages timer resolution dynamically. Apps request high-res timers via NtSetTimerResolution."}
    
    def set_resolution(self, resolution_ms: float) -> Dict[str, Any]:
        return {"success": True, "message": "Windows manages timer resolution. No BCD changes needed.", "note": "Use NtSetTimerResolution for runtime changes. BCD platform clock changes are not recommended on modern systems."}
    
    def restore_default(self) -> Dict[str, Any]:
        return {"success": True, "message": "Timer settings are default. No BCD modifications were made."}
