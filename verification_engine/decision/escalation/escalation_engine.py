from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from verification_engine.contracts import VerificationDecisionEnum

from .._base import DecisionContext, DecisionSignalCategory, PrecedenceResolution
from ..exceptions import InvalidDecisionInput


class EscalationAction(str, Enum):
    NONE = "NONE"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    RETRY = "RETRY"
    ABORT = "ABORT"
    ESCALATE = "ESCALATE"


@dataclass(frozen=True)
class EscalationPlan:
    action: EscalationAction
    rationale: str


class EscalationEngine:
    def determine(self, context: DecisionContext, resolution: PrecedenceResolution) -> EscalationPlan:
        if not isinstance(context, DecisionContext) or not isinstance(resolution, PrecedenceResolution):
            raise InvalidDecisionInput("escalation requires decision context and precedence resolution")
        categories = {signal.category for signal in context.signals}
        if DecisionSignalCategory.CRITICAL_FAILURE in categories or DecisionSignalCategory.SECURITY_FAILURE in categories:
            return EscalationPlan(EscalationAction.ABORT, "critical or security failure requires abort")
        if resolution.final_decision == VerificationDecisionEnum.ESCALATE:
            return EscalationPlan(EscalationAction.MANUAL_REVIEW, "escalated decision requires manual review")
        if resolution.final_decision == VerificationDecisionEnum.PARTIAL:
            return EscalationPlan(EscalationAction.RETRY, "partial decision may be retried")
        if resolution.final_decision == VerificationDecisionEnum.FAILED:
            return EscalationPlan(EscalationAction.ESCALATE, "failed decision requires escalation handling")
        return EscalationPlan(EscalationAction.NONE, "verified decision requires no escalation")
