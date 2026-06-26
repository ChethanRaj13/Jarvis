from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from verification_engine.contracts import (
    AuthorizationRetrievalRequest,
    ExecutionCompletionSignal,
    ICompletionReportingAdapter,
    IExecutionLayerTriggerAdapter,
    ISafetyEngineAuthorizationAdapter,
    VerificationDecision,
    VerificationDecisionEnum,
    VerificationOutcomeMessage,
)
from verification_engine.orchestrator import ExecutionContext, VerificationOrchestrator


class InvalidVerificationSignal(ValueError):
    pass


class VerificationTriggerService:
    def __init__(
        self,
        *,
        execution_adapter: IExecutionLayerTriggerAdapter,
        safety_adapter: ISafetyEngineAuthorizationAdapter,
        completion_adapter: ICompletionReportingAdapter | None = None,
        orchestrator_factory: Callable[[ExecutionContext], VerificationOrchestrator] | None = None,
        context_factory: Callable[[Any, Any], ExecutionContext] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._execution_adapter = execution_adapter
        self._safety_adapter = safety_adapter
        self._completion_adapter = completion_adapter
        self._orchestrator_factory = orchestrator_factory or (lambda _context: VerificationOrchestrator())
        self._context_factory = context_factory or (
            lambda request, authorization: ExecutionContext(request=request, authorization=authorization)
        )
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def verify(self, signal: ExecutionCompletionSignal) -> VerificationDecision:
        request = self._execution_adapter.receive_signal(signal)
        if request is None:
            raise InvalidVerificationSignal("invalid execution completion signal")

        try:
            authorization = self._safety_adapter.retrieve_authorization(
                AuthorizationRetrievalRequest(
                    request_id=request.request_id,
                    requester_id="verification-engine-api",
                    retrieval_timestamp=self._clock(),
                )
            )
            context = self._context_factory(request, authorization)
            outcome = self._orchestrator_factory(context).execute(context)
            decision = outcome.decision

            # TODO (Version 1.1)
            # AuditService.write(...)

            self._deliver_outcome(decision)
            return decision
        except Exception as exc:
            decision = self._escalate(signal.request_id, f"verification failed closed: {exc}")
            self._deliver_outcome(decision)
            return decision

    def _deliver_outcome(self, decision: VerificationDecision) -> None:
        if self._completion_adapter is None:
            return
        self._completion_adapter.deliver_outcome(
            VerificationOutcomeMessage(
                request_id=decision.request_id,
                final_decision=decision.final_decision,
                record_id=decision.decision_id,
                audit_integrity_hash="0" * 64,
                decision_timestamp=decision.decision_timestamp,
                escalation_expiry=decision.escalation_expiry,
                partial_scope_description=decision.partial_scope_description,
            )
        )

    def _escalate(self, request_id: UUID, rationale: str) -> VerificationDecision:
        now = self._clock()
        source_id = uuid4()
        return VerificationDecision(
            decision_id=uuid4(),
            request_id=request_id,
            final_decision=VerificationDecisionEnum.ESCALATE,
            controlling_results=[source_id],
            full_rationale=rationale,
            all_results=[source_id],
            decision_timestamp=now,
            decision_engine_version="api-fail-closed-v1",
            escalation_expiry=now + timedelta(minutes=30),
        )


__all__ = ["InvalidVerificationSignal", "VerificationTriggerService"]
