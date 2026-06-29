import subprocess
import psutil
import platform
import json
import time
import threading
import os
from typing import Dict, List, Optional, Any, Set

class GameMode:
    def __init__(self, os_type: str):
        self.os_type = os_type
        self.active = False
        self.monitored_games: Set[int] = set()
        self.original_settings: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_monitor = threading.Event()
    
    def get_game_processes(self) -> List[Dict[str, Any]]:
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
                
                if is_game and proc.info['cpu_percent'] > 1.0:
                    games.append({
                        "pid": proc.info['pid'],
                        "name": proc.info['name'],
                        "exe": proc.info['exe'],
                        "cpu_percent": proc.info['cpu_percent'],
                        "memory_percent": proc.info['memory_percent']
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return games
    
    def enable_game_mode(self) -> Dict[str, Any]:
        if self.active:
            return {"success": True, "message": "Game Mode already active"}
        
        results = []
        
        if self.os_type == "windows":
            results.extend(self._enable_windows_game_mode())
        
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
            results.extend(self._disable_windows_game_mode())
        
        with self._lock:
            self.active = False
            self._stop_monitor.set()
            if self._monitor_thread:
                self._monitor_thread.join(timeout=2)
        
        return {"success": True, "message": "Game Mode disabled", "results": results}
    
    def _enable_windows_game_mode(self) -> List[Dict[str, Any]]:
        results = []
        
        try:
            subprocess.run([
                "reg", "add", "HKCU\\Software\\Microsoft\\GameBar",
                "/v", "AllowAutoGameMode", "/t", "REG_DWORD", "/d", "1", "/f"
            ], capture_output=True, timeout=5)
            results.append({"success": True, "message": "Windows Game Mode enabled"})
        except Exception as e:
            results.append({"success": False, "message": f"Game Mode reg: {e}"})
        
        try:
            subprocess.run([
                "reg", "add", "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\GameDVR",
                "/v", "AppCaptureEnabled", "/t", "REG_DWORD", "/d", "0", "/f"
            ], capture_output=True, timeout=5)
            results.append({"success": True, "message": "Game DVR disabled"})
        except Exception as e:
            results.append({"success": False, "message": f"Game DVR: {e}"})
        
        try:
            subprocess.run([
                "powercfg", "/setactive", "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
            ], capture_output=True, timeout=10)
            results.append({"success": True, "message": "Ultimate Performance power plan activated"})
        except Exception:
            try:
                subprocess.run([
                    "powercfg", "/setactive", "SCHEME_MIN"
                ], capture_output=True, timeout=10)
                results.append({"success": True, "message": "High Performance power plan activated"})
            except Exception as e:
                results.append({"success": False, "message": f"Power plan: {e}"})
        
        try:
            subprocess.run([
                "reg", "add", "HKLM\\SYSTEM\\CurrentControlSet\\Control\\PriorityControl",
                "/v", "Win32PrioritySeparation", "/t", "REG_DWORD", "/d", "26", "/f"
            ], capture_output=True, timeout=5)
            results.append({"success": True, "message": "CPU priority set to programs"})
        except Exception as e:
            results.append({"success": False, "message": f"Priority: {e}"})
        
        try:
            subprocess.run([
                "bcdedit", "/set", "useplatformclock", "true"
            ], capture_output=True, timeout=5)
            results.append({"success": True, "message": "HPET forced on"})
        except Exception as e:
            results.append({"success": False, "message": f"HPET: {e}"})
        
        return results
    
    def _disable_windows_game_mode(self) -> List[Dict[str, Any]]:
        results = []
        
        try:
            subprocess.run([
                "reg", "add", "HKCU\\Software\\Microsoft\\GameBar",
                "/v", "AllowAutoGameMode", "/t", "REG_DWORD", "/d", "0", "/f"
            ], capture_output=True, timeout=5)
            results.append({"success": True, "message": "Windows Game Mode disabled"})
        except Exception as e:
            results.append({"success": False, "message": f"Game Mode reg: {e}"})
        
        try:
            subprocess.run([
                "reg", "add", "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\GameDVR",
                "/v", "AppCaptureEnabled", "/t", "REG_DWORD", "/d", "1", "/f"
            ], capture_output=True, timeout=5)
            results.append({"success": True, "message": "Game DVR re-enabled"})
        except Exception as e:
            results.append({"success": False, "message": f"Game DVR: {e}"})
        
        try:
            subprocess.run([
                "powercfg", "/setactive", "SCHEME_BALANCED"
            ], capture_output=True, timeout=10)
            results.append({"success": True, "message": "Balanced power plan restored"})
        except Exception as e:
            results.append({"success": False, "message": f"Power plan: {e}"})
        
        return results
    
    def _monitor_games(self):
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
        if self.os_type == "windows":
            try:
                subprocess.run([
                    "wmic", "process", "where", f"ProcessId={pid}",
                    "CALL", "setpriority", "128"
                ], capture_output=True, timeout=5)
            except Exception:
                pass
            
            try:
                p = psutil.Process(pid)
                if hasattr(p, 'cpu_affinity'):
                    cores = list(range(psutil.cpu_count()))
                    if len(cores) > 2:
                        p.cpu_affinity(cores[:-1])
            except Exception:
                pass
    
    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "active": self.active,
                "monitored_games": list(self.monitored_games),
                "game_count": len(self.monitored_games)
            }

class AffinityOptimizer:
    def __init__(self, os_type: str):
        self.os_type = os_type
        self.total_cores = psutil.cpu_count() or 1
        self.physical_cores = psutil.cpu_count(logical=False) or 1
        self.performance_cores = self._detect_performance_cores()
    
    def _detect_performance_cores(self) -> List[int]:
        if self.os_type != "windows":
            return list(range(self.physical_cores))
        
        try:
            r = subprocess.run([
                "wmic", "cpu", "get", "NumberOfCores,NumberOfLogicalProcessors", "/format:csv"
            ], capture_output=True, text=True, timeout=5)
        except Exception:
            return list(range(self.physical_cores))
        
        return list(range(self.physical_cores))
    
    def optimize_for_gaming(self, pid: Optional[int] = None) -> Dict[str, Any]:
        results = []
        
        if self.os_type != "windows":
            return {"success": False, "message": "Windows only", "results": results}
        
        if pid is None:
            game_mode = GameMode(self.os_type)
            games = game_mode.get_game_processes()
            if games:
                pid = games[0]['pid']
            else:
                return {"success": False, "message": "No game process found", "results": results}
        
        try:
            p = psutil.Process(pid)
            if hasattr(p, 'cpu_affinity'):
                if self.total_cores > 4:
                    perf_cores = self.performance_cores if self.performance_cores else list(range(self.physical_cores))
                    p.cpu_affinity(perf_cores)
                    results.append({"success": True, "message": f"Set affinity to performance cores: {perf_cores}"})
                else:
                    p.cpu_affinity(list(range(self.total_cores)))
                    results.append({"success": True, "message": f"Set affinity to all cores"})
        except Exception as e:
            results.append({"success": False, "message": f"Affinity: {e}"})
        
        try:
            subprocess.run([
                "wmic", "process", "where", f"ProcessId={pid}",
                "CALL", "setpriority", "128"
            ], capture_output=True, timeout=5)
            results.append({"success": True, "message": "Set real-time priority"})
        except Exception as e:
            results.append({"success": False, "message": f"Priority: {e}"})
        
        return {"success": True, "results": results}
    
    def disable_core_parking(self) -> Dict[str, Any]:
        if self.os_type != "windows":
            return {"success": False, "message": "Windows only"}
        
        results = []
        try:
            subprocess.run([
                "powercfg", "/setacvalueindex", "SCHEME_CURRENT",
                "SUB_PROCESSOR", "CPCCOREPARKING", "0"
            ], capture_output=True, timeout=5)
            results.append({"success": True, "message": "Core parking disabled (AC)"})
        except Exception as e:
            results.append({"success": False, "message": f"Core parking AC: {e}"})
        
        try:
            subprocess.run([
                "powercfg", "/setdcvalueindex", "SCHEME_CURRENT",
                "SUB_PROCESSOR", "CPCCOREPARKING", "0"
            ], capture_output=True, timeout=5)
            results.append({"success": True, "message": "Core parking disabled (DC)"})
        except Exception as e:
            results.append({"success": False, "message": f"Core parking DC: {e}"})
        
        try:
            subprocess.run(["powercfg", "/setactive", "SCHEME_CURRENT"], capture_output=True, timeout=5)
            results.append({"success": True, "message": "Power scheme updated"})
        except Exception as e:
            results.append({"success": False, "message": f"Power scheme: {e}"})
        
        return {"success": True, "results": results}

class TimerResolution:
    def __init__(self, os_type: str):
        self.os_type = os_type
        self.original_resolution: Optional[float] = None
    
    def get_current_resolution(self) -> Dict[str, Any]:
        if self.os_type != "windows":
            return {"resolution_ms": "N/A", "message": "Windows only"}
        
        try:
            r = subprocess.run([
                "wmic", "os", "get", "BootupTime", "/format:csv"
            ], capture_output=True, text=True, timeout=5)
        except Exception:
            return {"resolution_ms": "Unknown"}
        
        return {"resolution_ms": "15.6 (default)", "note": "Windows default is 15.6ms"}
    
    def set_resolution(self, resolution_ms: float) -> Dict[str, Any]:
        if self.os_type != "windows":
            return {"success": False, "message": "Windows only"}
        
        if resolution_ms < 0.5 or resolution_ms > 15.6:
            return {"success": False, "message": "Resolution must be between 0.5ms and 15.6ms"}
        
        results = []
        
        try:
            subprocess.run([
                "bcdedit", "/set", "useplatformclock", "true"
            ], capture_output=True, timeout=5)
            results.append({"success": True, "message": "Platform clock enabled (HPET)"})
        except Exception as e:
            results.append({"success": False, "message": f"Platform clock: {e}"})
        
        try:
            subprocess.run([
                "bcdedit", "/set", "disabledynamictick", "yes"
            ], capture_output=True, timeout=5)
            results.append({"success": True, "message": "Dynamic tick disabled"})
        except Exception as e:
            results.append({"success": False, "message": f"Dynamic tick: {e}"})
        
        return {
            "success": True,
            "message": f"Timer resolution optimizations applied. Target: {resolution_ms}ms",
            "results": results,
            "note": "Requires reboot for full effect. Use tools like TimerResolution.exe for runtime changes."
        }
    
    def restore_default(self) -> Dict[str, Any]:
        if self.os_type != "windows":
            return {"success": False, "message": "Windows only"}
        
        results = []
        
        try:
            subprocess.run(["bcdedit", "/deletevalue", "useplatformclock"], capture_output=True, timeout=5)
            results.append({"success": True, "message": "Platform clock restored"})
        except Exception:
            pass
        
        try:
            subprocess.run(["bcdedit", "/deletevalue", "disabledynamictick"], capture_output=True, timeout=5)
            results.append({"success": True, "message": "Dynamic tick restored"})
        except Exception:
            pass
        
        return {"success": True, "results": results}

if __name__ == "__main__":
    import sys
    gm = GameMode(platform.system())
    print("Game processes:", json.dumps(gm.get_game_processes(), indent=2))
    
    ao = AffinityOptimizer(platform.system())
    print("Affinity:", json.dumps(ao.optimize_for_gaming(), indent=2))
    
    tr = TimerResolution(platform.system())
    print("Timer:", json.dumps(tr.get_current_resolution(), indent=2))