from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import PureWindowsPath
from typing import Any
from uuid import uuid4

from verification_engine.contracts import (
    AuthorizationRecord,
    EvidencePackage,
    EvidenceType,
    VerificationDecisionEnum,
    VerificationResult,
    VerifierID,
)

from .exceptions import InvalidAuthorizationError, InvalidEvidenceError, VerificationError


@dataclass(frozen=True)
class VerificationComparison:
    decision: VerificationDecisionEnum
    confirmed_attributes: tuple[str, ...] = ()
    failed_attributes: tuple[str, ...] = ()
    rationale_parts: tuple[str, ...] = ()


@dataclass(frozen=True)
class ComparisonOutcome:
    confirmed: tuple[str, ...] = ()
    failed: tuple[str, ...] = ()
    partial: tuple[str, ...] = ()
    escalations: tuple[str, ...] = ()
    rationale: tuple[str, ...] = ()

    @property
    def decision(self) -> VerificationDecisionEnum:
        if self.escalations:
            return VerificationDecisionEnum.ESCALATE
        if self.failed:
            return VerificationDecisionEnum.FAILED
        if self.partial:
            return VerificationDecisionEnum.PARTIAL
        return VerificationDecisionEnum.VERIFIED


class BaseVerifier:
    evidence_type: EvidenceType
    verifier_id: VerifierID

    def verify(self, authorization: AuthorizationRecord, evidence: EvidencePackage) -> VerificationResult:
        try:
            self._validate_inputs(authorization, evidence)
            comparison = self._compare(authorization, evidence)
        except VerificationError as exc:
            comparison = VerificationComparison(
                decision=VerificationDecisionEnum.ESCALATE,
                rationale_parts=(str(exc),),
            )

        return VerificationResult(
            result_id=uuid4(),
            request_id=authorization.request_id,
            verifier_id=self.verifier_id,
            sub_decision=comparison.decision,
            confirmed_attributes=list(comparison.confirmed_attributes),
            failed_attributes=list(comparison.failed_attributes),
            evidence_reference=evidence.evidence_id,
            sub_decision_rationale="; ".join(comparison.rationale_parts) or comparison.decision.value,
            result_timestamp=datetime.now(timezone.utc),
        )

    def _validate_inputs(self, authorization: AuthorizationRecord, evidence: EvidencePackage) -> None:
        if authorization.request_id != evidence.request_id:
            raise InvalidEvidenceError("authorization and evidence request_id values do not match")
        if evidence.evidence_type != self.evidence_type:
            raise InvalidEvidenceError(f"expected {self.evidence_type.value} evidence")
        if not authorization.authorized_scope:
            raise InvalidAuthorizationError("authorized_scope is required")
        if not evidence.evidence_payload:
            raise InvalidEvidenceError("evidence_payload is required")

    def _compare(self, authorization: AuthorizationRecord, evidence: EvidencePackage) -> VerificationComparison:
        raise NotImplementedError


def expected(authorization: AuthorizationRecord, key: str, default: Any = None) -> Any:
    return authorization.authorized_scope.get(key, default)


def normalize_path(value: Any) -> str:
    return str(PureWindowsPath(str(value))).casefold()


def normalize_registry(value: Any) -> str:
    return "\\".join(part for part in str(value).replace("/", "\\").split("\\") if part).casefold()


def compare_field(
    payload: dict[str, Any],
    field_name: str,
    expected_value: Any,
    *,
    normalizer=None,
    required: bool = False,
) -> ComparisonOutcome:
    if expected_value is None:
        if required:
            return ComparisonOutcome(escalations=(field_name,), rationale=(f"missing expected {field_name}",))
        return ComparisonOutcome()
    observed_value = payload.get(field_name)
    if observed_value is None:
        return ComparisonOutcome(escalations=(field_name,), rationale=(f"missing evidence {field_name}",))
    left = normalizer(observed_value) if normalizer else observed_value
    right = normalizer(expected_value) if normalizer else expected_value
    if left == right:
        return ComparisonOutcome(confirmed=(field_name,), rationale=(f"{field_name} matched",))
    return ComparisonOutcome(failed=(field_name,), rationale=(f"{field_name} mismatch",))


def merge_outcomes(*outcomes: ComparisonOutcome) -> ComparisonOutcome:
    return ComparisonOutcome(
        confirmed=tuple(item for outcome in outcomes for item in outcome.confirmed),
        failed=tuple(item for outcome in outcomes for item in outcome.failed),
        partial=tuple(item for outcome in outcomes for item in outcome.partial),
        escalations=tuple(item for outcome in outcomes for item in outcome.escalations),
        rationale=tuple(item for outcome in outcomes for item in outcome.rationale),
    )


def comparison_from_outcome(outcome: ComparisonOutcome) -> VerificationComparison:
    decision = outcome.decision
    failed = outcome.failed + outcome.partial
    if decision == VerificationDecisionEnum.ESCALATE:
        failed = ()
    return VerificationComparison(
        decision=decision,
        confirmed_attributes=outcome.confirmed,
        failed_attributes=failed,
        rationale_parts=outcome.rationale or (decision.value,),
    )
