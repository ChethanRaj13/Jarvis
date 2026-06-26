import json

from verification_engine.config.verification_config import VerificationConfig
from verification_engine.security.integrity.config_integrity_verifier import (
    ConfigIntegrityVerifier,
)
from verification_engine.security.startup.config_integrity_check import (
    ConfigIntegrityCheck,
    RequiredConfiguration,
)


def valid_verification_config() -> dict:
    return {
        "evidence_collection": {
            "evidence_window_seconds": 30,
            "collection_timeout_seconds": 5,
        },
        "side_effect_detection": {
            "enabled": True,
            "default_scopes": ["FILESYSTEM"],
        },
        "configuration_verification": {},
        "enabled_verifiers": ["FILESYSTEM"],
    }


def write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


def test_config_integrity_verifier_accepts_valid_configuration_data():
    result = ConfigIntegrityVerifier().validate_data(
        valid_verification_config(),
        VerificationConfig,
    )

    assert result.valid is True
    assert result.model_name == "VerificationConfig"
    assert result.errors == ()


def test_config_integrity_verifier_rejects_invalid_configuration_data():
    data = valid_verification_config()
    data["evidence_collection"]["evidence_window_seconds"] = 0

    result = ConfigIntegrityVerifier().validate_data(data, VerificationConfig)

    assert result.valid is False
    assert result.model_name == "VerificationConfig"
    assert result.errors


def test_config_integrity_check_passes_for_existing_readable_valid_config(tmp_path):
    config_path = tmp_path / "verification.json"
    write_json(config_path, valid_verification_config())
    check = ConfigIntegrityCheck(
        (
            RequiredConfiguration(
                name="verification",
                path=config_path,
                model_type=VerificationConfig,
            ),
        )
    )

    result = check.run()

    assert result.passed is True
    assert result.messages == ()


def test_config_integrity_check_fails_for_missing_config(tmp_path):
    check = ConfigIntegrityCheck(
        (
            RequiredConfiguration(
                name="verification",
                path=tmp_path / "missing.json",
                model_type=VerificationConfig,
            ),
        )
    )

    result = check.run()

    assert result.passed is False
    assert "does not exist" in result.messages[0]
