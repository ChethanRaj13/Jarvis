from verification_engine.contracts import EvidencePackage

from ._base import BaseValidator, EvidenceValidationResult, ValidationContext, ValidationResult
from .binding_validator import BindingValidator
from .completeness_validator import CompletenessValidator
from .exceptions import ValidationError
from .window_validator import WindowValidator


class ValidationService:
    def __init__(self, validators: tuple[BaseValidator, ...] | None = None) -> None:
        self._validators = validators or (
            WindowValidator(),
            BindingValidator(),
            CompletenessValidator(),
        )

    def validate(
        self,
        evidence: EvidencePackage,
        context: ValidationContext,
    ) -> EvidenceValidationResult:
        results: list[ValidationResult] = []
        for validator in self._validators:
            try:
                results.append(validator.validate(evidence, context))
            except ValidationError as exc:
                results.append(
                    ValidationResult(
                        validator_name=validator.name,
                        passed=False,
                        mandatory=True,
                        reason=str(exc),
                    )
                )

        fail_closed = any(result.mandatory and not result.passed for result in results)
        return EvidenceValidationResult(
            passed=not fail_closed,
            fail_closed=fail_closed,
            results=tuple(results),
        )
