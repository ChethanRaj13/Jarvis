from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from WindowsAIAssistant.backend.verification_engine.contracts import (
    ActionType,
    AuthorizationRecord,
    EvidenceMetadata,
    EvidenceReference,
    EvidenceType,
    ExecutionCompletionSignal,
    FilesystemEvidence,
    RegistryEvidence,
    SideEffectChange,
    SideEffectReport,
    SideEffectSurface,
    TaskEvidence,
    UnauthorizedSideEffectChange,
    ValidationStatus,
    VerificationDecision,
    VerificationDecisionEnum,
    VerificationOutcomeMessage,
    VerificationRequest,
    VerificationResult,
    VerifierID,
)


UTC_NOW = datetime(2026, 6, 26, 1, 0, tzinfo=timezone.utc)
HASH = "a" * 64


def test_execution_completion_signal_serialization_round_trip():
    request_id = uuid4()
    signal = ExecutionCompletionSignal(
        request_id=request_id,
        action_type=ActionType.FILE_CREATE,
        execution_timestamp=UTC_NOW,
        execution_layer_id="execution-layer",
    )

    data = signal.model_dump_json()
    restored = ExecutionCompletionSignal.model_validate_json(data)

    assert restored == signal
    assert restored.request_id == request_id


def test_utc_timestamp_validation():
    with pytest.raises(ValidationError):
        ExecutionCompletionSignal(
            request_id=uuid4(),
            action_type=ActionType.DOWNLOAD,
            execution_timestamp=datetime(2026, 6, 26, 1, 0),
            execution_layer_id="execution-layer",
        )


def test_verification_request_requires_ordered_timestamps():
    with pytest.raises(ValidationError):
        VerificationRequest(
            request_id=uuid4(),
            action_type=ActionType.FILE_DELETE,
            execution_timestamp=UTC_NOW,
            trigger_received_timestamp=UTC_NOW - timedelta(seconds=1),
            session_id="session-1",
        )


def test_authorization_record_is_immutable_and_validates_non_empty_scope():
    record = AuthorizationRecord(
        authorization_id="auth-1",
        request_id=uuid4(),
        action_type=ActionType.PROCESS_LAUNCH,
        target_resource="C:\\Windows\\System32\\cmd.exe",
        authorized_scope={"path": "C:\\Windows\\System32\\cmd.exe"},
        risk_level="HIGH",
        authorization_timestamp=UTC_NOW,
        expected_outcome_specification={"exists": True},
    )

    with pytest.raises(ValidationError):
        AuthorizationRecord(
            authorization_id="auth-1",
            request_id=uuid4(),
            action_type=ActionType.PROCESS_LAUNCH,
            target_resource="target",
            authorized_scope={},
            risk_level="HIGH",
            authorization_timestamp=UTC_NOW,
            expected_outcome_specification={"exists": True},
        )
    with pytest.raises(ValidationError):
        record.authorization_id = "changed"


def test_evidence_metadata_invalid_requires_reason():
    with pytest.raises(ValidationError):
        EvidenceMetadata(
            evidence_id=uuid4(),
            request_id=uuid4(),
            collection_timestamp=UTC_NOW,
            evidence_window_seconds=30,
            time_since_execution_ms=10,
            within_window=False,
            binding_token="token",
            evidence_type=EvidenceType.FILESYSTEM,
            collection_api="api",
            validation_status=ValidationStatus.INVALID,
            validation_timestamp=UTC_NOW,
        )


def test_typed_evidence_validation():
    FilesystemEvidence(
        file_path="C:\\temp\\a.txt",
        exists=True,
        file_size_bytes=1,
        sha256_hash=HASH,
        creation_timestamp_utc=UTC_NOW,
        last_modified_timestamp_utc=UTC_NOW,
        file_attributes={"archive": True},
        owner_sid="S-1",
        dacl_summary={"entries": []},
    )
    with pytest.raises(ValidationError):
        RegistryEvidence(
            key_path="Software\\Example",
            key_exists=True,
            value_name="Name",
            value_type="REG_SZ",
            value_data="data",
            key_last_written_timestamp=UTC_NOW,
            subkey_names=[],
            parent_key_last_written_timestamp=UTC_NOW,
            is_in_protected_hive=False,
        )
    with pytest.raises(ValidationError):
        TaskEvidence(
            task_name="TaskOnly",
            task_exists=True,
            executable_path="C:\\tool.exe",
            arguments=[],
            working_directory="C:\\",
            run_as_user="User",
            highest_run_level=False,
            triggers=[{"type": "daily"}],
            task_state="Ready",
            creation_date=UTC_NOW,
            last_run_time=UTC_NOW,
            adjacent_tasks=[],
        )


def test_verification_result_decision_validation():
    with pytest.raises(ValidationError):
        VerificationResult(
            result_id=uuid4(),
            request_id=uuid4(),
            verifier_id=VerifierID.FILESYSTEM,
            sub_decision=VerificationDecisionEnum.FAILED,
            confirmed_attributes=[],
            failed_attributes=[],
            evidence_reference=uuid4(),
            sub_decision_rationale="missing failure",
            result_timestamp=UTC_NOW,
        )


def test_verification_decision_requires_controlling_subset_and_escalation_expiry():
    result_id = uuid4()
    VerificationDecision(
        decision_id=uuid4(),
        request_id=uuid4(),
        final_decision=VerificationDecisionEnum.VERIFIED,
        controlling_results=[result_id],
        full_rationale="all good",
        all_results=[result_id],
        decision_timestamp=UTC_NOW,
        decision_engine_version="1",
    )
    with pytest.raises(ValidationError):
        VerificationDecision(
            decision_id=uuid4(),
            request_id=uuid4(),
            final_decision=VerificationDecisionEnum.ESCALATE,
            controlling_results=[result_id],
            full_rationale="needs review",
            all_results=[result_id],
            decision_timestamp=UTC_NOW,
            decision_engine_version="1",
        )


def test_side_effect_and_outcome_validation():
    report = SideEffectReport(
        report_id=uuid4(),
        request_id=uuid4(),
        detection_scope="session",
        authorized_changes=[SideEffectChange(path_or_key="C:\\temp", change_type="WRITE", surface=SideEffectSurface.FILESYSTEM)],
        unauthorized_changes=[
            UnauthorizedSideEffectChange(
                path_or_key="HKLM\\Software",
                change_type="MODIFY",
                surface=SideEffectSurface.REGISTRY,
                severity="HIGH",
            )
        ],
        side_effect_sub_decision=VerificationDecisionEnum.FAILED,
        detection_timestamp=UTC_NOW,
    )
    dumped = report.model_dump(mode="json")
    assert dumped["unauthorized_changes"][0]["severity"] == "HIGH"

    with pytest.raises(ValidationError):
        VerificationOutcomeMessage(
            request_id=uuid4(),
            final_decision=VerificationDecisionEnum.PARTIAL,
            record_id=uuid4(),
            audit_integrity_hash=HASH,
            decision_timestamp=UTC_NOW,
        )


def test_evidence_reference_deserialization():
    evidence_id = uuid4()
    data = {
        "evidence_id": str(evidence_id),
        "evidence_type": "DOWNLOAD",
        "collection_timestamp": UTC_NOW.isoformat(),
        "within_window": True,
        "binding_token_valid": True,
        "resolution_status": "RESOLVED",
    }
    reference = EvidenceReference.model_validate(data)

    assert reference.evidence_id == UUID(str(evidence_id))
    assert reference.evidence_type == EvidenceType.DOWNLOAD
