from typing import Any

from WindowsAIAssistant.backend.verification_engine.contracts import EvidenceType, ProcessEvidence

from ._base import EvidencePackageBuilder, normalize_windows_path


class ProcessEvidenceBuilder(EvidencePackageBuilder):
    evidence_type = EvidenceType.PROCESS
    payload_model = ProcessEvidence

    def _normalize(self, raw_evidence: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(raw_evidence)
        if "executable_path" in normalized:
            normalized["executable_path"] = normalize_windows_path(normalized["executable_path"])
        if "command_line_parameters" in normalized:
            normalized["command_line_parameters"] = list(normalized["command_line_parameters"])
        if "child_processes" in normalized:
            normalized["child_processes"] = [dict(child) for child in normalized["child_processes"]]
        return normalized
