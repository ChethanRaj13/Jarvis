from __future__ import annotations

from typing import Any

from verification_engine.contracts import SideEffectSeverity, SideEffectSurface, VerificationResult

from .._base import BaseAnalyzer, DetectedSideEffect, SideEffectDetectionResult


class SideEffectDetector(BaseAnalyzer):
    def detect(self, verification_result: VerificationResult) -> SideEffectDetectionResult:
        self._validate_result(verification_result)
        effects = tuple(self._from_result_payload(verification_result)) + tuple(
            self._from_failed_attributes(verification_result)
        )
        rationale = tuple(effect.rationale for effect in effects) or ("no side effects reported by verification result",)
        return SideEffectDetectionResult(
            request_id=str(verification_result.request_id),
            effects=effects,
            rationale=rationale,
        )

    def _from_result_payload(self, verification_result: VerificationResult) -> tuple[DetectedSideEffect, ...]:
        items = verification_result.detected_side_effects or []
        effects: list[DetectedSideEffect] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            affected_resource = str(
                item.get("affected_resource")
                or item.get("path_or_key")
                or item.get("resource")
                or item.get("path")
                or item.get("key")
                or "unknown"
            )
            change_type = str(item.get("change_type") or item.get("type") or "UNKNOWN")
            effects.append(
                DetectedSideEffect(
                    surface=self._surface_from(item.get("surface"), affected_resource, change_type),
                    affected_resource=affected_resource,
                    change_type=change_type,
                    severity=self._severity_from(item.get("severity"), change_type, affected_resource),
                    rationale=str(item.get("rationale") or f"{change_type} affected {affected_resource}"),
                    source_result_id=str(verification_result.result_id),
                )
            )
        return tuple(effects)

    def _from_failed_attributes(self, verification_result: VerificationResult) -> tuple[DetectedSideEffect, ...]:
        effects: list[DetectedSideEffect] = []
        for attribute in verification_result.failed_attributes:
            surface = self._surface_from(None, attribute, attribute)
            if surface is None:
                continue
            effects.append(
                DetectedSideEffect(
                    surface=surface,
                    affected_resource=verification_result.controlling_attribute or attribute,
                    change_type=attribute,
                    severity=self._severity_from(None, attribute, attribute),
                    rationale=f"verification result reported unexpected {attribute}",
                    source_result_id=str(verification_result.result_id),
                )
            )
        return tuple(effects)

    def _surface_from(self, value: Any, affected_resource: str, change_type: str) -> SideEffectSurface | None:
        if value:
            try:
                return SideEffectSurface(str(value).upper())
            except ValueError:
                pass
        text = f"{affected_resource} {change_type}".casefold()
        if any(token in text for token in ("file", "directory", "path", "download", "write")):
            return SideEffectSurface.FILESYSTEM
        if any(token in text for token in ("registry", "hive", "key")):
            return SideEffectSurface.REGISTRY
        if any(token in text for token in ("process", "child", "spawn", "executed")):
            return SideEffectSurface.PROCESS
        if any(token in text for token in ("task", "startup", "run key", "persistence")):
            return SideEffectSurface.PERSISTENCE
        if "network" in text or "connection" in text:
            return SideEffectSurface.NETWORK
        return None

    def _severity_from(self, value: Any, change_type: str, affected_resource: str) -> SideEffectSeverity:
        if value:
            try:
                return SideEffectSeverity(str(value).upper())
            except ValueError:
                pass
        text = f"{change_type} {affected_resource}".casefold()
        if any(token in text for token in ("protected", "safety", "persistence", "startup", "executed")):
            return SideEffectSeverity.CRITICAL
        if any(token in text for token in ("registry", "child", "network")):
            return SideEffectSeverity.HIGH
        if any(token in text for token in ("process", "task", "configuration")):
            return SideEffectSeverity.MEDIUM
        return SideEffectSeverity.LOW
