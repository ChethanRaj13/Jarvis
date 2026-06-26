from __future__ import annotations

from pathlib import PureWindowsPath
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ValidationError

from WindowsAIAssistant.backend.verification_engine.contracts import EvidencePackage, EvidenceType

from .exceptions import EvidenceBuilderValidationError


class EvidencePackageBuilder:
    evidence_type: EvidenceType
    payload_model: type[BaseModel]

    def build(
        self,
        raw_evidence: dict[str, Any],
        *,
        request_id: UUID,
        collection_timestamp: Any,
        collection_window_open: bool,
        binding_token: str,
        collector_id: str,
        evidence_id: UUID | None = None,
        pre_execution_baseline_id: UUID | None = None,
        collection_duration_ms: int | None = None,
    ) -> EvidencePackage:
        try:
            payload = self.payload_model.model_validate(self._normalize(raw_evidence))
            return EvidencePackage(
                evidence_id=evidence_id or uuid4(),
                request_id=request_id,
                evidence_type=self.evidence_type,
                collection_timestamp=collection_timestamp,
                collection_window_open=collection_window_open,
                binding_token=binding_token,
                collector_id=collector_id,
                evidence_payload=payload.model_dump(mode="json"),
                pre_execution_baseline_id=pre_execution_baseline_id,
                collection_duration_ms=collection_duration_ms,
            )
        except (TypeError, ValueError, ValidationError) as exc:
            raise EvidenceBuilderValidationError(
                f"{type(self).__name__} could not build an evidence package"
            ) from exc

    def _normalize(self, raw_evidence: dict[str, Any]) -> dict[str, Any]:
        return dict(raw_evidence)


def normalize_windows_path(value: Any) -> str:
    return str(PureWindowsPath(str(value).strip()))


def normalize_registry_path(value: Any) -> str:
    path = "\\".join(part for part in str(value).strip().replace("/", "\\").split("\\") if part)
    hive, separator, remainder = path.partition("\\")
    normalized_hive = {
        "HKEY_LOCAL_MACHINE": "HKLM",
        "HKEY_CURRENT_USER": "HKCU",
        "HKLM": "HKLM",
        "HKCU": "HKCU",
    }.get(hive.upper(), hive.upper())
    return f"{normalized_hive}{separator}{remainder}"
