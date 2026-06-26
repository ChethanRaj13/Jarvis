from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from WindowsAIAssistant.backend.verification_engine.contracts import (
    SideEffectChange,
    SideEffectReport,
    UnauthorizedSideEffectChange,
    VerificationDecisionEnum,
)

from .._base import DetectedSideEffect
from ..classifiers.side_effect_classifier import SideEffectClassification
from ..exceptions import InvalidAnalysisInput


class SideEffectReportBuilder:
    def build(
        self,
        *,
        request_id: UUID,
        effects: tuple[DetectedSideEffect, ...],
        classification: SideEffectClassification,
        detection_scope: str,
        authorized_changes: tuple[SideEffectChange, ...] = (),
        tool_registry_informed_scope: bool | None = None,
        scope_expansion_reason: str | None = None,
    ) -> SideEffectReport:
        if not isinstance(effects, tuple):
            raise InvalidAnalysisInput("side-effect report builder requires an immutable tuple of effects")
        if not detection_scope:
            raise InvalidAnalysisInput("detection_scope is required")
        unauthorized_changes = [
            UnauthorizedSideEffectChange(
                path_or_key=effect.affected_resource,
                change_type=effect.change_type,
                surface=effect.surface,
                severity=effect.severity,
            )
            for effect in effects
        ]
        return SideEffectReport(
            report_id=uuid4(),
            request_id=request_id,
            detection_scope=detection_scope,
            authorized_changes=list(authorized_changes),
            unauthorized_changes=unauthorized_changes,
            side_effect_sub_decision=self._classification_to_sub_decision(classification),
            detection_timestamp=datetime.now(timezone.utc),
            tool_registry_informed_scope=tool_registry_informed_scope,
            scope_expansion_reason=scope_expansion_reason,
        )

    def _classification_to_sub_decision(self, classification: SideEffectClassification) -> VerificationDecisionEnum:
        if classification == SideEffectClassification.NONE:
            return VerificationDecisionEnum.VERIFIED
        if classification in (SideEffectClassification.LOW, SideEffectClassification.MEDIUM):
            return VerificationDecisionEnum.PARTIAL
        return VerificationDecisionEnum.FAILED
