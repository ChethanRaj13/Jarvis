from uuid import uuid4

import pytest

from WindowsAIAssistant.backend.verification_engine.storage.exceptions import StorageItemAlreadyExists, StorageItemNotFound
from WindowsAIAssistant.backend.verification_engine.storage.pending_store import PendingVerificationStore


def test_pending_store_register_update_remove(tmp_path):
    store = PendingVerificationStore(tmp_path / "pending")
    request_id = uuid4()

    store.register_pending(request_id, {"request_id": str(request_id), "status": "PENDING"})
    assert store.exists(request_id) is True
    assert store.retrieve_pending(request_id)["status"] == "PENDING"

    updated = store.update_status(request_id, "ESCALATED")
    assert updated["status"] == "ESCALATED"

    store.remove_pending(request_id)
    assert store.exists(request_id) is False
    with pytest.raises(StorageItemNotFound):
        store.retrieve_pending(request_id)


def test_pending_store_duplicate_register_raises(tmp_path):
    store = PendingVerificationStore(tmp_path / "pending")
    request_id = uuid4()
    store.register_pending(request_id, {"status": "PENDING"})

    with pytest.raises(StorageItemAlreadyExists):
        store.register_pending(request_id, {"status": "PENDING"})
