from pathlib import Path
from uuid import UUID

from verification_engine.contracts import EvidencePackage

from verification_engine.storage._json_files import ensure_directory, read_json, safe_key, write_json
from verification_engine.storage.exceptions import StorageItemNotFound


class EvidenceStore:
    def __init__(self, root_path: str | Path) -> None:
        self._root_path = ensure_directory(root_path)

    @property
    def root_path(self) -> Path:
        return self._root_path

    def store_evidence(self, evidence: EvidencePackage) -> None:
        write_json(self._path_for(evidence.request_id), evidence)

    def retrieve_evidence(self, request_id: str | UUID) -> EvidencePackage:
        path = self._path_for(request_id)
        if not path.exists():
            raise StorageItemNotFound(f"Evidence not found for request_id: {request_id}")
        return EvidencePackage.model_validate(read_json(path))

    def exists(self, request_id: str | UUID) -> bool:
        return self._path_for(request_id).exists()

    def delete_evidence(self, request_id: str | UUID) -> None:
        path = self._path_for(request_id)
        if not path.exists():
            raise StorageItemNotFound(f"Evidence not found for request_id: {request_id}")
        path.unlink()

    def list_evidence(self) -> list[UUID]:
        return sorted(UUID(path.stem) for path in self._root_path.glob("*.json"))

    def get_evidence(self, evidence_id: UUID) -> EvidencePackage:
        for request_id in self.list_evidence():
            evidence = self.retrieve_evidence(request_id)
            if evidence.evidence_id == evidence_id:
                return evidence
        raise StorageItemNotFound(f"Evidence not found for evidence_id: {evidence_id}")

    def _path_for(self, request_id: str | UUID) -> Path:
        return self._root_path / f"{safe_key(request_id)}.json"
