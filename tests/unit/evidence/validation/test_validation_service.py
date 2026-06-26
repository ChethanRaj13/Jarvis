from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from verification_engine.config.verification_config import EvidenceCollectionConfig
from verification_engine.contracts import EvidencePackage, EvidenceType
from verification_engine.evidence.validation import (
    BaseValidator,
    BindingValidator,
    CompletenessValidator,
    ValidationContext,
    ValidationResult,
    ValidationService,
    WindowValidationError,
    WindowValidator,
)


UTC_NOW = datetime(2026, 6, 26, 1, 0, tzinfo=timezone.utc)
HASH = "a" * 64


def filesystem_payload() -> dict:
    return {
        "file_path": "C:\\Temp\\example.txt",
        "exists": True,
        "file_size_bytes": 10,
        "sha256_hash": HASH,
        "creation_timestamp_utc": UTC_NOW.isoformat(),
        "last_modified_timestamp_utc": UTC_NOW.isoformat(),
        "file_attributes": {"archive": True},
        "owner_sid": "S-1",
        "dacl_summary": {"entries": []},
    }


def evidence_package(
    *,
    request_id=None,
    evidence_type=EvidenceType.FILESYSTEM,
    collection_timestamp=UTC_NOW,
    collection_window_open=True,
    payload=None,
) -> EvidencePackage:
    return EvidencePackage(
        evidence_id=uuid4(),
        request_id=request_id or uuid4(),
        evidence_type=evidence_type,
        collection_timestamp=collection_timestamp,
        collection_window_open=collection_window_open,
        binding_token="binding-token",
        collector_id="collector",
        evidence_payload=payload or filesystem_payload(),
    )


def context_for(request_id, *, window_seconds=30) -> ValidationContext:
    return ValidationContext(
        request_id=request_id,
        execution_timestamp=UTC_NOW,
        evidence_window_seconds=window_seconds,
    )


def test_window_validator_passes_inside_window():
    evidence = evidence_package(collection_timestamp=UTC_NOW + timedelta(seconds=10))
    result = WindowValidator().validate(evidence, context_for(evidence.request_id))

    assert result.passed is True
    assert result.validator_name == "window"


def test_window_validator_fails_outside_window():
    evidence = evidence_package(collection_timestamp=UTC_NOW + timedelta(seconds=31))
    result = WindowValidator().validate(evidence, context_for(evidence.request_id, window_seconds=30))

    assert result.passed is False
    assert result.reason == "evidence outside permitted window"


def test_window_validator_uses_ticket_2_config():
    evidence = evidence_package(collection_timestamp=UTC_NOW + timedelta(seconds=45))
    config = EvidenceCollectionConfig(
        evidence_window_seconds=60,
        collection_timeout_seconds=5,
    )
    result = WindowValidator(config=config).validate(evidence, context_for(evidence.request_id, window_seconds=1))

    assert result.passed is True


def test_window_validator_raises_typed_exception_for_invalid_window():
    evidence = evidence_package()

    with pytest.raises(WindowValidationError):
        WindowValidator(evidence_window_seconds=0).validate(evidence, context_for(evidence.request_id))


def test_binding_validator_passes_when_request_matches():
    evidence = evidence_package()
    result = BindingValidator().validate(evidence, context_for(evidence.request_id))

    assert result.passed is True


def test_binding_validator_fails_when_request_mismatches():
    evidence = evidence_package()
    result = BindingValidator().validate(evidence, context_for(uuid4()))

    assert result.passed is False
    assert "request_id" in result.reason


def test_completeness_validator_passes_for_complete_filesystem_payload():
    evidence = evidence_package()
    result = CompletenessValidator().validate(evidence, context_for(evidence.request_id))

    assert result.passed is True
    assert result.details["missing_fields"] == ()


def test_completeness_validator_fails_for_missing_required_field():
    payload = filesystem_payload()
    payload.pop("file_path")
    evidence = evidence_package(payload=payload)
    result = CompletenessValidator().validate(evidence, context_for(evidence.request_id))

    assert result.passed is False
    assert result.details["missing_fields"] == ("file_path",)


def test_completeness_validator_supports_context_required_field_override():
    evidence = evidence_package(payload={"custom": "value"})
    context = ValidationContext(
        request_id=evidence.request_id,
        execution_timestamp=UTC_NOW,
        evidence_window_seconds=30,
        required_fields={EvidenceType.FILESYSTEM.value: ("custom",)},
    )

    result = CompletenessValidator().validate(evidence, context)

    assert result.passed is True


def test_base_validator_rejects_invalid_input_type():
    class NoopValidator(BaseValidator):
        name = "noop"

        def _execute(self, evidence, context):
            return ValidationResult(validator_name=self.name, passed=True)

    with pytest.raises(Exception):
        NoopValidator().validate(object(), object())


def test_validation_service_passes_all_validators():
    evidence = evidence_package()
    result = ValidationService().validate(evidence, context_for(evidence.request_id))

    assert result.passed is True
    assert result.fail_closed is False
    assert [item.validator_name for item in result.results] == ["window", "binding", "completeness"]


def test_validation_service_fails_closed_on_mandatory_failure():
    evidence = evidence_package(collection_timestamp=UTC_NOW + timedelta(minutes=5))
    result = ValidationService().validate(evidence, context_for(evidence.request_id))

    assert result.passed is False
    assert result.fail_closed is True
    assert result.results[0].validator_name == "window"
    assert result.results[0].passed is False
