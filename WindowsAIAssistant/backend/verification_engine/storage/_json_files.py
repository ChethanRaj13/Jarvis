from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from .exceptions import StoragePathError


def ensure_directory(path: str | Path) -> Path:
    resolved = Path(path).expanduser().resolve()
    if resolved.exists() and not resolved.is_dir():
        raise StoragePathError(f"Storage path is not a directory: {resolved}")
    try:
        resolved.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise StoragePathError(f"Unable to create storage directory: {resolved}") from exc
    return resolved


def safe_key(value: str | UUID) -> str:
    text = str(value).strip()
    if not text:
        raise StoragePathError("Storage key cannot be empty")
    if any(character in text for character in ("\\", "/", ":", "*", "?", '"', "<", ">", "|")):
        raise StoragePathError(f"Storage key contains invalid path characters: {text}")
    return text


def to_jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [to_jsonable(item) for item in value]
    return value


def write_json(path: Path, payload: Any) -> None:
    try:
        path.write_text(
            json.dumps(to_jsonable(payload), indent=2, sort_keys=True),
            encoding="utf-8",
        )
    except OSError as exc:
        raise StoragePathError(f"Unable to write storage file: {path}") from exc


def read_json(path: Path) -> dict[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise StoragePathError(f"Unable to read storage file: {path}") from exc
    if not isinstance(loaded, dict):
        raise StoragePathError(f"Storage file must contain a JSON object: {path}")
    return loaded
