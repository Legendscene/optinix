import os
import json


class TweakState:
    def __init__(self):
        self._path = self._get_path()
        self._state = self._load()

    def _get_path(self):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base, "config", "tweak_state.json")

    def _load(self):
        if os.path.exists(self._path):
            try:
                with open(self._path) as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save(self):
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w") as f:
            json.dump(self._state, f, indent=2)

    def get(self, key, default=None):
        return self._state.get(key, default)

    def set(self, key, value):
        self._state[key] = value
        self.save()

    def get_all(self):
        return self._state

    def clear(self):
        self._state = {}
        self.save()
