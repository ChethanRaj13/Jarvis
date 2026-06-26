from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping
from uuid import UUID

from verification_engine.contracts import EvidencePackage, EvidenceType
from verification_engine.evidence.builders import EvidenceBuilderValidationError
from verification_engine.evidence.builders._base import EvidencePackageBuilder

from .exceptions import CollectionFailure, InvalidCollectionRequest, UnsupportedCollection


@dataclass(frozen=True)
class CollectionRequest:
    request_id: UUID
    evidence_type: EvidenceType
    raw_evidence: Mapping[str, Any]
    collection_timestamp: datetime
    collection_window_open: bool
    binding_token: str
    collector_id: str
    evidence_id: UUID | None = None
    pre_execution_baseline_id: UUID | None = None
    collection_duration_ms: int | None = None
    collection_context: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RawEvidence:
    values: Mapping[str, Any]

    def as_mapping(self) -> Mapping[str, Any]:
        return self.values


class BaseCollector:
    evidence_type: EvidenceType
    builder: EvidencePackageBuilder

    def collect(self, request: CollectionRequest) -> EvidencePackage:
        self._validate_request(request)
        raw_evidence = self._collect_raw_evidence(request)
        try:
            return self.builder.build(
                dict(raw_evidence.as_mapping()),
                request_id=request.request_id,
                collection_timestamp=request.collection_timestamp,
                collection_window_open=request.collection_window_open,
                binding_token=request.binding_token,
                collector_id=request.collector_id,
                evidence_id=request.evidence_id,
                pre_execution_baseline_id=request.pre_execution_baseline_id,
                collection_duration_ms=request.collection_duration_ms,
            )
        except EvidenceBuilderValidationError as exc:
            raise CollectionFailure(f"{type(self).__name__} failed to assemble evidence") from exc

    def _collect_raw_evidence(self, request: CollectionRequest) -> RawEvidence:
        return RawEvidence(values=request.raw_evidence)

    def _validate_request(self, request: CollectionRequest) -> None:
        if request.evidence_type != self.evidence_type:
            raise UnsupportedCollection(
                f"{type(self).__name__} does not support {request.evidence_type.value}"
            )
        if not request.raw_evidence:
            raise InvalidCollectionRequest("raw_evidence is required")
        if not request.binding_token:
            raise InvalidCollectionRequest("binding_token is required")
        if not request.collector_id:
            raise InvalidCollectionRequest("collector_id is required")
