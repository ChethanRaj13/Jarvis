from WindowsAIAssistant.backend.verification_engine.contracts import AuthorizationRecord, EvidencePackage, EvidenceType, VerifierID
from WindowsAIAssistant.backend.verification_engine.verification._base import (
    BaseVerifier,
    compare_field,
    comparison_from_outcome,
    expected,
    merge_outcomes,
    normalize_path,
)

from .execution_checker import ExecutionChecker
from .hash_verifier import HashVerifier
from .type_inspector import TypeInspector


class DownloadVerifier(BaseVerifier):
    evidence_type = EvidenceType.DOWNLOAD
    verifier_id = VerifierID.DOWNLOAD

    def __init__(
        self,
        hash_verifier: HashVerifier | None = None,
        type_inspector: TypeInspector | None = None,
        execution_checker: ExecutionChecker | None = None,
    ) -> None:
        self._hash_verifier = hash_verifier or HashVerifier()
        self._type_inspector = type_inspector or TypeInspector()
        self._execution_checker = execution_checker or ExecutionChecker()

    def _compare(self, authorization: AuthorizationRecord, evidence: EvidencePackage):
        payload = evidence.evidence_payload
        outcome = merge_outcomes(
            compare_field(payload, "file_path", authorization.target_resource, normalizer=normalize_path, required=True),
            compare_field(payload, "file_size_bytes", expected(authorization, "file_size_bytes")),
            compare_field(payload, "file_exists", expected(authorization, "file_exists")),
            self._hash_verifier.verify(authorization, payload),
            self._type_inspector.inspect(authorization, payload),
            self._execution_checker.check(payload),
            self._additional_paths(payload),
        )
        return comparison_from_outcome(outcome)

    def _additional_paths(self, payload: dict):
        extra_paths = tuple(path for path in payload.get("additional_write_paths", ()) if normalize_path(path) != normalize_path(payload.get("file_path", "")))
        if extra_paths:
            from WindowsAIAssistant.backend.verification_engine.verification._base import ComparisonOutcome

            return ComparisonOutcome(partial=("additional_write_paths",), rationale=("file was written to additional paths",))
        from WindowsAIAssistant.backend.verification_engine.verification._base import ComparisonOutcome

        return ComparisonOutcome(rationale=("no additional write paths detected",))
