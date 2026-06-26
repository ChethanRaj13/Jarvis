from typing import Any

from verification_engine.contracts import EvidenceType, FilesystemEvidence

from ._base import EvidencePackageBuilder, normalize_windows_path


class FilesystemEvidenceBuilder(EvidencePackageBuilder):
    evidence_type = EvidenceType.FILESYSTEM
    payload_model = FilesystemEvidence

    def _normalize(self, raw_evidence: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(raw_evidence)
        if "file_path" in normalized:
            normalized["file_path"] = normalize_windows_path(normalized["file_path"])
        return normalized
