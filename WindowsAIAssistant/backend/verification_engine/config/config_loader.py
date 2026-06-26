from __future__ import annotations

from pathlib import Path
from threading import RLock
from typing import TypeVar

from pydantic import BaseModel

from .audit_config import AuditConfig
from .loader import JsonConfigLoader
from .storage_config import StorageConfig
from .verification_config import VerificationConfig


ConfigModel = TypeVar("ConfigModel", bound=BaseModel)


class ConfigurationLoader:
    _instance: "ConfigurationLoader | None" = None
    _instance_lock = RLock()

    def __new__(cls) -> "ConfigurationLoader":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._json_loader = JsonConfigLoader()
        self._model_cache: dict[tuple[Path, type[BaseModel]], BaseModel] = {}
        self._lock = RLock()
        self._initialized = True

    def get_config(self, file_path: str | Path, model_type: type[ConfigModel]) -> ConfigModel:
        path = Path(file_path).expanduser().resolve()
        cache_key = (path, model_type)
        with self._lock:
            cached = self._model_cache.get(cache_key)
            if cached is not None:
                return cached

            config = self._json_loader.load_model(path, model_type)
            self._model_cache[cache_key] = config
            return config

    def get_verification_config(self, file_path: str | Path) -> VerificationConfig:
        return self.get_config(file_path, VerificationConfig)

    def get_storage_config(self, file_path: str | Path) -> StorageConfig:
        return self.get_config(file_path, StorageConfig)

    def get_audit_config(self, file_path: str | Path) -> AuditConfig:
        return self.get_config(file_path, AuditConfig)

    def clear_cache(self) -> None:
        with self._lock:
            self._model_cache.clear()
            self._json_loader.clear_cache()
