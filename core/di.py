from typing import Dict, Any, Optional, Type


class Container:
    _instances: Dict[str, Any] = {}
    _factories: Dict[str, Type] = {}

    @classmethod
    def register(cls, name: str, factory: Type, singleton: bool = True):
        if singleton:
            cls._factories[name] = factory
        else:
            cls._factories[name] = factory

    @classmethod
    def instance(cls, name: str, *args, **kwargs) -> Any:
        if name not in cls._instances:
            factory = cls._factories.get(name)
            if not factory:
                raise KeyError(f"No factory registered for '{name}'")
            cls._instances[name] = factory(*args, **kwargs)
        return cls._instances[name]

    @classmethod
    def get(cls, name: str) -> Optional[Any]:
        return cls._instances.get(name)

    @classmethod
    def reset(cls):
        cls._instances.clear()
        cls._factories.clear()
