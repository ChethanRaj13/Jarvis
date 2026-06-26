from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from verification_engine.storage._json_files import ensure_directory, read_json, safe_key, write_json
from verification_engine.storage.exceptions import StorageItemAlreadyExists, StorageItemNotFound


@dataclass(frozen=True)
class ReplayTokenRecord:
    token: str
    expires_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


class ReplayStore:
    def __init__(self, root_path: str | Path) -> None:
        self._root_path = ensure_directory(root_path)

    @property
    def root_path(self) -> Path:
        return self._root_path

    def record_token(
        self,
        token: str,
        expires_at: datetime,
        metadata: dict[str, Any] | None = None,
    ) -> ReplayTokenRecord:
        path = self._path_for(token)
        if path.exists():
            raise StorageItemAlreadyExists(f"Replay token already exists: {token}")
        record = ReplayTokenRecord(token=token, expires_at=expires_at, metadata=dict(metadata or {}))
        write_json(path, {"token": record.token, "expires_at": record.expires_at, "metadata": record.metadata})
        return record

    def lookup_token(self, token: str) -> ReplayTokenRecord:
        path = self._path_for(token)
        if not path.exists():
            raise StorageItemNotFound(f"Replay token not found: {token}")
        payload = read_json(path)
        return ReplayTokenRecord(
            token=str(payload["token"]),
            expires_at=datetime.fromisoformat(str(payload["expires_at"])),
            metadata=dict(payload.get("metadata", {})),
        )

    def exists(self, token: str) -> bool:
        return self._path_for(token).exists()

    def remove_expired_tokens(self, now: datetime | None = None) -> int:
        reference_time = now or datetime.now(timezone.utc)
        removed = 0
        for path in self._root_path.glob("*.json"):
            record = self.lookup_token(path.stem)
            if record.expires_at <= reference_time:
                path.unlink()
                removed += 1
        return removed

    def _path_for(self, token: str) -> Path:
        return self._root_path / f"{safe_key(token)}.json"
