from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any
from uuid import UUID

from WindowsAIAssistant.backend.verification_engine.contracts import (
    AuthorizationRecord,
    AuthorizationRetrievalRequest,
    ISafetyEngineAuthorizationAdapter,
)


class SafetyEngineAuthorizationNotFound(LookupError):
    pass


class SafetyEngineAuthorizationAdapter(ISafetyEngineAuthorizationAdapter):
    def __init__(
        self,
        *,
        authorization_provider: Callable[[AuthorizationRetrievalRequest], AuthorizationRecord | Mapping[str, Any]] | None = None,
        authorization_records: Mapping[UUID, AuthorizationRecord | Mapping[str, Any]] | None = None,
    ) -> None:
        self._authorization_provider = authorization_provider
        self._authorization_records = authorization_records or {}

    def retrieve_authorization(self, request: AuthorizationRetrievalRequest) -> AuthorizationRecord:
        raw_record = self._retrieve_raw_record(request)
        record = raw_record if isinstance(raw_record, AuthorizationRecord) else AuthorizationRecord.model_validate(raw_record)
        if record.request_id != request.request_id:
            raise ValueError("authorization record request_id does not match retrieval request")
        return record

    def _retrieve_raw_record(
        self,
        request: AuthorizationRetrievalRequest,
    ) -> AuthorizationRecord | Mapping[str, Any]:
        if self._authorization_provider is not None:
            return self._authorization_provider(request)
        try:
            return self._authorization_records[request.request_id]
        except KeyError as exc:
            raise SafetyEngineAuthorizationNotFound(
                f"authorization record not found for request {request.request_id}"
            ) from exc
