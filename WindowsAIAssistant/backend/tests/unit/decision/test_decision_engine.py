from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from WindowsAIAssistant.backend.verification_engine.contracts import (
    DriftReport,
    SideEffectReport,
    SideEffectSeverity,
    SideEffectSurface,
    UnauthorizedSideEffectChange,
    VerificationDecisionEnum,
    VerificationResult,
    VerifierID,
)
from WindowsAIAssistant.backend.verification_engine.decision import (
    DecisionAggregator,
    DecisionContext,
    DecisionSignal,
    DecisionSignalCategory,
    EscalationAction,
    EscalationEngine,
    InvalidDecisionInput,
    PrecedenceResolution,
    PrecedenceResolver,
)


def verification_result(decision: VerificationDecisionEnum = VerificationDecisionEnum.VERIFIED) -> VerificationResult:
    failed = ["path"] if decision == VerificationDecisionEnum.FAILED else []
    confirmed = ["path"] if decision != VerificationDecisionEnum.ESCALATE else []
    return VerificationResult(
        result_id=uuid4(),
        request_id=uuid4(),
        verifier_id=VerifierID.FILESYSTEM,
        sub_decision=decision,
        confirmed_attributes=confirmed,
        failed_attributes=failed,
        evidence_reference=uuid4(),
        sub_decision_rationale=f"{decision.value} rationale",
        result_timestamp=datetime.now(timezone.utc),
    )


def side_effect_report(
    request_id,
    decision: VerificationDecisionEnum = VerificationDecisionEnum.VERIFIED,
    severity: SideEffectSeverity | None = None,
) -> SideEffectReport:
    unauthorized = []
    if severity is not None:
        unauthorized.append(
            UnauthorizedSideEffectChange(
                path_or_key="C:\\Temp\\extra.txt",
                change_type="created",
                surface=SideEffectSurface.FILESYSTEM,
                severity=severity,
            )
        )
    return SideEffectReport(
        report_id=uuid4(),
        request_id=request_id,
        detection_scope="filesystem",
        authorized_changes=[],
        unauthorized_changes=unauthorized,
        side_effect_sub_decision=decision,
        detection_timestamp=datetime.now(timezone.utc),
    )


def drift_report(request_id, decision: VerificationDecisionEnum = VerificationDecisionEnum.VERIFIED) -> DriftReport:
    return DriftReport(
        report_id=uuid4(),
        session_id="session-1",
        request_id=request_id,
        attribution_findings=[],
        drift_findings=[],
        drift_sub_decision=decision,
        detection_timestamp=datetime.now(timezone.utc),
        cumulative_unattributed_count=0,
    )


def test_aggregator_collects_success_signals() -> None:
    result = verification_result()

    context = DecisionAggregator().aggregate(
        request_id=result.request_id,
        verification_results=(result,),
        side_effect_report=side_effect_report(result.request_id),
        drift_report=drift_report(result.request_id),
    )

    assert context.request_id == result.request_id
    assert len(context.signals) == 3
    assert context.confidence == 1.0
    assert all(signal.category == DecisionSignalCategory.SUCCESS for signal in context.signals)


def test_aggregator_fails_closed_when_mandatory_reports_are_missing() -> None:
    result = verification_result()

    context = DecisionAggregator().aggregate(
        request_id=result.request_id,
        verification_results=(result,),
        side_effect_report=None,
        drift_report=None,
    )

    assert any(signal.category == DecisionSignalCategory.ESCALATION for signal in context.signals)
    assert context.confidence == 0.0


def test_aggregator_rejects_mismatched_request_ids() -> None:
    result = verification_result()

    with pytest.raises(InvalidDecisionInput):
        DecisionAggregator().aggregate(
            request_id=uuid4(),
            verification_results=(result,),
            side_effect_report=None,
            drift_report=None,
        )


def test_precedence_resolver_selects_highest_priority_signal() -> None:
    critical = DecisionSignal(
        DecisionSignalCategory.CRITICAL_FAILURE,
        VerificationDecisionEnum.FAILED,
        uuid4(),
        "critical side effect",
    )
    verification_failure = DecisionSignal(
        DecisionSignalCategory.VERIFICATION_FAILURE,
        VerificationDecisionEnum.FAILED,
        uuid4(),
        "attribute mismatch",
    )
    context = DecisionContext(
        request_id=uuid4(),
        signals=(verification_failure, critical),
        all_result_ids=(verification_failure.source_id, critical.source_id),
        confidence=1.0,
        rationale="mixed failures",
    )

    resolution = PrecedenceResolver().resolve(context)

    assert resolution.final_decision == VerificationDecisionEnum.FAILED
    assert resolution.controlling_results == (critical.source_id,)
    assert "critical" in resolution.rationale


def test_precedence_resolver_handles_success_and_partial() -> None:
    partial = DecisionSignal(
        DecisionSignalCategory.PARTIAL,
        VerificationDecisionEnum.PARTIAL,
        uuid4(),
        "partial scope",
    )
    context = DecisionContext(
        request_id=uuid4(),
        signals=(partial,),
        all_result_ids=(partial.source_id,),
        confidence=0.5,
        rationale="partial",
    )

    resolution = PrecedenceResolver().resolve(context)

    assert resolution.final_decision == VerificationDecisionEnum.PARTIAL
    assert resolution.partial_scope_description == "partial verification scope"


def test_escalation_engine_maps_actions() -> None:
    source_id = uuid4()
    context = DecisionContext(
        request_id=uuid4(),
        signals=(
            DecisionSignal(
                DecisionSignalCategory.ESCALATION,
                VerificationDecisionEnum.ESCALATE,
                source_id,
                "missing evidence",
            ),
        ),
        all_result_ids=(source_id,),
        confidence=0.0,
        rationale="missing evidence",
    )
    resolution = PrecedenceResolution(VerificationDecisionEnum.ESCALATE, (source_id,), "missing evidence")

    plan = EscalationEngine().determine(context, resolution)

    assert plan.action == EscalationAction.MANUAL_REVIEW


def test_escalation_engine_aborts_critical_failures() -> None:
    source_id = uuid4()
    context = DecisionContext(
        request_id=uuid4(),
        signals=(
            DecisionSignal(
                DecisionSignalCategory.CRITICAL_FAILURE,
                VerificationDecisionEnum.FAILED,
                source_id,
                "critical",
            ),
        ),
        all_result_ids=(source_id,),
        confidence=1.0,
        rationale="critical",
    )
    resolution = PrecedenceResolution(VerificationDecisionEnum.FAILED, (source_id,), "critical")

    assert EscalationEngine().determine(context, resolution).action == EscalationAction.ABORT
