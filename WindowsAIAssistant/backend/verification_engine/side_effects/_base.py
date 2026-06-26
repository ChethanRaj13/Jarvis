from __future__ import annotations

from dataclasses import dataclass

from WindowsAIAssistant.backend.verification_engine.contracts import SideEffectSeverity, SideEffectSurface, VerificationResult

from .exceptions import InvalidAnalysisInput


@dataclass(frozen=True)
class DetectedSideEffect:
    surface: SideEffectSurface
    affected_resource: str
    change_type: str
    severity: SideEffectSeverity
    rationale: str
    source_result_id: str


@dataclass(frozen=True)
class SideEffectDetectionResult:
    request_id: str
    effects: tuple[DetectedSideEffect, ...]
    rationale: tuple[str, ...]
    fail_closed: bool = False


class BaseAnalyzer:
    def _validate_result(self, verification_result: VerificationResult) -> None:
        if not isinstance(verification_result, VerificationResult):
            raise InvalidAnalysisInput("side-effect analysis requires a VerificationResult")

    def _fail_closed(self, request_id: str, reason: str) -> SideEffectDetectionResult:
        return SideEffectDetectionResult(
            request_id=request_id,
            effects=(),
            rationale=(reason,),
            fail_closed=True,
        )
