from pathlib import Path
from typing import Any

from verification_engine.storage._json_files import ensure_directory, read_json, safe_key, write_json
from verification_engine.storage.exceptions import StorageItemNotFound


class DriftStore:
    def __init__(self, root_path: str | Path) -> None:
        self._root_path = ensure_directory(root_path)

    @property
    def root_path(self) -> Path:
        return self._root_path

    def store_state(self, session_id: str, state: dict[str, Any]) -> None:
        write_json(self._path_for(session_id), state)

    def retrieve_state(self, session_id: str) -> dict[str, Any]:
        path = self._path_for(session_id)
        if not path.exists():
            raise StorageItemNotFound(f"Drift state not found: {session_id}")
        return read_json(path)

    def update_state(self, session_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        current = self.retrieve_state(session_id)
        current.update(updates)
        write_json(self._path_for(session_id), current)
        return current

    def remove_state(self, session_id: str) -> None:
        path = self._path_for(session_id)
        if not path.exists():
            raise StorageItemNotFound(f"Drift state not found: {session_id}")
        path.unlink()

    def _path_for(self, session_id: str) -> Path:
        return self._root_path / f"{safe_key(session_id)}.json"
