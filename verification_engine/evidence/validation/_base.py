from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from verification_engine.contracts import EvidencePackage

from .exceptions import ValidationError


@dataclass(frozen=True)
class ValidationContext:
    request_id: UUID
    execution_timestamp: datetime
    evidence_window_seconds: int
    required_fields: dict[str, tuple[str, ...]] = field(default_factory=dict)


@dataclass(frozen=True)
class ValidationResult:
    validator_name: str
    passed: bool
    mandatory: bool = True
    reason: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceValidationResult:
    passed: bool
    fail_closed: bool
    results: tuple[ValidationResult, ...]


class BaseValidator:
    name = "base"
    exception_type = ValidationError

    def validate(self, evidence: EvidencePackage, context: ValidationContext) -> ValidationResult:
        self._validate_input(evidence, context)
        return self._execute(evidence, context)

    def _validate_input(self, evidence: EvidencePackage, context: ValidationContext) -> None:
        if not isinstance(evidence, EvidencePackage):
            raise self.exception_type("evidence must be an EvidencePackage")
        if not isinstance(context, ValidationContext):
            raise self.exception_type("context must be a ValidationContext")

    def _execute(self, evidence: EvidencePackage, context: ValidationContext) -> ValidationResult:
        raise NotImplementedError
