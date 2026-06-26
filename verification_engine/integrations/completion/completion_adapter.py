from __future__ import annotations

from collections.abc import Callable
from typing import Any

from verification_engine.contracts import ICompletionReportingAdapter, VerificationOutcomeMessage


class CompletionReportingAdapter(ICompletionReportingAdapter):
    def __init__(
        self,
        *,
        outcome_sink: Callable[[VerificationOutcomeMessage], None] | None = None,
    ) -> None:
        self._outcome_sink = outcome_sink
        self.delivered_outcomes: list[VerificationOutcomeMessage] = []

    def deliver_outcome(self, message: VerificationOutcomeMessage) -> None:
        if self._outcome_sink is not None:
            self._outcome_sink(message)
            return
        self.delivered_outcomes.append(message)
