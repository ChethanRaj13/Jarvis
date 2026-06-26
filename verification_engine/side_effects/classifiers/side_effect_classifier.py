from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from verification_engine.contracts import SideEffectSeverity

from .._base import DetectedSideEffect
from ..exceptions import InvalidAnalysisInput


class SideEffectClassification(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class SideEffectClassificationResult:
    classification: SideEffectClassification
    rationale: str


class SideEffectClassifier:
    _severity_order = {
        SideEffectSeverity.LOW: 1,
        SideEffectSeverity.MEDIUM: 2,
        SideEffectSeverity.HIGH: 3,
        SideEffectSeverity.CRITICAL: 4,
    }

    def classify(self, effects: tuple[DetectedSideEffect, ...]) -> SideEffectClassificationResult:
        if not isinstance(effects, tuple):
            raise InvalidAnalysisInput("side-effect classification requires an immutable tuple of effects")
        if not effects:
            return SideEffectClassificationResult(SideEffectClassification.NONE, "no unauthorized side effects detected")
        highest = max((effect.severity for effect in effects), key=lambda severity: self._severity_order[severity])
        return SideEffectClassificationResult(
            SideEffectClassification(highest.value),
            f"highest observed side-effect severity is {highest.value}",
        )
