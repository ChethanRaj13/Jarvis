from __future__ import annotations

import json
from pathlib import Path
from threading import RLock
from types import MappingProxyType
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from .exceptions import (
    ConfigurationFileNotFound,
    ConfigurationParseError,
    ConfigurationValidationError,
)


ConfigModel = TypeVar("ConfigModel", bound=BaseModel)


class JsonConfigLoader:
    def __init__(self) -> None:
        self._cache: dict[Path, MappingProxyType[str, Any]] = {}
        self._lock = RLock()

    def load_json(self, file_path: str | Path) -> MappingProxyType[str, Any]:
        path = Path(file_path).expanduser().resolve()
        with self._lock:
            cached = self._cache.get(path)
            if cached is not None:
                return cached

            if not path.is_file():
                raise ConfigurationFileNotFound(f"Configuration file not found: {path}")

            try:
                with path.open("r", encoding="utf-8") as config_file:
                    loaded = json.load(config_file)
            except json.JSONDecodeError as exc:
                raise ConfigurationParseError(f"Invalid JSON in configuration file: {path}") from exc
            except OSError as exc:
                raise ConfigurationParseError(f"Unable to read configuration file: {path}") from exc

            if not isinstance(loaded, dict):
                raise ConfigurationParseError(f"Configuration file must contain a JSON object: {path}")

            cached_mapping = MappingProxyType(loaded)
            self._cache[path] = cached_mapping
            return cached_mapping

    def load_model(self, file_path: str | Path, model_type: type[ConfigModel]) -> ConfigModel:
        data = self.load_json(file_path)
        try:
            return model_type.model_validate(dict(data))
        except ValidationError as exc:
            raise ConfigurationValidationError(
                f"Configuration validation failed for {Path(file_path).expanduser().resolve()}"
            ) from exc

    def clear_cache(self) -> None:
        with self._lock:
            self._cache.clear()
