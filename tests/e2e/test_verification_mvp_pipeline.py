from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from verification_engine.api.dependencies import build_execution_context, build_orchestrator
from verification_engine.api.trigger import VerificationTriggerService
from verification_engine.contracts import (
    ActionType,
    AuthorizationRecord,
    EvidencePackage,
    EvidenceType,
    ExecutionCompletionSignal,
    RiskLevel,
    VerificationDecisionEnum,
    VerificationResult,
    VerifierID,
)
from verification_engine.integrations import (
    CompletionReportingAdapter,
    ExecutionLayerTriggerAdapter,
    SafetyEngineAuthorizationAdapter,
)
from verification_engine.orchestrator import ExecutionContext, VerificationOrchestrator


HASH = "a" * 64


def filesystem_raw(**overrides):
    now = datetime.now(timezone.utc)
    raw = {
        "file_path": "C:/Temp/example.txt",
        "exists": True,
        "file_size_bytes": 10,
        "sha256_hash": HASH,
        "creation_timestamp_utc": now,
        "last_modified_timestamp_utc": now,
        "file_attributes": {"archive": True},
        "owner_sid": "S-1",
        "dacl_summary": {"entries": []},
    }
    raw.update(overrides)
    return raw


def auth(request_id, *, scope, raw_evidence) -> AuthorizationRecord:
    now = datetime.now(timezone.utc)
    return AuthorizationRecord(
        authorization_id="auth-1",
        request_id=request_id,
        action_type=ActionType.FILE_CREATE,
        target_resource="C:/Temp/example.txt",
        authorized_scope=scope,
        risk_level=RiskLevel.LOW,
        authorization_timestamp=now,
        expected_outcome_specification={"raw_evidence": raw_evidence},
        session_id="session-1",
    )


def payload(request_id):
    return ExecutionCompletionSignal(
        request_id=request_id,
        action_type=ActionType.FILE_CREATE,
        execution_timestamp=datetime.now(timezone.utc),
        execution_layer_id="execution-layer",
    ).model_dump(mode="json")


def service_for(record: AuthorizationRecord) -> VerificationTriggerService:
    return VerificationTriggerService(
        execution_adapter=ExecutionLayerTriggerAdapter(
            session_id_resolver=lambda _signal: "session-1",
            clock=lambda: datetime.now(timezone.utc),
        ),
        safety_adapter=SafetyEngineAuthorizationAdapter(authorization_records={record.request_id: record}),
        completion_adapter=CompletionReportingAdapter(),
        context_factory=build_execution_context,
        orchestrator_factory=build_orchestrator,
        clock=lambda: datetime.now(timezone.utc),
    )


def post_decision(record: AuthorizationRecord) -> str:
    decision = service_for(record).verify(ExecutionCompletionSignal.model_validate(payload(record.request_id)))
    return decision.final_decision.value


def test_successful_verification_returns_verified():
    request_id = uuid4()
    record = auth(
        request_id,
        scope={"exists": True, "file_size_bytes": 10, "sha256_hash": HASH},
        raw_evidence=filesystem_raw(),
    )

    assert post_decision(record) == VerificationDecisionEnum.VERIFIED.value


def test_filesystem_mismatch_returns_failed():
    request_id = uuid4()
    record = auth(
        request_id,
        scope={"exists": True, "file_size_bytes": 20},
        raw_evidence=filesystem_raw(file_size_bytes=10),
    )

    assert post_decision(record) == VerificationDecisionEnum.FAILED.value


def test_missing_evidence_scope_returns_partial():
    request_id = uuid4()
    record = auth(
        request_id,
        scope={"exists": True},
        raw_evidence=filesystem_raw(),
    )

    class PartialCollector:
        def collect(self, _request):
            return EvidencePackage(
                evidence_id=uuid4(),
                request_id=request_id,
                evidence_type=EvidenceType.FILESYSTEM,
                collection_timestamp=datetime.now(timezone.utc),
                collection_window_open=True,
                binding_token="binding-token",
                collector_id="partial-collector",
                evidence_payload=filesystem_raw(),
            )

    class PartialVerifier:
        def verify(self, authorization, evidence):
            return VerificationResult(
                result_id=uuid4(),
                request_id=authorization.request_id,
                verifier_id=VerifierID.FILESYSTEM,
                sub_decision=VerificationDecisionEnum.PARTIAL,
                confirmed_attributes=["exists"],
                failed_attributes=[],
                evidence_reference=evidence.evidence_id,
                sub_decision_rationale="filesystem evidence confirmed primary target; optional metadata was unavailable",
                result_timestamp=datetime.now(timezone.utc),
            )

    service = VerificationTriggerService(
        execution_adapter=ExecutionLayerTriggerAdapter(
            session_id_resolver=lambda _signal: "session-1",
            clock=lambda: datetime.now(timezone.utc),
        ),
        safety_adapter=SafetyEngineAuthorizationAdapter(authorization_records={record.request_id: record}),
        completion_adapter=CompletionReportingAdapter(),
        context_factory=lambda request, authorization: ExecutionContext(
            request=request,
            authorization=authorization,
            collection_requests=(object(),),
        ),
        orchestrator_factory=lambda _context: VerificationOrchestrator(
            collectors=(PartialCollector(),),
            verifiers=(PartialVerifier(),),
        ),
        clock=lambda: datetime.now(timezone.utc),
    )

    decision = service.verify(ExecutionCompletionSignal.model_validate(payload(record.request_id)))

    assert decision.final_decision == VerificationDecisionEnum.PARTIAL


def test_evidence_collection_failure_returns_escalate():
    request_id = uuid4()
    record = auth(
        request_id,
        scope={"exists": True},
        raw_evidence={"file_path": "C:/Temp/example.txt", "exists": True},
    )

    assert post_decision(record) == VerificationDecisionEnum.ESCALATE.value


def test_malformed_request_returns_http_validation_error():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from verification_engine.api.app import create_app
    from verification_engine.api.dependencies import get_verification_service

    record = auth(uuid4(), scope={"exists": True}, raw_evidence=filesystem_raw())
    app = create_app()
    app.dependency_overrides[get_verification_service] = lambda: service_for(record)
    response = TestClient(app).post("/verify", json={"request_id": "bad"})

    assert response.status_code == 422
