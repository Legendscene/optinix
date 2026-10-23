"""
Game Profiles — Per-game optimization profiles
Similar to HyperTune's game-specific optimization system.
"""
import json
import os
import platform
import subprocess
from typing import Dict, Any, List, Optional
from .logger import get_logger
from .config import CONFIG

logger = get_logger("game_profiles")

# Pre-built profiles for popular games
BUILTIN_PROFILES: Dict[str, Dict[str, Any]] = {
    "valorant": {
        "name": "Valorant",
        "process_keywords": ["valorant", "val-client", "val-vg"],
        "priority": "high",
        "gpu_priority": True,
        "game_mode": True,
        "dvr_off": True,
        "fullscreen_opt": False,
        "mouse_accel": False,
        "shader_cache": True,
        "visual_effects": "off",
        "power_plan": "ultimate",
        "network_priority": True,
        "description": "Optimized for competitive FPS — max frames, min input lag"
    },
    "cs2": {
        "name": "Counter-Strike 2",
        "process_keywords": ["cs2", "cs:go", "csgo"],
        "priority": "high",
        "gpu_priority": True,
        "game_mode": True,
        "dvr_off": True,
        "fullscreen_opt": False,
        "mouse_accel": False,
        "shader_cache": True,
        "visual_effects": "off",
        "power_plan": "ultimate",
        "network_priority": True,
        "description": "Low latency competitive profile"
    },
    "fortnite": {
        "name": "Fortnite",
        "process_keywords": ["fortniteclient", "fortnite"],
        "priority": "high",
        "gpu_priority": True,
        "game_mode": True,
        "dvr_off": True,
        "fullscreen_opt": False,
        "mouse_accel": False,
        "shader_cache": True,
        "visual_effects": "minimal",
        "power_plan": "high",
        "network_priority": True,
        "description": "High FPS for building/editing responsiveness"
    },
    "apex": {
        "name": "Apex Legends",
        "process_keywords": ["r5apex", "apex"],
        "priority": "high",
        "gpu_priority": True,
        "game_mode": True,
        "dvr_off": True,
        "fullscreen_opt": False,
        "mouse_accel": False,
        "shader_cache": True,
        "visual_effects": "off",
        "power_plan": "ultimate",
        "network_priority": True,
        "description": "Competitive BR profile"
    },
    "warzone": {
        "name": "Call of Duty: Warzone",
        "process_keywords": ["modernwarfare", "warzone", "cod"],
        "priority": "high",
        "gpu_priority": True,
        "game_mode": True,
        "dvr_off": True,
        "fullscreen_opt": False,
        "mouse_accel": False,
        "shader_cache": True,
        "visual_effects": "minimal",
        "power_plan": "ultimate",
        "network_priority": True,
        "description": "High FPS for fast-paced combat"
    },
    "overwatch2": {
        "name": "Overwatch 2",
        "process_keywords": ["overwatch", "ow2"],
        "priority": "high",
        "gpu_priority": True,
        "game_mode": True,
        "dvr_off": True,
        "fullscreen_opt": False,
        "mouse_accel": False,
        "shader_cache": True,
        "visual_effects": "off",
        "power_plan": "high",
        "network_priority": True,
        "description": "Smooth gameplay with consistent frame pacing"
    },
    "pubg": {
        "name": "PUBG: Battlegrounds",
        "process_keywords": ["tslgame", "pubg"],
        "priority": "high",
        "gpu_priority": True,
        "game_mode": True,
        "dvr_off": True,
        "fullscreen_opt": False,
        "mouse_accel": False,
        "shader_cache": True,
        "visual_effects": "minimal",
        "power_plan": "ultimate",
        "network_priority": True,
        "description": "Maximize FPS in large maps"
    },
    "rust": {
        "name": "Rust",
        "process_keywords": ["rustclient", "rust"],
        "priority": "high",
        "gpu_priority": True,
        "game_mode": True,
        "dvr_off": True,
        "fullscreen_opt": False,
        "mouse_accel": False,
        "shader_cache": True,
        "visual_effects": "minimal",
        "power_plan": "high",
        "network_priority": True,
        "description": "CPU-heavy game — max performance"
    },
    "minecraft": {
        "name": "Minecraft",
        "process_keywords": ["minecraft", "javaw"],
        "priority": "high",
        "gpu_priority": True,
        "game_mode": True,
        "dvr_off": True,
        "fullscreen_opt": False,
        "mouse_accel": False,
        "shader_cache": True,
        "visual_effects": "off",
        "power_plan": "high",
        "network_priority": False,
        "description": "Java CPU-bound optimization"
    },
    "gta5": {
        "name": "Grand Theft Auto V",
        "process_keywords": ["gta5", "gtav"],
        "priority": "high",
        "gpu_priority": True,
        "game_mode": True,
        "dvr_off": True,
        "fullscreen_opt": False,
        "mouse_accel": False,
        "shader_cache": True,
        "visual_effects": "minimal",
        "power_plan": "ultimate",
        "network_priority": True,
        "description": "Open world performance profile"
    },
    "eldenring": {
        "name": "Elden Ring",
        "process_keywords": ["eldenring", "elden ring"],
        "priority": "high",
        "gpu_priority": True,
        "game_mode": True,
        "dvr_off": True,
        "fullscreen_opt": True,
        "mouse_accel": False,
        "shader_cache": True,
        "visual_effects": "minimal",
        "power_plan": "ultimate",
        "network_priority": False,
        "description": "Fix stuttering, smooth frame pacing"
    },
    "cyberpunk": {
        "name": "Cyberpunk 2077",
        "process_keywords": ["cyberpunk2077"],
        "priority": "high",
        "gpu_priority": True,
        "game_mode": True,
        "dvr_off": True,
        "fullscreen_opt": True,
        "mouse_accel": False,
        "shader_cache": True,
        "visual_effects": "minimal",
        "power_plan": "ultimate",
        "network_priority": False,
        "description": "GPU-heavy — max GPU scheduling"
    },
    "league": {
        "name": "League of Legends",
        "process_keywords": ["league of legends", "lol"],
        "priority": "high",
        "gpu_priority": True,
        "game_mode": True,
        "dvr_off": True,
        "fullscreen_opt": False,
        "mouse_accel": False,
        "shader_cache": True,
        "visual_effects": "off",
        "power_plan": "high",
        "network_priority": True,
        "description": "Low latency MOBA profile"
    },
    "dota2": {
        "name": "Dota 2",
        "process_keywords": ["dota2", "dota 2"],
        "priority": "high",
        "gpu_priority": True,
        "game_mode": True,
        "dvr_off": True,
        "fullscreen_opt": False,
        "mouse_accel": False,
        "shader_cache": True,
        "visual_effects": "off",
        "power_plan": "high",
        "network_priority": True,
        "description": "Responsive teamfight performance"
    },
    "rainbow6": {
        "name": "Rainbow Six Siege",
        "process_keywords": ["rainbow6", "r6"],
        "priority": "high",
        "gpu_priority": True,
        "game_mode": True,
        "dvr_off": True,
        "fullscreen_opt": False,
        "mouse_accel": False,
        "shader_cache": True,
        "visual_effects": "off",
        "power_plan": "ultimate",
        "network_priority": True,
        "description": "Tactical FPS — minimal input lag"
    }
}


class GameProfiles:
    """Manages per-game optimization profiles."""

    def __init__(self):
        self.profiles_dir = os.path.join(CONFIG.base_dir, "data", "game_profiles")
        os.makedirs(self.profiles_dir, exist_ok=True)
        self._load_custom_profiles()

    def _load_custom_profiles(self):
        """Load custom profiles from disk."""
        self.custom_profiles = {}
        for f in os.listdir(self.profiles_dir):
            if f.endswith(".json"):
                try:
                    with open(os.path.join(self.profiles_dir, f), 'r') as fp:
                        data = json.load(fp)
                        key = f.replace(".json", "")
                        self.custom_profiles[key] = data
                except Exception as e:
                    logger.warning(f"Failed to load profile {f}: {e}")

    def get_all_profiles(self) -> List[Dict[str, Any]]:
        """Return all available profiles (built-in + custom)."""
        profiles = []
        for key, profile in BUILTIN_PROFILES.items():
            profiles.append({
                "id": key,
                "name": profile["name"],
                "description": profile["description"],
                "builtin": True
            })
        for key, profile in self.custom_profiles.items():
            profiles.append({
                "id": key,
                "name": profile.get("name", key),
                "description": profile.get("description", "Custom profile"),
                "builtin": False
            })
        return profiles

    def get_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific profile by ID."""
        if profile_id in BUILTIN_PROFILES:
            return BUILTIN_PROFILES[profile_id]
        return self.custom_profiles.get(profile_id)

    def save_custom_profile(self, profile_id: str, profile: Dict[str, Any]) -> bool:
        """Save a custom profile."""
        try:
            path = os.path.join(self.profiles_dir, f"{profile_id}.json")
            with open(path, 'w') as f:
                json.dump(profile, f, indent=2)
            self.custom_profiles[profile_id] = profile
            return True
        except Exception as e:
            logger.error(f"Failed to save profile: {e}")
            return False

    def delete_custom_profile(self, profile_id: str) -> bool:
        """Delete a custom profile."""
        if profile_id in BUILTIN_PROFILES:
            return False
        try:
            path = os.path.join(self.profiles_dir, f"{profile_id}.json")
            if os.path.exists(path):
                os.remove(path)
            self.custom_profiles.pop(profile_id, None)
            return True
        except Exception as e:
            logger.error(f"Failed to delete profile: {e}")
            return False

    def detect_running_game(self) -> Optional[str]:
        """Detect if a known game is currently running."""
        try:
            import psutil
            for proc in psutil.process_iter(['name', 'exe', 'cmdline']):
                try:
                    info = proc.info
                    name = (info.get('name') or '').lower()
                    exe = (info.get('exe') or '').lower()
                    cmdline = ' '.join(info.get('cmdline') or []).lower()

                    for game_id, profile in BUILTIN_PROFILES.items():
                        for keyword in profile.get('process_keywords', []):
                            kw = keyword.lower()
                            if kw in name or kw in exe or kw in cmdline:
                                return game_id
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            logger.error(f"Game detection failed: {e}")
        return None

    # Registry values a profile may change — snapshotted BEFORE any write so
    # Revert restores the user's actual previous values, not guessed defaults.
    _TWEAKED_VALUES = [
        (r"HKCU\Software\Microsoft\GameBar", "AllowAutoGameMode"),
        (r"HKCU\System\GameConfigStore", "GameDVR_Enabled"),
        (r"HKLM\SOFTWARE\Policies\Microsoft\Windows\GameDVR", "AllowGameDVR"),
        (r"HKCU\System\GameConfigStore", "GameDVR_FSEBehaviorMode"),
        (r"HKCU\Control Panel\Mouse", "MouseSpeed"),
        (r"HKCU\Control Panel\Mouse", "MouseThreshold1"),
        (r"HKCU\Control Panel\Mouse", "MouseThreshold2"),
        (r"HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers", "HwSchMode"),
        (r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects", "VisualFXSetting"),
        (r"HKLM\SOFTWARE\Policies\Microsoft\Windows\Psched", "NonBestEffortLimit"),
    ]

    def _snapshot_before_apply(self) -> Optional[str]:
        """Capture current values + active power plan into the rollback store.

        Returns the snapshot file path, or None when snapshotting FAILED.
        caller MUST refuse to continue on None: applying changes without a
        saved prior state would leave the user with only default-value
        Revert, which is not the user's real previous state."""
        try:
            from .rollback_engine import RollbackEngine
            re_ = RollbackEngine()
            for key, name in self._TWEAKED_VALUES:
                re_.snapshot_registry(key, name)
            re_.snapshot_power_plan()
            return re_.save_snapshot()
        except Exception as e:  # noqa: BLE001 - surfaced to the apply caller
            self._last_snapshot_error = str(e)
            logger.warning(f"Pre-apply snapshot failed; apply was NOT continued: {e}")
            return None

    def apply_profile(self, profile_id: str) -> List[Dict[str, Any]]:
        """Apply a game profile's optimizations."""
        profile = self.get_profile(profile_id)
        if not profile:
            return [{"success": False, "message": f"Profile '{profile_id}' not found"}]

        results = []
        system = platform.system().lower()

        if system != "windows":
            return [{"success": False, "message": "Game profiles currently only support Windows"}]

        # Snapshot BEFORE any write so Revert can restore the user's real
        # previous values. A failed snapshot BLOCKS the apply: changing
        # system settings without a saved prior state would leave Revert
        # with only defaults, which is not a safe operation.
        snap_file = self._snapshot_before_apply()
        if not snap_file:
            results.append({
                "success": False,
                "message": f"Pre-apply snapshot failed — apply blocked so your previous settings stay protected ({getattr(self, '_last_snapshot_error', 'unknown error')})",
            })
            return results
        results.append({"success": True, "message": f"Rollback snapshot saved ({os.path.basename(snap_file)})"})

        # 1. Set power plan
        power_plan = profile.get("power_plan", "high")
        try:
            plans = {"high": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c", "ultimate": "e9a42b02-d5df-448d-aa00-03f14749eb61"}
            guid = plans.get(power_plan, plans["high"])
            subprocess.run(["powercfg", "/setactive", guid], capture_output=True, timeout=10)
            results.append({"success": True, "message": f"Power plan set to {power_plan}"})
        except Exception as e:
            results.append({"success": False, "message": f"Power plan failed: {e}"})

        # 2. Enable Game Mode via registry
        if profile.get("game_mode"):
            try:
                subprocess.run(
                    ['reg', 'add', r'HKCU\Software\Microsoft\GameBar', '/v', 'AllowAutoGameMode',
                     '/t', 'REG_DWORD', '/d', '1', '/f'],
                    capture_output=True, timeout=10
                )
                results.append({"success": True, "message": "Windows Game Mode enabled"})
            except Exception as e:
                results.append({"success": False, "message": f"Game Mode failed: {e}"})

        # 3. Disable Game DVR
        if profile.get("dvr_off"):
            try:
                subprocess.run(
                    ['reg', 'add', r'HKCU\System\GameConfigStore', '/v', 'GameDVR_Enabled',
                     '/t', 'REG_DWORD', '/d', '0', '/f'],
                    capture_output=True, timeout=10
                )
                subprocess.run(
                    ['reg', 'add', r'HKLM\SOFTWARE\Policies\Microsoft\Windows\GameDVR',
                     '/v', 'AllowGameDVR', '/t', 'REG_DWORD', '/d', '0', '/f'],
                    capture_output=True, timeout=10
                )
                results.append({"success": True, "message": "Game DVR disabled"})
            except Exception as e:
                results.append({"success": False, "message": f"DVR disable failed: {e}"})

        # 4. Disable fullscreen optimizations
        if not profile.get("fullscreen_opt", True):
            try:
                subprocess.run(
                    ['reg', 'add', r'HKCU\System\GameConfigStore', '/v', 'GameDVR_FSEBehaviorMode',
                     '/t', 'REG_DWORD', '/d', '2', '/f'],
                    capture_output=True, timeout=10
                )
                results.append({"success": True, "message": "Fullscreen optimizations disabled"})
            except Exception as e:
                results.append({"success": False, "message": f"Fullscreen opt failed: {e}"})

        # 5. Disable mouse acceleration
        if not profile.get("mouse_accel", True):
            try:
                subprocess.run(
                    ['reg', 'add', r'HKCU\Control Panel\Mouse', '/v', 'MouseSpeed',
                     '/t', 'REG_SZ', '/d', '0', '/f'],
                    capture_output=True, timeout=10
                )
                subprocess.run(
                    ['reg', 'add', r'HKCU\Control Panel\Mouse', '/v', 'MouseThreshold1',
                     '/t', 'REG_SZ', '/d', '0', '/f'],
                    capture_output=True, timeout=10
                )
                subprocess.run(
                    ['reg', 'add', r'HKCU\Control Panel\Mouse', '/v', 'MouseThreshold2',
                     '/t', 'REG_SZ', '/d', '0', '/f'],
                    capture_output=True, timeout=10
                )
                results.append({"success": True, "message": "Mouse acceleration disabled"})
            except Exception as e:
                results.append({"success": False, "message": f"Mouse accel failed: {e}"})

        # 6. GPU Hardware Scheduling
        if profile.get("gpu_priority"):
            try:
                subprocess.run(
                    ['reg', 'add', r'HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers',
                     '/v', 'HwSchMode', '/t', 'REG_DWORD', '/d', '2', '/f'],
                    capture_output=True, timeout=10
                )
                results.append({"success": True, "message": "GPU Hardware Scheduling enabled"})
            except Exception as e:
                results.append({"success": False, "message": f"GPU scheduling failed: {e}"})

        # 7. Visual effects — best performance
        if profile.get("visual_effects") == "off":
            try:
                subprocess.run(
                    ['reg', 'add', r'HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects',
                     '/v', 'VisualFXSetting', '/t', 'REG_DWORD', '/d', '2', '/f'],
                    capture_output=True, timeout=10
                )
                results.append({"success": True, "message": "Visual effects set to best performance"})
            except Exception as e:
                results.append({"success": False, "message": f"Visual effects failed: {e}"})

        # 8. Network QoS for gaming
        if profile.get("network_priority"):
            try:
                subprocess.run(
                    ['reg', 'add', r'HKLM\SOFTWARE\Policies\Microsoft\Windows\Psched',
                     '/v', 'NonBestEffortLimit', '/t', 'REG_DWORD', '/d', '0', '/f'],
                    capture_output=True, timeout=10
                )
                results.append({"success": True, "message": "Network QoS priority set for gaming"})
            except Exception as e:
                results.append({"success": False, "message": f"Network priority failed: {e}"})

        logger.info(f"Applied profile '{profile_id}' — {sum(1 for r in results if r['success'])}/{len(results)} succeeded")
        return results

    def revert_profile(self) -> List[Dict[str, Any]]:
        """Revert all game optimizations to defaults."""
        results = []
        system = platform.system().lower()
        if system != "windows":
            return [{"success": False, "message": "Revert only supports Windows"}]

        reverts = [
            (r'HKCU\Control Panel\Mouse', 'MouseSpeed', '1'),
            (r'HKCU\Control Panel\Mouse', 'MouseThreshold1', '6'),
            (r'HKCU\Control Panel\Mouse', 'MouseThreshold2', '10'),
        ]
        for key, val_name, val_data in reverts:
            try:
                subprocess.run(
                    ['reg', 'add', key, '/v', val_name, '/t', 'REG_SZ', '/d', val_data, '/f'],
                    capture_output=True, timeout=10
                )
            except Exception:
                pass

        results.append({"success": True, "message": "Game optimizations reverted to defaults"})
        return results
