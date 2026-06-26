from WindowsAIAssistant.backend.verification_engine.contracts import AuthorizationRecord, EvidencePackage, EvidenceType, VerifierID
from WindowsAIAssistant.backend.verification_engine.verification._base import (
    BaseVerifier,
    compare_field,
    comparison_from_outcome,
    expected,
    merge_outcomes,
    normalize_path,
)

from .persistence_detector import PersistenceDetector
from .trigger_comparator import TriggerComparator


class TaskVerifier(BaseVerifier):
    evidence_type = EvidenceType.TASK
    verifier_id = VerifierID.TASK

    def __init__(
        self,
        trigger_comparator: TriggerComparator | None = None,
        persistence_detector: PersistenceDetector | None = None,
    ) -> None:
        self._trigger_comparator = trigger_comparator or TriggerComparator()
        self._persistence_detector = persistence_detector or PersistenceDetector()

    def _compare(self, authorization: AuthorizationRecord, evidence: EvidencePackage):
        payload = evidence.evidence_payload
        outcome = merge_outcomes(
            compare_field(payload, "task_name", authorization.target_resource, required=True),
            compare_field(payload, "task_exists", expected(authorization, "task_exists")),
            compare_field(payload, "executable_path", expected(authorization, "executable_path"), normalizer=normalize_path),
            compare_field(payload, "run_as_user", expected(authorization, "run_as_user")),
            compare_field(payload, "highest_run_level", expected(authorization, "highest_run_level")),
            compare_field(payload, "arguments", expected(authorization, "arguments")),
            compare_field(payload, "working_directory", expected(authorization, "working_directory"), normalizer=normalize_path),
            compare_field(payload, "task_state", expected(authorization, "task_state")),
            self._trigger_comparator.compare(authorization, payload),
            self._persistence_detector.detect(payload),
        )
        return comparison_from_outcome(outcome)
