from uuid import uuid4

import pytest

from WindowsAIAssistant.backend.verification_engine.storage.audit_store import AuditStore
from WindowsAIAssistant.backend.verification_engine.storage.exceptions import StorageImmutableRecordError, StorageItemNotFound


def test_audit_store_append_and_retrieve(tmp_path):
    store = AuditStore(tmp_path / "audit")
    record_id = uuid4()
    record = {
        "record_id": str(record_id),
        "request_id": str(uuid4()),
        "final_decision": "VERIFIED",
    }

    store.append_record(record_id, record)

    assert store.exists(record_id) is True
    assert store.retrieve_record(record_id) == record
    assert store.list_records() == [str(record_id)]


def test_audit_store_is_append_only_for_record_ids(tmp_path):
    store = AuditStore(tmp_path / "audit")
    record_id = uuid4()
    store.append_record(record_id, {"record_id": str(record_id)})

    with pytest.raises(StorageImmutableRecordError):
        store.append_record(record_id, {"record_id": str(record_id), "changed": True})


def test_audit_store_missing_record_raises(tmp_path):
    store = AuditStore(tmp_path / "audit")

    with pytest.raises(StorageItemNotFound):
        store.retrieve_record(uuid4())
