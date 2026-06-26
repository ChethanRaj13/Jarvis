from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from verification_engine.contracts import SideEffectSeverity, VerificationResult

from .exceptions import InvalidAnalysisInput


@dataclass(frozen=True)
class DriftObservation:
    request_id: str
    source_result_id: str
    attribute: str
    expected: str
    observed: str
    affected_asset: str
    authorized: bool
    expected_drift: bool
    severity: SideEffectSeverity


@dataclass(frozen=True)
class DriftAccumulationResult:
    observations: tuple[DriftObservation, ...]
    rationale: tuple[str, ...]
    fail_closed: bool = False


class BaseAnalyzer:
    def _validate_result(self, verification_result: VerificationResult) -> None:
        if not isinstance(verification_result, VerificationResult):
            raise InvalidAnalysisInput("drift analysis requires VerificationResult input")

    def _validate_results(self, verification_results: Iterable[VerificationResult]) -> tuple[VerificationResult, ...]:
        if isinstance(verification_results, VerificationResult):
            results = (verification_results,)
        else:
            try:
                results = tuple(verification_results)
            except TypeError as exc:
                raise InvalidAnalysisInput("drift analysis requires VerificationResult input") from exc
        for result in results:
            self._validate_result(result)
        return results
