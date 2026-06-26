from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from uuid import UUID, uuid4

from WindowsAIAssistant.backend.verification_engine.contracts import VerificationDecision, VerificationDecisionEnum


class DecisionSignalCategory(str, Enum):
    CRITICAL_FAILURE = "CRITICAL_FAILURE"
    SECURITY_FAILURE = "SECURITY_FAILURE"
    VERIFICATION_FAILURE = "VERIFICATION_FAILURE"
    SIDE_EFFECT_FAILURE = "SIDE_EFFECT_FAILURE"
    DRIFT_FAILURE = "DRIFT_FAILURE"
    ESCALATION = "ESCALATION"
    PARTIAL = "PARTIAL"
    SUCCESS = "SUCCESS"


@dataclass(frozen=True)
class DecisionSignal:
    category: DecisionSignalCategory
    decision: VerificationDecisionEnum
    source_id: UUID
    rationale: str


@dataclass(frozen=True)
class DecisionContext:
    request_id: UUID
    signals: tuple[DecisionSignal, ...]
    all_result_ids: tuple[UUID, ...]
    confidence: float
    rationale: str


@dataclass(frozen=True)
class PrecedenceResolution:
    final_decision: VerificationDecisionEnum
    controlling_results: tuple[UUID, ...]
    rationale: str
    partial_scope_description: str | None = None


class BaseDecisionEngine:
    decision_engine_version = "decision-engine-v1"

    def _build_decision(self, context: DecisionContext, resolution: PrecedenceResolution) -> VerificationDecision:
        escalation_expiry = None
        if resolution.final_decision == VerificationDecisionEnum.ESCALATE:
            escalation_expiry = datetime.now(timezone.utc) + timedelta(minutes=30)
        return VerificationDecision(
            decision_id=uuid4(),
            request_id=context.request_id,
            final_decision=resolution.final_decision,
            controlling_results=list(resolution.controlling_results),
            full_rationale=resolution.rationale,
            all_results=list(context.all_result_ids),
            decision_timestamp=datetime.now(timezone.utc),
            decision_engine_version=self.decision_engine_version,
            escalation_expiry=escalation_expiry,
            partial_scope_description=resolution.partial_scope_description,
        )

    def _fail_closed_decision(self, request_id: UUID, source_id: UUID, reason: str) -> VerificationDecision:
        now = datetime.now(timezone.utc)
        return VerificationDecision(
            decision_id=uuid4(),
            request_id=request_id,
            final_decision=VerificationDecisionEnum.ESCALATE,
            controlling_results=[source_id],
            full_rationale=reason,
            all_results=[source_id],
            decision_timestamp=now,
            decision_engine_version=self.decision_engine_version,
            escalation_expiry=now + timedelta(minutes=30),
        )
