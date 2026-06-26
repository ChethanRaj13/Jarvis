from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from pydantic import ValidationError

from WindowsAIAssistant.backend.verification_engine.contracts import ExecutionCompletionSignal, IExecutionLayerTriggerAdapter, VerificationRequest


class ExecutionLayerTriggerAdapter(IExecutionLayerTriggerAdapter):
    def __init__(
        self,
        *,
        session_id_resolver: Callable[[ExecutionCompletionSignal], str] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session_id_resolver = session_id_resolver or (lambda _signal: "default-session")
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def receive_signal(self, signal: ExecutionCompletionSignal) -> VerificationRequest | None:
        try:
            return VerificationRequest(
                request_id=signal.request_id,
                action_type=signal.action_type,
                execution_timestamp=signal.execution_timestamp,
                trigger_received_timestamp=self._clock(),
                session_id=self._session_id_resolver(signal),
                execution_layer_id=signal.execution_layer_id,
                action_subtype=signal.action_subtype,
            )
        except (TypeError, ValueError, ValidationError):
            return None
