from datetime import datetime, timedelta

from verification_engine.config.verification_config import EvidenceCollectionConfig
from verification_engine.contracts import EvidencePackage

from ._base import BaseValidator, ValidationContext, ValidationResult
from .exceptions import WindowValidationError


class WindowValidator(BaseValidator):
    name = "window"
    exception_type = WindowValidationError

    def __init__(
        self,
        evidence_window_seconds: int | None = None,
        config: EvidenceCollectionConfig | None = None,
    ) -> None:
        self._evidence_window_seconds = evidence_window_seconds
        self._config = config

    def _execute(self, evidence: EvidencePackage, context: ValidationContext) -> ValidationResult:
        if not isinstance(evidence.collection_timestamp, datetime):
            return ValidationResult(
                validator_name=self.name,
                passed=False,
                reason="collection_timestamp is not a datetime",
            )

        window_seconds = self._resolve_window_seconds(context)
        if window_seconds <= 0:
            raise WindowValidationError("evidence window must be greater than zero")

        window_open = context.execution_timestamp
        window_close = window_open + timedelta(seconds=window_seconds)
        in_window = window_open <= evidence.collection_timestamp <= window_close

        return ValidationResult(
            validator_name=self.name,
            passed=in_window and evidence.collection_window_open,
            reason=None if in_window and evidence.collection_window_open else "evidence outside permitted window",
            details={
                "window_open": window_open.isoformat(),
                "window_close": window_close.isoformat(),
                "collection_timestamp": evidence.collection_timestamp.isoformat(),
            },
        )

    def _resolve_window_seconds(self, context: ValidationContext) -> int:
        if self._config is not None:
            return self._config.evidence_window_seconds
        if self._evidence_window_seconds is not None:
            return self._evidence_window_seconds
        return context.evidence_window_seconds
