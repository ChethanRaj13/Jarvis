import json

from verification_engine.config.verification_config import VerificationConfig
from verification_engine.security.startup.audit_store_check import (
    AuditStoreCheck,
    AuditStoreRequirement,
)
from verification_engine.security.startup.config_integrity_check import (
    ConfigIntegrityCheck,
    RequiredConfiguration,
    StartupCheckResult,
)
from verification_engine.security.startup.restricted_mode_enforcer import (
    RestrictedModeEnforcer,
)
from verification_engine.security.startup.startup_validator import StartupValidator


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


class PassingCheck:
    def run(self):
        return StartupCheckResult(
            check_name="passing",
            passed=True,
            mandatory=True,
        )


def test_startup_validator_successful_startup(tmp_path):
    config_path = tmp_path / "verification.json"
    audit_path = tmp_path / "audit"
    audit_path.mkdir()
    write_json(config_path, valid_verification_config())
    enforcer = RestrictedModeEnforcer()
    validator = StartupValidator(
        checks=(
            ConfigIntegrityCheck(
                (
                    RequiredConfiguration(
                        name="verification",
                        path=config_path,
                        model_type=VerificationConfig,
                    ),
                )
            ),
            AuditStoreCheck(AuditStoreRequirement(path=audit_path)),
        ),
        restricted_mode_enforcer=enforcer,
    )

    result = validator.validate()

    assert result.startup_allowed is True
    assert result.restricted_mode is False
    assert result.failures == ()
    assert enforcer.is_restricted() is False


def test_startup_validator_configuration_failure_enters_restricted_mode(tmp_path):
    audit_path = tmp_path / "audit"
    audit_path.mkdir()
    enforcer = RestrictedModeEnforcer()
    validator = StartupValidator(
        checks=(
            ConfigIntegrityCheck(
                (
                    RequiredConfiguration(
                        name="verification",
                        path=tmp_path / "missing.json",
                        model_type=VerificationConfig,
                    ),
                )
            ),
            AuditStoreCheck(AuditStoreRequirement(path=audit_path)),
        ),
        restricted_mode_enforcer=enforcer,
    )

    result = validator.validate()

    assert result.startup_allowed is False
    assert result.restricted_mode is True
    assert result.failures[0].check_name == "configuration_integrity"
    assert enforcer.is_restricted() is True


def test_startup_validator_audit_store_failure_enters_restricted_mode(tmp_path):
    config_path = tmp_path / "verification.json"
    write_json(config_path, valid_verification_config())
    enforcer = RestrictedModeEnforcer()
    validator = StartupValidator(
        checks=(
            ConfigIntegrityCheck(
                (
                    RequiredConfiguration(
                        name="verification",
                        path=config_path,
                        model_type=VerificationConfig,
                    ),
                )
            ),
            AuditStoreCheck(AuditStoreRequirement(path=tmp_path / "missing-audit")),
        ),
        restricted_mode_enforcer=enforcer,
    )

    result = validator.validate()

    assert result.startup_allowed is False
    assert result.restricted_mode is True
    assert result.failures[-1].check_name == "audit_store"


def test_startup_validator_ignores_optional_failure_for_startup_gate():
    class OptionalFailureCheck:
        def run(self):
            return StartupCheckResult(
                check_name="optional",
                passed=False,
                mandatory=False,
                messages=("optional warning",),
            )

    enforcer = RestrictedModeEnforcer()
    validator = StartupValidator(
        checks=(PassingCheck(), OptionalFailureCheck()),
        restricted_mode_enforcer=enforcer,
    )

    result = validator.validate()

    assert result.startup_allowed is True
    assert result.restricted_mode is False
    assert len(result.failures) == 1
