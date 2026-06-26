from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from verification_engine.contracts import (
    ActionType,
    AuthorizationRecord,
    RiskLevel,
    VerificationDecisionEnum,
    VerificationRequest,
)
from verification_engine.orchestrator import (
    EarlyExit,
    ExecutionContext,
    ExecutionPipeline,
    InvalidStateTransition,
    OrchestratorState,
    PipelineState,
    PipelineStep,
    StateMachine,
    VerificationOrchestrator,
)


def execution_context(**overrides) -> ExecutionContext:
    request_id = uuid4()
    now = datetime.now(timezone.utc)
    request = VerificationRequest(
        request_id=request_id,
        action_type=ActionType.FILE_CREATE,
        execution_timestamp=now,
        trigger_received_timestamp=now,
        session_id="session-1",
    )
    authorization = AuthorizationRecord(
        authorization_id="auth-1",
        request_id=request_id,
        action_type=ActionType.FILE_CREATE,
        target_resource="C:\\Temp\\artifact.txt",
        authorized_scope={"path": "C:\\Temp\\artifact.txt"},
        risk_level=RiskLevel.LOW,
        authorization_timestamp=now,
        expected_outcome_specification={"exists": True},
        session_id="session-1",
    )
    values = {"request": request, "authorization": authorization}
    values.update(overrides)
    return ExecutionContext(**values)


def test_pipeline_executes_steps_in_order() -> None:
    result = ExecutionPipeline().run(
        1,
        (
            PipelineStep("add", lambda value: value + 1),
            PipelineStep("double", lambda value: value * 2),
        ),
    )

    assert result.state == PipelineState.COMPLETED
    assert result.value == 4
    assert result.completed_steps == ("add", "double")


def test_pipeline_fails_closed_on_step_failure() -> None:
    def fail(_value):
        raise RuntimeError("boom")

    result = ExecutionPipeline().run(1, (PipelineStep("fail", fail),))

    assert result.state == PipelineState.FAILED
    assert result.fail_closed is True
    assert result.failed_step == "fail"


def test_pipeline_supports_early_exit() -> None:
    result = ExecutionPipeline().run(
        1,
        (
            PipelineStep("stop", lambda value: EarlyExit(value=value, reason="done")),
            PipelineStep("never", lambda value: value + 1),
        ),
    )

    assert result.state == PipelineState.EARLY_EXIT
    assert result.value == 1
    assert result.early_exit_reason == "done"
    assert result.completed_steps == ("stop",)


def test_state_machine_allows_legal_transitions() -> None:
    machine = StateMachine()
    machine = machine.transition(OrchestratorState.COLLECTING)
    machine = machine.transition(OrchestratorState.VALIDATING)
    machine = machine.transition(OrchestratorState.VERIFYING)
    machine = machine.transition(OrchestratorState.ANALYZING)
    machine = machine.transition(OrchestratorState.DECIDING)
    machine = machine.transition(OrchestratorState.COMPLETED)

    assert machine.state == OrchestratorState.COMPLETED


def test_state_machine_rejects_illegal_transitions() -> None:
    with pytest.raises(InvalidStateTransition):
        StateMachine().transition(OrchestratorState.COMPLETED)


def test_orchestrator_completes_pipeline_and_fails_closed_without_results() -> None:
    outcome = VerificationOrchestrator().execute(execution_context())

    assert outcome.pipeline_state == PipelineState.COMPLETED
    assert outcome.completed_steps == ("collect", "validate", "verify", "analyze", "decide", "complete")
    assert outcome.decision.final_decision == VerificationDecisionEnum.ESCALATE
    assert outcome.escalation_plan is not None


def test_orchestrator_fails_closed_on_collector_failure() -> None:
    class FailingCollector:
        def collect(self, _request):
            raise RuntimeError("collection unavailable")

    context = execution_context(collection_requests=(object(),))

    outcome = VerificationOrchestrator(collectors=(FailingCollector(),)).execute(context)

    assert outcome.pipeline_state == PipelineState.FAILED
    assert outcome.fail_closed is True
    assert outcome.decision.final_decision == VerificationDecisionEnum.ESCALATE
    assert "collection unavailable" in outcome.error
