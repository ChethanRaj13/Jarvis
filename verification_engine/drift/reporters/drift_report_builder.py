from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from verification_engine.contracts import (
    DriftAttributionFinding,
    DriftFinding,
    DriftReport,
    SideEffectSeverity,
    VerificationDecisionEnum,
)

from .._base import DriftObservation
from ..attribution.drift_attributor import DriftAttributionResult
from ..exceptions import InvalidAnalysisInput


class DriftReportBuilder:
    def build(
        self,
        *,
        session_id: str,
        request_id: UUID,
        attribution: DriftAttributionResult,
        session_boundary_verified: bool | None = None,
    ) -> DriftReport:
        if not session_id:
            raise InvalidAnalysisInput("session_id is required")
        if not isinstance(attribution, DriftAttributionResult):
            raise InvalidAnalysisInput("drift report builder requires attribution results")
        observations = attribution.expected + attribution.unexpected
        drift_findings = [
            DriftFinding(
                expected_attribute=observation.expected,
                observed_attribute=observation.observed,
                delta_description=f"{observation.attribute}: {observation.expected} -> {observation.observed}",
            )
            for observation in observations
        ]
        attribution_findings = [
            DriftAttributionFinding(
                change_description=f"{observation.attribute} drift on {observation.affected_asset}",
                attributed_to_request_id=UUID(observation.request_id) if observation.authorized else None,
                affected_asset=observation.affected_asset,
                severity=observation.severity,
            )
            for observation in observations
        ]
        return DriftReport(
            report_id=uuid4(),
            session_id=session_id,
            request_id=request_id,
            attribution_findings=attribution_findings,
            drift_findings=drift_findings,
            drift_sub_decision=self._sub_decision(attribution.unauthorized),
            detection_timestamp=datetime.now(timezone.utc),
            session_boundary_verified=session_boundary_verified,
            cumulative_unattributed_count=len(attribution.unauthorized),
        )

    def _sub_decision(self, unauthorized: tuple[DriftObservation, ...]) -> VerificationDecisionEnum:
        if not unauthorized:
            return VerificationDecisionEnum.VERIFIED
        if any(observation.severity in (SideEffectSeverity.CRITICAL, SideEffectSeverity.HIGH) for observation in unauthorized):
            return VerificationDecisionEnum.FAILED
        return VerificationDecisionEnum.PARTIAL
