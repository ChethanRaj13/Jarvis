from datetime import datetime, timezone
from uuid import uuid4

import pytest

from verification_engine.contracts import EvidencePackage, EvidenceType
from verification_engine.storage.evidence_store import EvidenceStore
from verification_engine.storage.exceptions import StorageItemNotFound


UTC_NOW = datetime(2026, 6, 26, 1, 0, tzinfo=timezone.utc)


def evidence_package(request_id=None) -> EvidencePackage:
    return EvidencePackage(
        evidence_id=uuid4(),
        request_id=request_id or uuid4(),
        evidence_type=EvidenceType.FILESYSTEM,
        collection_timestamp=UTC_NOW,
        collection_window_open=True,
        binding_token="binding-token",
        collector_id="collector",
        evidence_payload={"path": "C:/temp/file.txt", "exists": True},
    )


def test_evidence_store_creates_storage_directory(tmp_path):
    root = tmp_path / "evidence"

    store = EvidenceStore(root)

    assert store.root_path == root.resolve()
    assert root.is_dir()


def test_evidence_store_store_retrieve_exists_and_list(tmp_path):
    store = EvidenceStore(tmp_path / "evidence")
    evidence = evidence_package()

    store.store_evidence(evidence)

    assert store.exists(evidence.request_id) is True
    assert store.retrieve_evidence(evidence.request_id) == evidence
    assert store.list_evidence() == [evidence.request_id]


def test_evidence_store_delete(tmp_path):
    store = EvidenceStore(tmp_path / "evidence")
    evidence = evidence_package()
    store.store_evidence(evidence)

    store.delete_evidence(evidence.request_id)

    assert store.exists(evidence.request_id) is False
    with pytest.raises(StorageItemNotFound):
        store.retrieve_evidence(evidence.request_id)


def test_evidence_store_get_evidence_by_evidence_id(tmp_path):
    store = EvidenceStore(tmp_path / "evidence")
    evidence = evidence_package()
    store.store_evidence(evidence)

    assert store.get_evidence(evidence.evidence_id) == evidence
