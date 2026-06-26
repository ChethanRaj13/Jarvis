import json

import pytest
from pydantic import ValidationError

from WindowsAIAssistant.backend.verification_engine.config.audit_config import AuditConfig
from WindowsAIAssistant.backend.verification_engine.config.config_loader import ConfigurationLoader
from WindowsAIAssistant.backend.verification_engine.config.storage_config import StorageConfig
from WindowsAIAssistant.backend.verification_engine.config.verification_config import VerificationConfig


def write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


def verification_config_data() -> dict:
    return {
        "evidence_collection": {
            "evidence_window_seconds": 45,
            "collection_timeout_seconds": 10,
        },
        "side_effect_detection": {
            "enabled": True,
            "default_scopes": ["FILESYSTEM"],
        },
        "configuration_verification": {},
        "enabled_verifiers": ["FILESYSTEM"],
    }


def storage_config_data() -> dict:
    return {
        "evidence_storage": {
            "root_path": "C:/verification/evidence",
            "max_evidence_package_bytes": 1024,
        },
        "audit_storage": {
            "root_path": "C:/verification/audit",
        },
        "replay_storage": {
            "root_path": "C:/verification/replay",
            "ttl_seconds": 60,
        },
        "drift_storage": {
            "root_path": "C:/verification/drift",
            "retention_days": 30,
        },
        "pending_storage": {
            "root_path": "C:/verification/pending",
            "expiry_seconds": 300,
        },
    }


def audit_config_data() -> dict:
    return {
        "retention": {
            "retention_days": 90,
            "minimum_records_to_keep": 1,
        },
        "hashing": {
            "algorithm": "SHA256",
            "digest_length": 64,
        },
        "chain": {
            "enabled": True,
            "verify_on_startup": True,
            "verification_interval_seconds": 300,
        },
        "persistence": {
            "enabled": True,
            "append_only": True,
            "audit_record_path": "C:/verification/audit/records.jsonl",
        },
    }


def test_configuration_loader_is_singleton():
    assert ConfigurationLoader() is ConfigurationLoader()


def test_configuration_loader_lazy_cache_behavior(tmp_path):
    config_path = tmp_path / "verification.json"
    write_json(config_path, verification_config_data())
    loader = ConfigurationLoader()
    loader.clear_cache()

    first = loader.get_verification_config(config_path)
    changed = verification_config_data()
    changed["evidence_collection"]["evidence_window_seconds"] = 90
    write_json(config_path, changed)
    second = loader.get_verification_config(config_path)

    assert first is second
    assert second.evidence_collection.evidence_window_seconds == 45


def test_configuration_loader_can_clear_cache(tmp_path):
    config_path = tmp_path / "verification.json"
    write_json(config_path, verification_config_data())
    loader = ConfigurationLoader()
    loader.clear_cache()

    first = loader.get_verification_config(config_path)
    loader.clear_cache()
    changed = verification_config_data()
    changed["evidence_collection"]["evidence_window_seconds"] = 90
    write_json(config_path, changed)
    second = loader.get_verification_config(config_path)

    assert first is not second
    assert second.evidence_collection.evidence_window_seconds == 90


def test_configuration_models_are_read_only(tmp_path):
    config_path = tmp_path / "verification.json"
    write_json(config_path, verification_config_data())
    loader = ConfigurationLoader()
    loader.clear_cache()

    config = loader.get_verification_config(config_path)

    with pytest.raises(ValidationError):
        config.evidence_collection.evidence_window_seconds = 1


def test_storage_config_validation_success(tmp_path):
    config_path = tmp_path / "storage.json"
    write_json(config_path, storage_config_data())
    loader = ConfigurationLoader()
    loader.clear_cache()

    config = loader.get_storage_config(config_path)

    assert isinstance(config, StorageConfig)
    assert config.audit_storage.integrity_chain_required is True


def test_audit_config_validation_success(tmp_path):
    config_path = tmp_path / "audit.json"
    write_json(config_path, audit_config_data())
    loader = ConfigurationLoader()
    loader.clear_cache()

    config = loader.get_audit_config(config_path)

    assert isinstance(config, AuditConfig)
    assert config.hashing.algorithm == "SHA256"


def test_audit_config_rejects_disabled_chain(tmp_path):
    data = audit_config_data()
    data["chain"]["enabled"] = False
    config_path = tmp_path / "audit.json"
    write_json(config_path, data)

    with pytest.raises(ValidationError):
        AuditConfig.model_validate(data)
