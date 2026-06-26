import json

import pytest

from WindowsAIAssistant.backend.verification_engine.config.exceptions import (
    ConfigurationFileNotFound,
    ConfigurationParseError,
    ConfigurationValidationError,
)
from WindowsAIAssistant.backend.verification_engine.config.loader import JsonConfigLoader
from WindowsAIAssistant.backend.verification_engine.config.verification_config import VerificationConfig


def verification_config_data() -> dict:
    return {
        "evidence_collection": {
            "evidence_window_seconds": 30,
            "collection_timeout_seconds": 5,
            "max_collection_retries": 1,
        },
        "side_effect_detection": {
            "enabled": True,
            "default_scopes": ["FILESYSTEM", "REGISTRY"],
            "protected_paths": ["C:/Windows/System32"],
        },
        "configuration_verification": {
            "safety_config_paths": ["C:/configs/safety.json"],
            "policy_config_paths": ["C:/configs/policy.json"],
            "require_pre_execution_baseline": True,
        },
        "enabled_verifiers": ["FILESYSTEM", "CONFIGURATION", "SIDE_EFFECT"],
        "verification_policy_file_locations": ["C:/configs/verification-policy.json"],
    }


def write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


def test_load_json_success_and_cache(tmp_path):
    config_path = tmp_path / "verification.json"
    write_json(config_path, {"name": "verification", "version": 1})
    loader = JsonConfigLoader()

    first = loader.load_json(config_path)
    config_path.write_text('{"name": "changed"}', encoding="utf-8")
    second = loader.load_json(config_path)

    assert first is second
    assert second["name"] == "verification"
    with pytest.raises(TypeError):
        second["name"] = "changed"


def test_missing_file_raises_typed_exception(tmp_path):
    loader = JsonConfigLoader()

    with pytest.raises(ConfigurationFileNotFound):
        loader.load_json(tmp_path / "missing.json")


def test_invalid_json_raises_parse_exception(tmp_path):
    config_path = tmp_path / "invalid.json"
    config_path.write_text("{invalid", encoding="utf-8")
    loader = JsonConfigLoader()

    with pytest.raises(ConfigurationParseError):
        loader.load_json(config_path)


def test_non_object_json_raises_parse_exception(tmp_path):
    config_path = tmp_path / "array.json"
    config_path.write_text("[]", encoding="utf-8")
    loader = JsonConfigLoader()

    with pytest.raises(ConfigurationParseError):
        loader.load_json(config_path)


def test_load_model_success(tmp_path):
    config_path = tmp_path / "verification.json"
    write_json(config_path, verification_config_data())
    loader = JsonConfigLoader()

    config = loader.load_model(config_path, VerificationConfig)

    assert config.evidence_collection.evidence_window_seconds == 30
    assert config.enabled_verifiers[-1].value == "SIDE_EFFECT"


def test_load_model_validation_failure_raises_typed_exception(tmp_path):
    data = verification_config_data()
    data["evidence_collection"]["evidence_window_seconds"] = 0
    config_path = tmp_path / "verification.json"
    write_json(config_path, data)
    loader = JsonConfigLoader()

    with pytest.raises(ConfigurationValidationError):
        loader.load_model(config_path, VerificationConfig)
