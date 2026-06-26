from WindowsAIAssistant.backend.verification_engine.contracts import AuthorizationRecord, EvidencePackage, EvidenceType, VerifierID
from WindowsAIAssistant.backend.verification_engine.verification._base import (
    BaseVerifier,
    compare_field,
    comparison_from_outcome,
    expected,
    merge_outcomes,
    normalize_path,
)

from .child_process_scanner import ChildProcessScanner
from .privilege_checker import PrivilegeChecker


class ProcessVerifier(BaseVerifier):
    evidence_type = EvidenceType.PROCESS
    verifier_id = VerifierID.PROCESS

    def __init__(
        self,
        privilege_checker: PrivilegeChecker | None = None,
        child_process_scanner: ChildProcessScanner | None = None,
    ) -> None:
        self._privilege_checker = privilege_checker or PrivilegeChecker()
        self._child_process_scanner = child_process_scanner or ChildProcessScanner()

    def _compare(self, authorization: AuthorizationRecord, evidence: EvidencePackage):
        payload = evidence.evidence_payload
        outcome = merge_outcomes(
            compare_field(payload, "executable_path", authorization.target_resource, normalizer=normalize_path, required=True),
            compare_field(payload, "process_id", expected(authorization, "process_id")),
            compare_field(payload, "command_line_parameters", expected(authorization, "command_line_parameters")),
            compare_field(payload, "parent_process_id", expected(authorization, "parent_process_id")),
            compare_field(payload, "process_exists", expected(authorization, "process_exists")),
            self._privilege_checker.check(authorization, payload),
            self._child_process_scanner.scan(authorization, payload),
        )
        return comparison_from_outcome(outcome)
