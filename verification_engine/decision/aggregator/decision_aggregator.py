from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID, uuid4

from verification_engine.contracts import (
    DriftReport,
    SideEffectReport,
    SideEffectSeverity,
    VerificationDecisionEnum,
    VerificationResult,
)

from .._base import BaseDecisionEngine, DecisionContext, DecisionSignal, DecisionSignalCategory
from ..exceptions import InvalidDecisionInput


class DecisionAggregator(BaseDecisionEngine):
    def aggregate(
        self,
        *,
        request_id: UUID,
        verification_results: Iterable[VerificationResult],
        side_effect_report: SideEffectReport | None,
        drift_report: DriftReport | None,
    ) -> DecisionContext:
        results = tuple(verification_results)
        if not results:
            source_id = uuid4()
            return DecisionContext(
                request_id=request_id,
                signals=(
                    DecisionSignal(
                        DecisionSignalCategory.ESCALATION,
                        VerificationDecisionEnum.ESCALATE,
                        source_id,
                        "no verification results available",
                    ),
                ),
                all_result_ids=(source_id,),
                confidence=0.0,
                rationale="fail-closed: no verification results available",
            )
        self._validate_request_ids(request_id, results, side_effect_report, drift_report)
        signals = list(self._verification_signals(results))
        signals.extend(self._side_effect_signals(request_id, side_effect_report))
        signals.extend(self._drift_signals(request_id, drift_report))
        all_result_ids = tuple(signal.source_id for signal in signals)
        confidence = self._confidence(signals)
        return DecisionContext(
            request_id=request_id,
            signals=tuple(signals),
            all_result_ids=all_result_ids,
            confidence=confidence,
            rationale="; ".join(signal.rationale for signal in signals),
        )

    def _validate_request_ids(
        self,
        request_id: UUID,
        results: tuple[VerificationResult, ...],
        side_effect_report: SideEffectReport | None,
        drift_report: DriftReport | None,
    ) -> None:
        if any(result.request_id != request_id for result in results):
            raise InvalidDecisionInput("verification result request_id mismatch")
        if side_effect_report is not None and side_effect_report.request_id != request_id:
            raise InvalidDecisionInput("side-effect report request_id mismatch")
        if drift_report is not None and drift_report.request_id != request_id:
            raise InvalidDecisionInput("drift report request_id mismatch")

    def _verification_signals(self, results: tuple[VerificationResult, ...]) -> tuple[DecisionSignal, ...]:
        signals: list[DecisionSignal] = []
        for result in results:
            if result.sub_decision == VerificationDecisionEnum.FAILED:
                category = DecisionSignalCategory.VERIFICATION_FAILURE
            elif result.sub_decision == VerificationDecisionEnum.ESCALATE:
                category = DecisionSignalCategory.ESCALATION
            elif result.sub_decision == VerificationDecisionEnum.PARTIAL:
                category = DecisionSignalCategory.PARTIAL
            else:
                category = DecisionSignalCategory.SUCCESS
            signals.append(DecisionSignal(category, result.sub_decision, result.result_id, result.sub_decision_rationale))
        return tuple(signals)

    def _side_effect_signals(
        self,
        request_id: UUID,
        side_effect_report: SideEffectReport | None,
    ) -> tuple[DecisionSignal, ...]:
        if side_effect_report is None:
            return (
                DecisionSignal(
                    DecisionSignalCategory.ESCALATION,
                    VerificationDecisionEnum.ESCALATE,
                    uuid4(),
                    f"missing mandatory side-effect report for request {request_id}",
                ),
            )
        if side_effect_report.unauthorized_changes:
            if any(change.severity == SideEffectSeverity.CRITICAL for change in side_effect_report.unauthorized_changes):
                category = DecisionSignalCategory.CRITICAL_FAILURE
            elif any(change.severity in (SideEffectSeverity.HIGH, SideEffectSeverity.MEDIUM) for change in side_effect_report.unauthorized_changes):
                category = DecisionSignalCategory.SECURITY_FAILURE
            else:
                category = DecisionSignalCategory.SIDE_EFFECT_FAILURE
            return (
                DecisionSignal(
                    category,
                    side_effect_report.side_effect_sub_decision,
                    side_effect_report.report_id,
                    "unauthorized side effects detected",
                ),
            )
        return (
            DecisionSignal(
                DecisionSignalCategory.SUCCESS,
                side_effect_report.side_effect_sub_decision,
                side_effect_report.report_id,
                "side-effect report found no unauthorized changes",
            ),
        )

    def _drift_signals(self, request_id: UUID, drift_report: DriftReport | None) -> tuple[DecisionSignal, ...]:
        if drift_report is None:
            return (
                DecisionSignal(
                    DecisionSignalCategory.ESCALATION,
                    VerificationDecisionEnum.ESCALATE,
                    uuid4(),
                    f"missing mandatory drift report for request {request_id}",
                ),
            )
        if drift_report.drift_sub_decision == VerificationDecisionEnum.FAILED:
            category = DecisionSignalCategory.DRIFT_FAILURE
        elif drift_report.drift_sub_decision == VerificationDecisionEnum.ESCALATE:
            category = DecisionSignalCategory.ESCALATION
        elif drift_report.drift_sub_decision == VerificationDecisionEnum.PARTIAL:
            category = DecisionSignalCategory.PARTIAL
        else:
            category = DecisionSignalCategory.SUCCESS
        return (
            DecisionSignal(
                category,
                drift_report.drift_sub_decision,
                drift_report.report_id,
                "drift report evaluated",
            ),
        )

    def _confidence(self, signals: list[DecisionSignal]) -> float:
        if any(signal.category == DecisionSignalCategory.ESCALATION for signal in signals):
            return 0.0
        if any(signal.decision == VerificationDecisionEnum.FAILED for signal in signals):
            return 1.0
        if any(signal.decision == VerificationDecisionEnum.PARTIAL for signal in signals):
            return 0.5
        return 1.0
