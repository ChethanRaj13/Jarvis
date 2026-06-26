from verification_engine.contracts import AuthorizationRecord, EvidencePackage, EvidenceType, VerifierID
from verification_engine.verification._base import (
    BaseVerifier,
    compare_field,
    comparison_from_outcome,
    expected,
    merge_outcomes,
    normalize_path,
    normalize_registry,
)

from .baseline_comparator import BaselineComparator
from .safety_config_guard import SafetyConfigGuard


class ConfigurationVerifier(BaseVerifier):
    evidence_type = EvidenceType.CONFIGURATION
    verifier_id = VerifierID.CONFIGURATION

    def __init__(
        self,
        baseline_comparator: BaselineComparator | None = None,
        safety_config_guard: SafetyConfigGuard | None = None,
    ) -> None:
        self._baseline_comparator = baseline_comparator or BaselineComparator()
        self._safety_config_guard = safety_config_guard or SafetyConfigGuard()

    def _compare(self, authorization: AuthorizationRecord, evidence: EvidencePackage):
        payload = evidence.evidence_payload
        path_normalizer = normalize_registry if payload.get("config_source_type") == "REGISTRY" else normalize_path
        outcome = merge_outcomes(
            compare_field(payload, "config_path", authorization.target_resource, normalizer=path_normalizer, required=True),
            compare_field(payload, "config_format", expected(authorization, "config_format")),
            self._baseline_comparator.compare(authorization, payload),
            self._safety_config_guard.check(payload),
        )
        return comparison_from_outcome(outcome)
