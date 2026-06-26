from typing import Any

from WindowsAIAssistant.backend.verification_engine.contracts import ConfigurationSnapshot, EvidenceType

from ._base import EvidencePackageBuilder, normalize_registry_path, normalize_windows_path


class ConfigurationEvidenceBuilder(EvidencePackageBuilder):
    evidence_type = EvidenceType.CONFIGURATION
    payload_model = ConfigurationSnapshot

    def _normalize(self, raw_evidence: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(raw_evidence)
        source_type = str(normalized.get("config_source_type", "")).upper()
        if "config_source_type" in normalized:
            normalized["config_source_type"] = source_type
        if "config_path" in normalized and source_type == "FILE":
            normalized["config_path"] = normalize_windows_path(normalized["config_path"])
        if "config_path" in normalized and source_type == "REGISTRY":
            normalized["config_path"] = normalize_registry_path(normalized["config_path"])
        if "config_format" in normalized:
            normalized["config_format"] = str(normalized["config_format"]).upper()
        if "all_key_value_pairs" in normalized:
            normalized["all_key_value_pairs"] = dict(normalized["all_key_value_pairs"])
        return normalized
