from WindowsAIAssistant.backend.verification_engine.contracts import AuthorizationRecord, EvidencePackage, EvidenceType, VerifierID
from WindowsAIAssistant.backend.verification_engine.verification._base import (
    BaseVerifier,
    compare_field,
    comparison_from_outcome,
    expected,
    merge_outcomes,
    normalize_registry,
)

from .adjacent_key_scanner import AdjacentKeyScanner
from .hive_protector import RegistryHiveProtector


class RegistryVerifier(BaseVerifier):
    evidence_type = EvidenceType.REGISTRY
    verifier_id = VerifierID.REGISTRY

    def __init__(
        self,
        hive_protector: RegistryHiveProtector | None = None,
        adjacent_key_scanner: AdjacentKeyScanner | None = None,
    ) -> None:
        self._hive_protector = hive_protector or RegistryHiveProtector()
        self._adjacent_key_scanner = adjacent_key_scanner or AdjacentKeyScanner()

    def _compare(self, authorization: AuthorizationRecord, evidence: EvidencePackage):
        payload = evidence.evidence_payload
        outcome = merge_outcomes(
            compare_field(payload, "key_path", authorization.target_resource, normalizer=normalize_registry, required=True),
            compare_field(payload, "key_exists", expected(authorization, "key_exists")),
            compare_field(payload, "value_name", expected(authorization, "value_name")),
            compare_field(payload, "value_type", expected(authorization, "value_type")),
            compare_field(payload, "value_data", expected(authorization, "value_data")),
            self._hive_protector.check(authorization, payload),
            self._adjacent_key_scanner.scan(payload),
        )
        return comparison_from_outcome(outcome)
