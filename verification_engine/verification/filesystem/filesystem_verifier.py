from verification_engine.contracts import AuthorizationRecord, EvidencePackage, EvidenceType, VerifierID
from verification_engine.verification._base import BaseVerifier, comparison_from_outcome, merge_outcomes

from .attribute_comparator import FilesystemAttributeComparator
from .side_effect_scanner import FilesystemSideEffectScanner


class FilesystemVerifier(BaseVerifier):
    evidence_type = EvidenceType.FILESYSTEM
    verifier_id = VerifierID.FILESYSTEM

    def __init__(
        self,
        comparator: FilesystemAttributeComparator | None = None,
        side_effect_scanner: FilesystemSideEffectScanner | None = None,
    ) -> None:
        self._comparator = comparator or FilesystemAttributeComparator()
        self._side_effect_scanner = side_effect_scanner or FilesystemSideEffectScanner()

    def _compare(self, authorization: AuthorizationRecord, evidence: EvidencePackage):
        payload = evidence.evidence_payload
        outcome = merge_outcomes(
            self._comparator.compare(authorization, payload),
            self._side_effect_scanner.scan(payload),
        )
        return comparison_from_outcome(outcome)
