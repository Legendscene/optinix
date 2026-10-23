import os
import sys
import importlib
import inspect
import json
import shutil
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Type
from core.config import CONFIG
from core.logger import get_logger
from core.base import OptimizerBase


class PluginMetadata:
    def __init__(self, name: str, version: str, author: str, description: str, min_app_version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.author = author
        self.description = description
        self.min_app_version = min_app_version

    def to_dict(self) -> Dict[str, str]:
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "min_app_version": self.min_app_version,
        }

    @staticmethod
    def from_dict(data: Dict[str, str]) -> "PluginMetadata":
        return PluginMetadata(
            name=data.get("name", "unknown"),
            version=data.get("version", "0.0.0"),
            author=data.get("author", "unknown"),
            description=data.get("description", ""),
            min_app_version=data.get("min_app_version", "1.0.0"),
        )


class PluginBase(ABC):
    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        ...

    @abstractmethod
    def initialize(self) -> bool:
        ...

    @abstractmethod
    def on_optimize(self) -> List[Dict[str, Any]]:
        ...

    def on_cleanup(self) -> None:
        pass

    def on_settings_changed(self, settings: Dict[str, Any]) -> None:
        pass


class PluginManager:
    def __init__(self):
        self.logger = get_logger("plugin_system")
        self.plugins_dir = os.path.join(CONFIG.base_dir, "plugins")
        self.loaded_plugins: Dict[str, PluginBase] = {}
        self.plugin_metadata: Dict[str, PluginMetadata] = {}
        self.enabled_plugins: List[str] = []
        self._ensure_plugins_dir()
        self._load_enabled_list()

    def _ensure_plugins_dir(self):
        try:
            os.makedirs(self.plugins_dir, exist_ok=True)
        except Exception as e:
            self.logger.error(f"Failed to create plugins directory: {e}")

    def _load_enabled_list(self):
        config_dir = CONFIG.config_dir if hasattr(CONFIG, "config_dir") else CONFIG.base_dir
        state_file = os.path.join(config_dir, "plugin_state.json")
        try:
            if os.path.isfile(state_file):
                with open(state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.enabled_plugins = data.get("enabled", [])
            else:
                self.enabled_plugins = []
        except Exception as e:
            self.logger.warning(f"Failed to load plugin state: {e}")
            self.enabled_plugins = []

    def _save_enabled_list(self):
        config_dir = CONFIG.config_dir if hasattr(CONFIG, "config_dir") else CONFIG.base_dir
        state_file = os.path.join(config_dir, "plugin_state.json")
        try:
            os.makedirs(config_dir, exist_ok=True)
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump({"enabled": self.enabled_plugins}, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save plugin state: {e}")

    def _find_plugin_modules(self) -> List[str]:
        if not os.path.isdir(self.plugins_dir):
            self.logger.warning(f"Plugins directory not found: {self.plugins_dir}")
            return []
        names = []
        for entry in os.listdir(self.plugins_dir):
            plugin_path = os.path.join(self.plugins_dir, entry)
            if os.path.isdir(plugin_path):
                plugin_file = os.path.join(plugin_path, "plugin.py")
                if os.path.isfile(plugin_file):
                    names.append(entry)
        return sorted(names)

    def _load_plugin_metadata_from_json(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        manifest_path = os.path.join(self.plugins_dir, plugin_name, "plugin.json")
        if not os.path.isfile(manifest_path):
            return None
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            self.logger.warning(f"Failed to read plugin.json for '{plugin_name}': {e}")
            return None

    def discover_plugins(self) -> List[Dict[str, Any]]:
        discovered = []
        for name in self._find_plugin_modules():
            info = {"name": name, "path": os.path.join(self.plugins_dir, name), "loaded": name in self.loaded_plugins}
            manifest = self._load_plugin_metadata_from_json(name)
            if manifest:
                info["version"] = manifest.get("version", "0.0.0")
                info["author"] = manifest.get("author", "unknown")
                info["description"] = manifest.get("description", "")
                info["min_app_version"] = manifest.get("min_app_version", "1.0.0")
            else:
                info["version"] = "0.0.0"
                info["author"] = "unknown"
                info["description"] = ""
                info["min_app_version"] = "1.0.0"
            discovered.append(info)
        return discovered

    def load_plugin(self, plugin_name: str) -> bool:
        if plugin_name in self.loaded_plugins:
            self.logger.debug(f"Plugin '{plugin_name}' already loaded")
            return True

        plugin_dir = os.path.join(self.plugins_dir, plugin_name)
        plugin_file = os.path.join(plugin_dir, "plugin.py")

        if not os.path.isfile(plugin_file):
            self.logger.error(f"Plugin file not found: {plugin_file}")
            return False

        try:
            sys_path_entry = os.path.dirname(self.plugins_dir.rstrip(os.sep))
            if sys_path_entry not in sys.path:
                sys.path.insert(0, sys_path_entry)

            module_path = f"plugins.{plugin_name}.plugin"
            module = importlib.import_module(module_path)

            plugin_classes = []
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, PluginBase) and obj is not PluginBase:
                    plugin_classes.append(obj)

            if not plugin_classes:
                self.logger.error(f"No PluginBase subclass found in '{plugin_name}'")
                return False

            plugin_class = plugin_classes[0]
            plugin_instance = plugin_class()

            metadata = plugin_instance.get_metadata()
            self.plugin_metadata[plugin_name] = metadata

            initialized = plugin_instance.initialize()
            if not initialized:
                self.logger.warning(f"Plugin '{plugin_name}' initialize() returned False, skipping")
                return False

            self.loaded_plugins[plugin_name] = plugin_instance
            self.logger.info(f"Loaded plugin: {metadata.name} v{metadata.version} by {metadata.author}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to load plugin '{plugin_name}': {e}", exc_info=True)
            return False

    def load_all_plugins(self) -> Dict[str, bool]:
        results = {}
        for name in self._find_plugin_modules():
            if name in self.enabled_plugins:
                results[name] = self.load_plugin(name)
            else:
                results[name] = False
        return results

    def unload_plugin(self, plugin_name: str) -> bool:
        if plugin_name not in self.loaded_plugins:
            self.logger.warning(f"Plugin '{plugin_name}' is not loaded")
            return False
        try:
            plugin = self.loaded_plugins[plugin_name]
            plugin.on_cleanup()
            del self.loaded_plugins[plugin_name]
            self.plugin_metadata.pop(plugin_name, None)
            parent = os.path.dirname(self.plugins_dir.rstrip(os.sep))
            sys.path = [p for p in sys.path if p != parent]
            self.logger.info(f"Unloaded plugin: {plugin_name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to unload plugin '{plugin_name}': {e}")
            return False

    def enable_plugin(self, plugin_name: str) -> bool:
        if plugin_name in self.enabled_plugins:
            return True
        self.enabled_plugins.append(plugin_name)
        self._save_enabled_list()
        self.logger.info(f"Enabled plugin: {plugin_name}")
        return True

    def disable_plugin(self, plugin_name: str) -> bool:
        if plugin_name not in self.enabled_plugins:
            return True
        self.enabled_plugins = [p for p in self.enabled_plugins if p != plugin_name]
        if plugin_name in self.loaded_plugins:
            self.unload_plugin(plugin_name)
        self._save_enabled_list()
        self.logger.info(f"Disabled plugin: {plugin_name}")
        return True

    def get_plugin_optimizers(self) -> List[OptimizerBase]:
        optimizers = []
        for name, plugin in self.loaded_plugins.items():
            try:
                adapter = _PluginOptimizerAdapter(name, plugin)
                optimizers.append(adapter)
            except Exception as e:
                self.logger.error(f"Failed to create optimizer adapter for '{name}': {e}")
        return optimizers

    def run_plugin_optimizers(self) -> Dict[str, List[Dict[str, Any]]]:
        results = {}
        for name, plugin in self.loaded_plugins.items():
            try:
                self.logger.info(f"Running plugin optimizer: {name}")
                plugin_results = plugin.on_optimize()
                results[name] = plugin_results
            except Exception as e:
                self.logger.error(f"Plugin '{name}' on_optimize failed: {e}", exc_info=True)
                results[name] = [{"success": False, "error": str(e)}]
        return results

    def get_plugin_info(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        plugin_dir = os.path.join(self.plugins_dir, plugin_name)
        if not os.path.isdir(plugin_dir):
            return None

        info: Dict[str, Any] = {
            "name": plugin_name,
            "path": plugin_dir,
            "loaded": plugin_name in self.loaded_plugins,
            "enabled": plugin_name in self.enabled_plugins,
        }

        manifest = self._load_plugin_metadata_from_json(plugin_name)
        if manifest:
            info["version"] = manifest.get("version", "0.0.0")
            info["author"] = manifest.get("author", "unknown")
            info["description"] = manifest.get("description", "")
            info["min_app_version"] = manifest.get("min_app_version", "1.0.0")
            info["manifest"] = manifest

        if plugin_name in self.plugin_metadata:
            meta = self.plugin_metadata[plugin_name]
            info["metadata"] = meta.to_dict()

        has_plugin_py = os.path.isfile(os.path.join(plugin_dir, "plugin.py"))
        info["has_plugin_py"] = has_plugin_py
        info["valid"] = has_plugin_py

        return info

    def get_all_plugins_info(self) -> List[Dict[str, Any]]:
        infos = []
        for name in self._find_plugin_modules():
            info = self.get_plugin_info(name)
            if info:
                infos.append(info)
        return infos


class _PluginOptimizerAdapter(OptimizerBase):
    def __init__(self, plugin_name: str, plugin: PluginBase):
        meta = plugin.get_metadata()
        self.name = meta.name
        self.description = meta.description
        self._plugin_name = plugin_name
        self._plugin = plugin
        super().__init__()

    def run(self) -> List[Dict[str, Any]]:
        try:
            return self._plugin.on_optimize()
        except Exception as e:
            self.logger.error(f"Plugin '{self._plugin_name}' run failed: {e}", exc_info=True)
            return [{"success": False, "error": str(e)}]


class PluginDeveloperTools:
    @staticmethod
    def create_plugin_template(name: str, author: str, description: str) -> str:
        content = f'''import os
from typing import Dict, List, Any
from core.plugin_system import PluginBase, PluginMetadata


class {name.capitalize().replace("-", "").replace("_", "")}Plugin(PluginBase):
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="{name}",
            version="1.0.0",
            author="{author}",
            description="{description}",
            min_app_version="1.0.0",
        )

    def initialize(self) -> bool:
        return True

    def on_optimize(self) -> List[Dict[str, Any]]:
        return [{{"success": True, "message": "{name} optimization complete"}}]

    def on_cleanup(self) -> None:
        pass

    def on_settings_changed(self, settings: Dict[str, Any]) -> None:
        pass
'''
        return content.strip()

    @staticmethod
    def validate_plugin(plugin_path: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "valid": False,
            "errors": [],
            "warnings": [],
            "info": {},
        }

        if not os.path.exists(plugin_path):
            result["errors"].append("Path does not exist")
            return result

        plugin_file = plugin_path if plugin_path.endswith(".py") else os.path.join(plugin_path, "plugin.py")
        if not os.path.isfile(plugin_file):
            result["errors"].append(f"plugin.py not found at {plugin_file}")
            return result

        manifest_path = os.path.join(os.path.dirname(plugin_file), "plugin.json")
        if os.path.isfile(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                required = ["name", "version", "author"]
                missing = [k for k in required if k not in manifest]
                if missing:
                    result["warnings"].append(f"plugin.json missing keys: {missing}")
                result["info"]["manifest"] = manifest
            except Exception as e:
                result["warnings"].append(f"plugin.json is invalid JSON: {e}")

        try:
            import_name = os.path.splitext(os.path.basename(plugin_file))[0]
            spec = importlib.util.spec_from_file_location(import_name, plugin_file)

            if spec is None or spec.loader is None:
                result["errors"].append("Could not create module spec from plugin.py")
                return result

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            plugin_classes = []
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, PluginBase) and obj is not PluginBase:
                    plugin_classes.append(obj)

            if not plugin_classes:
                result["errors"].append("No class inheriting from PluginBase found")
                return result

            plugin_class = plugin_classes[0]
            instance = plugin_class()
            meta = instance.get_metadata()
            result["info"]["metadata"] = {
                "name": meta.name,
                "version": meta.version,
                "author": meta.author,
                "description": meta.description,
                "min_app_version": meta.min_app_version,
            }

            initialized = instance.initialize()
            if not initialized:
                result["warnings"].append("initialize() returned False")
            else:
                result["info"]["initialized"] = True

            optimize_results = instance.on_optimize()
            if not isinstance(optimize_results, list):
                result["errors"].append("on_optimize() must return a list")
                return result

            result["info"]["optimize_count"] = len(optimize_results)
            result["info"]["all_success"] = all(r.get("success", False) for r in optimize_results)
            result["valid"] = True

        except Exception as e:
            result["errors"].append(f"Validation error: {e}")

        return result

    @staticmethod
    def create_plugin_structure(name: str, author: str, description: str, version: str) -> str:
        plugins_base = os.path.join(CONFIG.base_dir, "plugins")
        plugin_dir = os.path.join(plugins_base, name)
        os.makedirs(plugin_dir, exist_ok=True)

        plugin_py = os.path.join(plugin_dir, "plugin.py")
        template = PluginDeveloperTools.create_plugin_template(name, author, description)
        with open(plugin_py, "w", encoding="utf-8") as f:
            f.write(template)

        plugin_json = os.path.join(plugin_dir, "plugin.json")
        manifest = {
            "name": name,
            "version": version,
            "author": author,
            "description": description,
            "min_app_version": "1.0.0",
        }
        with open(plugin_json, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        readme_path = os.path.join(plugin_dir, "README.md")
        if not os.path.isfile(readme_path):
            readme = f"# {name}\n\n**Author:** {author}\n**Version:** {version}\n\n{description}\n"
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(readme)

        self_path = os.path.join(plugin_dir, "__init__.py")
        if not os.path.isfile(self_path):
            with open(self_path, "w", encoding="utf-8") as f:
                f.write("")

        return plugin_dir
