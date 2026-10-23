import os
import json
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from ..config import CONFIG
from ..logger import get_logger


class AIProvider(ABC):
    def __init__(self, name: str):
        self.name = name
        self.logger = get_logger(f"ai.{name}")

    @abstractmethod
    def chat(self, messages: List[Dict], model: str = None) -> Dict:
        pass

    @abstractmethod
    def analyze(self, prompt: str, system_prompt: str = None) -> str:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass

    @abstractmethod
    def to_dict(self) -> Dict:
        pass

    def get_models(self) -> List[str]:
        return []


class OpenAIProvider(AIProvider):
    def __init__(self, config: Dict):
        super().__init__("openai")
        self.api_key = config.get("api_key", "")
        self.base_url = "https://api.openai.com/v1"
        self.models = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o3-mini"]

    def chat(self, messages: List[Dict], model: str = None) -> Dict:
        return {"content": f"{self.name} is coming soon! Configure it in Settings.", "success": True, "simulated": True}

    def analyze(self, prompt: str, system_prompt: str = None) -> str:
        return self.chat([{"role": "user", "content": prompt}]).get("content", "")

    def is_available(self) -> bool:
        return bool(self.api_key)

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "display_name": "OpenAI",
            "available": self.is_available(),
            "models": self.models,
            "config": {"has_key": bool(self.api_key)},
        }

    def get_models(self) -> List[str]:
        return self.models


class GeminiProvider(AIProvider):
    def __init__(self, config: Dict):
        super().__init__("gemini")
        self.api_key = config.get("api_key", "")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.models = ["gemini-2.0-flash", "gemini-2.0-pro", "gemini-1.5-pro"]

    def chat(self, messages: List[Dict], model: str = None) -> Dict:
        return {"content": f"{self.name} is coming soon! Configure it in Settings.", "success": True, "simulated": True}

    def analyze(self, prompt: str, system_prompt: str = None) -> str:
        return self.chat([{"role": "user", "content": prompt}]).get("content", "")

    def is_available(self) -> bool:
        return bool(self.api_key)

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "display_name": "Gemini",
            "available": self.is_available(),
            "models": self.models,
            "config": {"has_key": bool(self.api_key)},
        }

    def get_models(self) -> List[str]:
        return self.models


class ClaudeProvider(AIProvider):
    def __init__(self, config: Dict):
        super().__init__("claude")
        self.api_key = config.get("api_key", "")
        self.base_url = "https://api.anthropic.com/v1"
        self.models = ["claude-sonnet-4-20250514", "claude-3-5-sonnet-latest", "claude-3-haiku"]

    def chat(self, messages: List[Dict], model: str = None) -> Dict:
        return {"content": f"{self.name} is coming soon! Configure it in Settings.", "success": True, "simulated": True}

    def analyze(self, prompt: str, system_prompt: str = None) -> str:
        return self.chat([{"role": "user", "content": prompt}]).get("content", "")

    def is_available(self) -> bool:
        return bool(self.api_key)

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "display_name": "Claude",
            "available": self.is_available(),
            "models": self.models,
            "config": {"has_key": bool(self.api_key)},
        }

    def get_models(self) -> List[str]:
        return self.models


class OpenRouterProvider(AIProvider):
    def __init__(self, config: Dict):
        super().__init__("openrouter")
        self.api_key = config.get("api_key", "")
        self.base_url = "https://openrouter.ai/api/v1"
        self.models = ["any"]

    def chat(self, messages: List[Dict], model: str = None) -> Dict:
        return {"content": f"{self.name} is coming soon! Configure it in Settings.", "success": True, "simulated": True}

    def analyze(self, prompt: str, system_prompt: str = None) -> str:
        return self.chat([{"role": "user", "content": prompt}]).get("content", "")

    def is_available(self) -> bool:
        return bool(self.api_key)

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "display_name": "OpenRouter",
            "available": self.is_available(),
            "models": self.models,
            "config": {"has_key": bool(self.api_key)},
        }

    def get_models(self) -> List[str]:
        return self.models


class OllamaProvider(AIProvider):
    def __init__(self, config: Dict):
        super().__init__("ollama")
        self.host = config.get("host", "localhost:11434")
        self.base_url = f"http://{self.host}/api"
        self.models = []

    def chat(self, messages: List[Dict], model: str = None) -> Dict:
        return {"content": f"{self.name} is coming soon! Configure it in Settings.", "success": True, "simulated": True}

    def analyze(self, prompt: str, system_prompt: str = None) -> str:
        return self.chat([{"role": "user", "content": prompt}]).get("content", "")

    def is_available(self) -> bool:
        return bool(self.host)

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "display_name": "Ollama",
            "available": self.is_available(),
            "models": self.models,
            "config": {"host": self.host},
        }

    def get_models(self) -> List[str]:
        return self.models


class LMStudioProvider(AIProvider):
    def __init__(self, config: Dict):
        super().__init__("lmstudio")
        self.host = config.get("host", "localhost:1234")
        self.base_url = f"http://{self.host}/v1"
        self.models = []

    def chat(self, messages: List[Dict], model: str = None) -> Dict:
        return {"content": f"{self.name} is coming soon! Configure it in Settings.", "success": True, "simulated": True}

    def analyze(self, prompt: str, system_prompt: str = None) -> str:
        return self.chat([{"role": "user", "content": prompt}]).get("content", "")

    def is_available(self) -> bool:
        return bool(self.host)

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "display_name": "LM Studio",
            "available": self.is_available(),
            "models": self.models,
            "config": {"host": self.host},
        }

    def get_models(self) -> List[str]:
        return self.models


class AIProviderManager:
    def __init__(self):
        self._providers: Dict[str, AIProvider] = {}
        self._active_provider: str = None
        self._settings: Dict = {}
        self.logger = get_logger("ai.manager")
        self._load_settings()
        self._init_providers()

    def _load_settings(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self._settings_path = os.path.join(base_dir, "data", "ai_settings.json")
        if os.path.exists(self._settings_path):
            try:
                with open(self._settings_path) as f:
                    self._settings = json.load(f)
            except Exception:
                self._settings = {}

    def _save_settings(self):
        os.makedirs(os.path.dirname(self._settings_path), exist_ok=True)
        with open(self._settings_path, "w") as f:
            json.dump(self._settings, f, indent=2)

    def _init_providers(self):
        self._providers = {
            "openai": OpenAIProvider(self._settings.get("openai", {})),
            "gemini": GeminiProvider(self._settings.get("gemini", {})),
            "claude": ClaudeProvider(self._settings.get("claude", {})),
            "openrouter": OpenRouterProvider(self._settings.get("openrouter", {})),
            "ollama": OllamaProvider(self._settings.get("ollama", {})),
            "lmstudio": LMStudioProvider(self._settings.get("lmstudio", {})),
        }
        self._active_provider = self._settings.get("active_provider")

    def get_providers(self) -> List[Dict]:
        return [p.to_dict() for p in self._providers.values()]

    def get_provider(self, name: str) -> Optional[AIProvider]:
        return self._providers.get(name)

    def get_active_provider(self) -> Optional[AIProvider]:
        if self._active_provider:
            return self._providers.get(self._active_provider)
        return None

    def set_active_provider(self, name: str) -> bool:
        if name in self._providers:
            self._active_provider = name
            self._settings["active_provider"] = name
            self._save_settings()
            return True
        return False

    def configure_provider(self, name: str, config: Dict) -> bool:
        if name not in self._providers:
            return False
        self._settings[name] = config
        self._init_providers()
        self._save_settings()
        return True

    def chat(self, messages: List[Dict], model: str = None) -> Dict:
        provider = self.get_active_provider()
        if provider and provider.is_available():
            return provider.chat(messages, model)
        return {
            "content": "AI features are coming soon! Configure a provider in Settings > AI Assistant to enable intelligent optimization recommendations.",
            "success": False,
            "simulated": True,
        }

    def analyze(self, prompt: str) -> str:
        result = self.chat([{"role": "user", "content": prompt}])
        return result.get("content", "")


ai_provider_manager = AIProviderManager()
