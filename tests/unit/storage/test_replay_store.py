from datetime import datetime, timedelta, timezone

import pytest

from verification_engine.storage.exceptions import StorageItemAlreadyExists, StorageItemNotFound
from verification_engine.storage.replay_store import ReplayStore


UTC_NOW = datetime(2026, 6, 26, 1, 0, tzinfo=timezone.utc)


def test_replay_store_insert_and_lookup(tmp_path):
    store = ReplayStore(tmp_path / "replay")

    stored = store.record_token(
        token="token-1",
        expires_at=UTC_NOW + timedelta(days=1),
        metadata={"request_id": "request-1"},
    )
    loaded = store.lookup_token("token-1")

    assert stored == loaded
    assert store.exists("token-1") is True


def test_replay_store_duplicate_token_raises(tmp_path):
    store = ReplayStore(tmp_path / "replay")
    store.record_token("token-1", UTC_NOW + timedelta(days=1))

    with pytest.raises(StorageItemAlreadyExists):
        store.record_token("token-1", UTC_NOW + timedelta(days=2))


def test_replay_store_remove_expired_tokens(tmp_path):
    store = ReplayStore(tmp_path / "replay")
    store.record_token("expired", UTC_NOW - timedelta(seconds=1))
    store.record_token("active", UTC_NOW + timedelta(seconds=1))

    removed = store.remove_expired_tokens(now=UTC_NOW)

    assert removed == 1
    assert store.exists("expired") is False
    assert store.exists("active") is True
    with pytest.raises(StorageItemNotFound):
        store.lookup_token("missing")
