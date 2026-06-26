from __future__ import annotations

from WindowsAIAssistant.backend.verification_engine.contracts import VerificationDecisionEnum

from .._base import DecisionContext, DecisionSignal, DecisionSignalCategory, PrecedenceResolution
from ..exceptions import InvalidDecisionInput


class PrecedenceResolver:
    _priority = {
        DecisionSignalCategory.CRITICAL_FAILURE: 100,
        DecisionSignalCategory.SECURITY_FAILURE: 90,
        DecisionSignalCategory.VERIFICATION_FAILURE: 80,
        DecisionSignalCategory.SIDE_EFFECT_FAILURE: 70,
        DecisionSignalCategory.DRIFT_FAILURE: 60,
        DecisionSignalCategory.ESCALATION: 50,
        DecisionSignalCategory.PARTIAL: 40,
        DecisionSignalCategory.SUCCESS: 0,
    }

    def resolve(self, context: DecisionContext) -> PrecedenceResolution:
        if not isinstance(context, DecisionContext):
            raise InvalidDecisionInput("precedence resolution requires DecisionContext")
        if not context.signals:
            raise InvalidDecisionInput("DecisionContext must include at least one signal")
        controlling = max(context.signals, key=lambda signal: self._priority[signal.category])
        same_priority = tuple(
            signal for signal in context.signals if self._priority[signal.category] == self._priority[controlling.category]
        )
        decision = self._decision_for(controlling)
        return PrecedenceResolution(
            final_decision=decision,
            controlling_results=tuple(signal.source_id for signal in same_priority),
            rationale="; ".join(signal.rationale for signal in same_priority),
            partial_scope_description="partial verification scope" if decision == VerificationDecisionEnum.PARTIAL else None,
        )

    def _decision_for(self, signal: DecisionSignal) -> VerificationDecisionEnum:
        if signal.category in (
            DecisionSignalCategory.CRITICAL_FAILURE,
            DecisionSignalCategory.SECURITY_FAILURE,
            DecisionSignalCategory.VERIFICATION_FAILURE,
            DecisionSignalCategory.SIDE_EFFECT_FAILURE,
            DecisionSignalCategory.DRIFT_FAILURE,
        ):
            return VerificationDecisionEnum.FAILED
        if signal.category == DecisionSignalCategory.ESCALATION:
            return VerificationDecisionEnum.ESCALATE
        if signal.category == DecisionSignalCategory.PARTIAL:
            return VerificationDecisionEnum.PARTIAL
        return VerificationDecisionEnum.VERIFIED
