from typing import Any

from verification_engine.contracts import EvidenceType, RegistryEvidence

from ._base import EvidencePackageBuilder, normalize_registry_path


class RegistryEvidenceBuilder(EvidencePackageBuilder):
    evidence_type = EvidenceType.REGISTRY
    payload_model = RegistryEvidence

    def _normalize(self, raw_evidence: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(raw_evidence)
        if "key_path" in normalized:
            normalized["key_path"] = normalize_registry_path(normalized["key_path"])
        return normalized
