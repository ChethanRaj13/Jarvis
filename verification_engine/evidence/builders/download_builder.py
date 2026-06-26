from typing import Any

from verification_engine.contracts import DownloadEvidence, EvidenceType

from ._base import EvidencePackageBuilder, normalize_windows_path


class DownloadEvidenceBuilder(EvidencePackageBuilder):
    evidence_type = EvidenceType.DOWNLOAD
    payload_model = DownloadEvidence

    def _normalize(self, raw_evidence: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(raw_evidence)
        if "file_path" in normalized:
            normalized["file_path"] = normalize_windows_path(normalized["file_path"])
        if "additional_write_paths" in normalized:
            normalized["additional_write_paths"] = [
                normalize_windows_path(path) for path in normalized["additional_write_paths"]
            ]
        return normalized
