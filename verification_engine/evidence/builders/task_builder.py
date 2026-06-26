from typing import Any

from verification_engine.contracts import EvidenceType, TaskEvidence

from ._base import EvidencePackageBuilder, normalize_windows_path


class TaskEvidenceBuilder(EvidencePackageBuilder):
    evidence_type = EvidenceType.TASK
    payload_model = TaskEvidence

    def _normalize(self, raw_evidence: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(raw_evidence)
        if "executable_path" in normalized:
            normalized["executable_path"] = normalize_windows_path(normalized["executable_path"])
        if "working_directory" in normalized:
            normalized["working_directory"] = normalize_windows_path(normalized["working_directory"])
        if "arguments" in normalized:
            normalized["arguments"] = list(normalized["arguments"])
        if "triggers" in normalized:
            normalized["triggers"] = [dict(trigger) for trigger in normalized["triggers"]]
        return normalized
