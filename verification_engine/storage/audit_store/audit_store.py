from pathlib import Path
from typing import Any, Mapping
from uuid import UUID

from pydantic import BaseModel

from verification_engine.storage._json_files import ensure_directory, read_json, safe_key, to_jsonable, write_json
from verification_engine.storage.exceptions import StorageImmutableRecordError, StorageItemNotFound


class AuditStore:
    def __init__(self, root_path: str | Path) -> None:
        self._root_path = ensure_directory(root_path)

    @property
    def root_path(self) -> Path:
        return self._root_path

    def append_record(self, record_id: str | UUID, record: Mapping[str, Any] | BaseModel) -> None:
        path = self._path_for(record_id)
        if path.exists():
            raise StorageImmutableRecordError(f"Audit record already exists: {record_id}")
        write_json(path, to_jsonable(record))

    def retrieve_record(self, record_id: str | UUID) -> dict[str, Any]:
        path = self._path_for(record_id)
        if not path.exists():
            raise StorageItemNotFound(f"Audit record not found: {record_id}")
        return read_json(path)

    def exists(self, record_id: str | UUID) -> bool:
        return self._path_for(record_id).exists()

    def list_records(self) -> list[str]:
        return sorted(path.stem for path in self._root_path.glob("*.json"))

    def _path_for(self, record_id: str | UUID) -> Path:
        return self._root_path / f"{safe_key(record_id)}.json"
