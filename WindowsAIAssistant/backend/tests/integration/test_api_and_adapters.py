from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from WindowsAIAssistant.backend.verification_engine.api.trigger import VerificationTriggerService
from WindowsAIAssistant.backend.verification_engine.contracts import (
    ActionType,
    AuthorizationRecord,
    ExecutionCompletionSignal,
    RiskLevel,
    VerificationDecisionEnum,
)
from WindowsAIAssistant.backend.verification_engine.integrations import (
    CompletionReportingAdapter,
    ExecutionLayerTriggerAdapter,
    SafetyEngineAuthorizationAdapter,
)
from WindowsAIAssistant.backend.verification_engine.orchestrator import ExecutionContext, VerificationOrchestrator


UTC_NOW = datetime(2026, 6, 26, 1, 0, tzinfo=timezone.utc)
HASH = "a" * 64


def signal(request_id=None) -> ExecutionCompletionSignal:
    return ExecutionCompletionSignal(
        request_id=request_id or uuid4(),
        action_type=ActionType.FILE_CREATE,
        execution_timestamp=UTC_NOW,
        execution_layer_id="execution-layer",
    )


def authorization(request_id, *, scope=None, expected=None) -> AuthorizationRecord:
    return AuthorizationRecord(
        authorization_id="auth-1",
        request_id=request_id,
        action_type=ActionType.FILE_CREATE,
        target_resource="C:/Temp/example.txt",
        authorized_scope=scope or {"exists": True},
        risk_level=RiskLevel.LOW,
        authorization_timestamp=UTC_NOW,
        expected_outcome_specification=expected or {"exists": True},
        session_id="session-1",
    )


def filesystem_raw(**overrides):
    raw = {
        "file_path": "C:/Temp/example.txt",
        "exists": True,
        "file_size_bytes": 10,
        "sha256_hash": HASH,
        "creation_timestamp_utc": UTC_NOW,
        "last_modified_timestamp_utc": UTC_NOW,
        "file_attributes": {"archive": True},
        "owner_sid": "S-1",
        "dacl_summary": {"entries": []},
    }
    raw.update(overrides)
    return raw


def service_for(record: AuthorizationRecord) -> VerificationTriggerService:
    completion = CompletionReportingAdapter()
    return VerificationTriggerService(
        execution_adapter=ExecutionLayerTriggerAdapter(
            session_id_resolver=lambda _signal: "session-1",
            clock=lambda: UTC_NOW,
        ),
        safety_adapter=SafetyEngineAuthorizationAdapter(authorization_records={record.request_id: record}),
        completion_adapter=completion,
        context_factory=lambda request, auth: ExecutionContext(
            request=request,
            authorization=auth,
            collection_requests=(),
            validation_context=None,
        ),
        orchestrator_factory=lambda _context: VerificationOrchestrator(),
        clock=lambda: UTC_NOW,
    )


def test_execution_layer_adapter_translates_signal_to_verification_request():
    incoming = signal()

    request = ExecutionLayerTriggerAdapter(
        session_id_resolver=lambda _signal: "session-1",
        clock=lambda: UTC_NOW,
    ).receive_signal(incoming)

    assert request is not None
    assert request.request_id == incoming.request_id
    assert request.session_id == "session-1"
    assert request.execution_layer_id == "execution-layer"


def test_safety_engine_adapter_retrieves_and_validates_authorization():
    request_id = uuid4()
    record = authorization(request_id)
    adapter = SafetyEngineAuthorizationAdapter(authorization_records={request_id: record})

    retrieved = adapter.retrieve_authorization(
        request=__import__("verification_engine.contracts", fromlist=["AuthorizationRetrievalRequest"]).AuthorizationRetrievalRequest(
            request_id=request_id,
            requester_id="test",
            retrieval_timestamp=UTC_NOW,
        )
    )

    assert retrieved == record


def test_completion_adapter_delivers_outcome_to_sink():
    delivered = []
    adapter = CompletionReportingAdapter(outcome_sink=delivered.append)
    record = authorization(uuid4())
    decision = service_for(record).verify(signal(record.request_id))

    adapter.deliver_outcome(
        __import__("verification_engine.contracts", fromlist=["VerificationOutcomeMessage"]).VerificationOutcomeMessage(
            request_id=decision.request_id,
            final_decision=decision.final_decision,
            record_id=decision.decision_id,
            audit_integrity_hash="0" * 64,
            decision_timestamp=decision.decision_timestamp,
            escalation_expiry=decision.escalation_expiry,
        )
    )

    assert delivered


def test_verify_endpoint_returns_decision():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from WindowsAIAssistant.backend.verification_engine.api.app import create_app
    from WindowsAIAssistant.backend.verification_engine.api.dependencies import get_verification_service

    request_id = uuid4()
    app = create_app()
    app.dependency_overrides[get_verification_service] = lambda: service_for(authorization(request_id))

    response = TestClient(app).post("/verify", json=signal(request_id).model_dump(mode="json"))

    assert response.status_code == 200
    assert response.json()["final_decision"] == VerificationDecisionEnum.ESCALATE.value


def test_verify_endpoint_rejects_malformed_request_with_validation_error():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from WindowsAIAssistant.backend.verification_engine.api.app import create_app

    response = TestClient(create_app()).post("/verify", json={"request_id": "not-a-uuid"})

    assert response.status_code == 422


def test_verify_endpoint_returns_bad_request_for_invalid_trigger():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from WindowsAIAssistant.backend.verification_engine.api.app import create_app
    from WindowsAIAssistant.backend.verification_engine.api.dependencies import get_verification_service

    request_id = uuid4()
    app = create_app()
    service = VerificationTriggerService(
        execution_adapter=ExecutionLayerTriggerAdapter(clock=lambda: datetime(2020, 1, 1, tzinfo=timezone.utc)),
        safety_adapter=SafetyEngineAuthorizationAdapter(authorization_records={request_id: authorization(request_id)}),
        clock=lambda: UTC_NOW,
    )
    app.dependency_overrides[get_verification_service] = lambda: service

    response = TestClient(app).post("/verify", json=signal(request_id).model_dump(mode="json"))

    assert response.status_code == 400
