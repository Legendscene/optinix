import os
import json
import shutil
import threading
from typing import Dict, List, Optional
from datetime import datetime

from ..config import CONFIG
from ..logger import get_logger

BUILTIN_MODULES = {
    "obs-toolkit": {
        "name": "OBS Toolkit",
        "description": "Optimize Windows for OBS streaming. Configures GPU scheduling, disables desktop composition for fullscreen, sets high priority for OBS, and tunes network QoS for streaming.",
        "category": "content-creation",
        "icon": "video",
    },
    "vscode-toolkit": {
        "name": "VS Code Toolkit",
        "description": "Optimize system performance for VS Code development. Disables unnecessary animations, configures file watcher limits, tunes I/O for large projects.",
        "category": "development",
        "icon": "code-2",
    },
    "blender-toolkit": {
        "name": "Blender Toolkit",
        "description": "Optimize GPU and CPU for Blender rendering. Configures CUDA/Optix for NVIDIA, sets power plan for consistent rendering, optimizes memory allocation.",
        "category": "content-creation",
        "icon": "cube",
    },
    "adobe-toolkit": {
        "name": "Adobe Toolkit",
        "description": "Optimize for Adobe Creative Cloud apps (Photoshop, Premiere, After Effects). Configures GPU acceleration, disk cache, and memory allocation.",
        "category": "content-creation",
        "icon": "palette",
    },
    "unreal-toolkit": {
        "name": "Unreal Toolkit",
        "description": "Optimize Windows for Unreal Engine development. Configures shader cache, sets CPU priority, optimizes disk I/O for asset loading.",
        "category": "development",
        "icon": "gamepad-2",
    },
    "unity-toolkit": {
        "name": "Unity Toolkit",
        "description": "Optimize system for Unity development. Configures GPU for Editor, optimizes asset importing, tunes memory for large scenes.",
        "category": "development",
        "icon": "box",
    },
    "steam-toolkit": {
        "name": "Steam Toolkit",
        "description": "Optimize for Steam gaming. Configures shader pre-caching, optimizes download settings, tunes background processes for gaming.",
        "category": "gaming",
        "icon": "gamepad",
    },
    "minecraft-toolkit": {
        "name": "Minecraft Toolkit",
        "description": "Optimize Java performance for Minecraft. Configures JVM arguments, allocates optimal RAM, sets process priority for Java.",
        "category": "gaming",
        "icon": "pickaxe",
    },
    "docker-toolkit": {
        "name": "Docker Toolkit",
        "description": "Optimize Windows for Docker. Configures WSL2 resources, disk image storage location, and network performance for containers.",
        "category": "development",
        "icon": "container",
    },
}

MODULE_TEMPLATE = {
    "version": "1.0.0",
    "author": "Optinix",
    "tags": [],
    "size_kb": 0,
    "downloads": 0,
    "rating": 4.5,
    "installed": False,
    "install_time": None,
    "settings": {},
    "optimizers_included": [],
    "requirements": {"min_ram_gb": 8, "os": "windows"},
}


class MarketplaceManager:
    def __init__(self):
        self._lock = threading.Lock()
        self.logger = get_logger("marketplace")
        self._base_path = os.path.join(CONFIG.base_dir, "data", "marketplace")
        self._modules_path = os.path.join(self._base_path, "modules.json")
        self._installed_path = os.path.join(self._base_path, "installed.json")
        self._installed_dir = os.path.join(self._base_path, "installed")
        self._init_dirs()
        self._register_builtins()

    def _init_dirs(self):
        try:
            os.makedirs(self._base_path, exist_ok=True)
            os.makedirs(self._installed_dir, exist_ok=True)
        except OSError:
            self.logger.exception("Failed to create marketplace directories")

    def _register_builtins(self):
        try:
            registry = self._get_registry()
            changed = False
            for mid, info in BUILTIN_MODULES.items():
                if mid not in registry:
                    entry = {
                        "id": mid,
                        "name": info["name"],
                        "description": info["description"],
                        "category": info["category"],
                        "icon": info["icon"],
                    }
                    entry.update(MODULE_TEMPLATE)
                    registry[mid] = entry
                    changed = True
            if changed:
                self._save_registry(registry)
        except Exception:
            self.logger.exception("Failed to register built-in modules")

    def _get_registry(self) -> Dict:
        with self._lock:
            if not os.path.isfile(self._modules_path):
                return {}
            try:
                with open(self._modules_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                self.logger.exception("Failed to load module registry")
                return {}

    def _save_registry(self, data: Dict):
        with self._lock:
            try:
                with open(self._modules_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            except IOError:
                self.logger.exception("Failed to save module registry")

    def _get_installed(self) -> Dict:
        with self._lock:
            if not os.path.isfile(self._installed_path):
                return {}
            try:
                with open(self._installed_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                self.logger.exception("Failed to load installed modules")
                return {}

    def _save_installed(self, data: Dict):
        with self._lock:
            try:
                with open(self._installed_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            except IOError:
                self.logger.exception("Failed to save installed modules")

    def list_modules(self, category: str = None, installed_only: bool = False) -> List[Dict]:
        try:
            registry = self._get_registry()
            installed = self._get_installed()
            modules = []
            for mid, mod in registry.items():
                is_installed = mid in installed
                if installed_only and not is_installed:
                    continue
                if category and mod.get("category") != category:
                    continue
                entry = dict(mod)
                entry["installed"] = is_installed
                entry["install_time"] = installed.get(mid, {}).get("install_time")
                modules.append(entry)
            return modules
        except Exception:
            self.logger.exception("Failed to list modules")
            return []

    def get_module(self, module_id: str) -> Optional[Dict]:
        try:
            registry = self._get_registry()
            if module_id not in registry:
                return None
            installed = self._get_installed()
            entry = dict(registry[module_id])
            entry["installed"] = module_id in installed
            entry["install_time"] = installed.get(module_id, {}).get("install_time")
            return entry
        except Exception:
            self.logger.exception(f"Failed to get module {module_id}")
            return None

    def get_categories(self) -> List[str]:
        try:
            registry = self._get_registry()
            cats = {m.get("category", "other") for m in registry.values()}
            return sorted(cats)
        except Exception:
            self.logger.exception("Failed to get categories")
            return []

    def install_module(self, module_id: str) -> Dict:
        try:
            registry = self._get_registry()
            if module_id not in registry:
                return {"success": False, "error": f"Module '{module_id}' not found"}
            installed = self._get_installed()
            if module_id in installed:
                return {"success": False, "error": f"Module '{module_id}' is already installed"}
            mod_dir = os.path.join(self._installed_dir, module_id)
            os.makedirs(mod_dir, exist_ok=True)
            config = {
                "module_id": module_id,
                "name": registry[module_id]["name"],
                "installed_at": datetime.now().isoformat(),
                "settings": {},
            }
            config_path = os.path.join(mod_dir, "config.json")
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            installed[module_id] = {
                "install_time": datetime.now().isoformat(),
                "settings": {},
            }
            self._save_installed(installed)
            registry[module_id]["installed"] = True
            self._save_registry(registry)
            return {"success": True, "module_id": module_id}
        except Exception as e:
            self.logger.exception(f"Failed to install module {module_id}")
            return {"success": False, "error": str(e)}

    def uninstall_module(self, module_id: str) -> Dict:
        try:
            installed = self._get_installed()
            if module_id not in installed:
                return {"success": False, "error": f"Module '{module_id}' is not installed"}
            mod_dir = os.path.join(self._installed_dir, module_id)
            if os.path.isdir(mod_dir):
                shutil.rmtree(mod_dir)
            del installed[module_id]
            self._save_installed(installed)
            registry = self._get_registry()
            if module_id in registry:
                registry[module_id]["installed"] = False
                self._save_registry(registry)
            return {"success": True, "module_id": module_id}
        except Exception as e:
            self.logger.exception(f"Failed to uninstall module {module_id}")
            return {"success": False, "error": str(e)}

    def get_installed_count(self) -> int:
        try:
            installed = self._get_installed()
            return len(installed)
        except Exception:
            return 0

    def get_install_path(self, module_id: str) -> str:
        return os.path.join(self._installed_dir, module_id)

    def is_installed(self, module_id: str) -> bool:
        try:
            installed = self._get_installed()
            return module_id in installed
        except Exception:
            return False

    def get_module_settings(self, module_id: str) -> Dict:
        try:
            installed = self._get_installed()
            if module_id not in installed:
                return {}
            return installed[module_id].get("settings", {})
        except Exception:
            self.logger.exception(f"Failed to get settings for {module_id}")
            return {}

    def save_module_settings(self, module_id: str, settings: Dict) -> Dict:
        try:
            installed = self._get_installed()
            if module_id not in installed:
                return {"success": False, "error": f"Module '{module_id}' is not installed"}
            installed[module_id]["settings"] = settings
            self._save_installed(installed)
            config_path = os.path.join(self._installed_dir, module_id, "config.json")
            try:
                if os.path.isfile(config_path):
                    with open(config_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                    cfg["settings"] = settings
                    with open(config_path, "w", encoding="utf-8") as f:
                        json.dump(cfg, f, indent=2, ensure_ascii=False)
            except (IOError, json.JSONDecodeError):
                pass
            return {"success": True, "module_id": module_id}
        except Exception as e:
            self.logger.exception(f"Failed to save settings for {module_id}")
            return {"success": False, "error": str(e)}


marketplace_manager = MarketplaceManager()
