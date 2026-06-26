import pytest

from verification_engine.storage.drift_store import DriftStore
from verification_engine.storage.exceptions import StorageItemNotFound


def test_drift_store_create_update_delete(tmp_path):
    store = DriftStore(tmp_path / "drift")

    store.store_state("session-1", {"changes": [], "count": 0})
    assert store.retrieve_state("session-1") == {"changes": [], "count": 0}

    updated = store.update_state("session-1", {"count": 1})
    assert updated == {"changes": [], "count": 1}
    assert store.retrieve_state("session-1") == updated

    store.remove_state("session-1")
    with pytest.raises(StorageItemNotFound):
        store.retrieve_state("session-1")
