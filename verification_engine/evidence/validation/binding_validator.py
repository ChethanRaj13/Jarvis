from verification_engine.contracts import EvidencePackage

from ._base import BaseValidator, ValidationContext, ValidationResult
from .exceptions import BindingValidationError


class BindingValidator(BaseValidator):
    name = "binding"
    exception_type = BindingValidationError

    def _execute(self, evidence: EvidencePackage, context: ValidationContext) -> ValidationResult:
        if evidence.request_id != context.request_id:
            return ValidationResult(
                validator_name=self.name,
                passed=False,
                reason="evidence request_id does not match validation context",
            )
        if evidence.evidence_id is None:
            return ValidationResult(
                validator_name=self.name,
                passed=False,
                reason="evidence_id is required",
            )
        if not evidence.binding_token:
            return ValidationResult(
                validator_name=self.name,
                passed=False,
                reason="binding_token is required",
            )
        return ValidationResult(validator_name=self.name, passed=True)
