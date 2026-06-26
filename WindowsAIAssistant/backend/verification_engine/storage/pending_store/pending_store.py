from pathlib import Path
from typing import Any
from uuid import UUID

from WindowsAIAssistant.backend.verification_engine.storage._json_files import ensure_directory, read_json, safe_key, write_json
from WindowsAIAssistant.backend.verification_engine.storage.exceptions import StorageItemAlreadyExists, StorageItemNotFound


class PendingVerificationStore:
    def __init__(self, root_path: str | Path) -> None:
        self._root_path = ensure_directory(root_path)

    @property
    def root_path(self) -> Path:
        return self._root_path

    def register_pending(self, request_id: str | UUID, pending: dict[str, Any]) -> None:
        path = self._path_for(request_id)
        if path.exists():
            raise StorageItemAlreadyExists(f"Pending verification already exists: {request_id}")
        write_json(path, pending)

    def update_status(self, request_id: str | UUID, status: str) -> dict[str, Any]:
        pending = self.retrieve_pending(request_id)
        pending["status"] = status
        write_json(self._path_for(request_id), pending)
        return pending

    def retrieve_pending(self, request_id: str | UUID) -> dict[str, Any]:
        path = self._path_for(request_id)
        if not path.exists():
            raise StorageItemNotFound(f"Pending verification not found: {request_id}")
        return read_json(path)

    def remove_pending(self, request_id: str | UUID) -> None:
        path = self._path_for(request_id)
        if not path.exists():
            raise StorageItemNotFound(f"Pending verification not found: {request_id}")
        path.unlink()

    def exists(self, request_id: str | UUID) -> bool:
        return self._path_for(request_id).exists()

    def _path_for(self, request_id: str | UUID) -> Path:
        return self._root_path / f"{safe_key(request_id)}.json"
