from __future__ import annotations

from typing import Iterable

from WindowsAIAssistant.backend.verification_engine.contracts import SideEffectSeverity, VerificationResult

from .._base import BaseAnalyzer, DriftAccumulationResult, DriftObservation


class DriftAccumulator(BaseAnalyzer):
    def accumulate(self, verification_results: Iterable[VerificationResult]) -> DriftAccumulationResult:
        results = self._validate_results(verification_results)
        observations: list[DriftObservation] = []
        for result in results:
            observations.extend(self._from_failed_attributes(result))
            observations.extend(self._from_payload_findings(result))
        rationale = tuple(
            f"{observation.attribute} drift observed on {observation.affected_asset}" for observation in observations
        ) or ("no drift observed in verification results",)
        return DriftAccumulationResult(observations=tuple(observations), rationale=rationale)

    def _from_failed_attributes(self, result: VerificationResult) -> tuple[DriftObservation, ...]:
        return tuple(
            DriftObservation(
                request_id=str(result.request_id),
                source_result_id=str(result.result_id),
                attribute=attribute,
                expected="authorized value",
                observed="verification mismatch",
                affected_asset=result.controlling_attribute or str(result.evidence_reference),
                authorized=False,
                expected_drift=False,
                severity=self._severity_for(attribute),
            )
            for attribute in result.failed_attributes
        )

    def _from_payload_findings(self, result: VerificationResult) -> tuple[DriftObservation, ...]:
        findings = result.drift_findings or []
        observations: list[DriftObservation] = []
        for finding in findings:
            if not isinstance(finding, dict):
                continue
            attribute = str(finding.get("attribute") or finding.get("expected_attribute") or "drift")
            observations.append(
                DriftObservation(
                    request_id=str(result.request_id),
                    source_result_id=str(result.result_id),
                    attribute=attribute,
                    expected=str(finding.get("expected") or finding.get("expected_attribute") or "authorized value"),
                    observed=str(finding.get("observed") or finding.get("observed_attribute") or "observed value"),
                    affected_asset=str(finding.get("affected_asset") or result.controlling_attribute or result.evidence_reference),
                    authorized=bool(finding.get("authorized", False)),
                    expected_drift=bool(finding.get("expected_drift", False)),
                    severity=self._severity_for(str(finding.get("severity") or attribute)),
                )
            )
        return tuple(observations)

    def _severity_for(self, attribute: str) -> SideEffectSeverity:
        text = attribute.casefold()
        if any(token in text for token in ("safety", "protected", "persistence", "startup")):
            return SideEffectSeverity.CRITICAL
        if any(token in text for token in ("registry", "privilege", "process")):
            return SideEffectSeverity.HIGH
        if any(token in text for token in ("configuration", "task")):
            return SideEffectSeverity.MEDIUM
        return SideEffectSeverity.LOW
