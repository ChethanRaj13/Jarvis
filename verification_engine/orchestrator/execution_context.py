from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping

from verification_engine.contracts import AuthorizationRecord, VerificationRequest


@dataclass(frozen=True)
class ExecutionContext:
    request: VerificationRequest
    authorization: AuthorizationRecord
    collection_requests: tuple[Any, ...] = ()
    validation_context: Any | None = None
    execution_metadata: Mapping[str, Any] = field(default_factory=dict)
    configuration: Mapping[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
