from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import ClassVar

from .exceptions import InvalidStateTransition


class OrchestratorState(str, Enum):
    INITIALIZED = "INITIALIZED"
    COLLECTING = "COLLECTING"
    VALIDATING = "VALIDATING"
    VERIFYING = "VERIFYING"
    ANALYZING = "ANALYZING"
    DECIDING = "DECIDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class StateMachine:
    state: OrchestratorState = OrchestratorState.INITIALIZED

    _legal_transitions: ClassVar[dict[OrchestratorState, frozenset[OrchestratorState]]] = {
        OrchestratorState.INITIALIZED: frozenset({OrchestratorState.COLLECTING, OrchestratorState.FAILED}),
        OrchestratorState.COLLECTING: frozenset({OrchestratorState.VALIDATING, OrchestratorState.FAILED}),
        OrchestratorState.VALIDATING: frozenset({OrchestratorState.VERIFYING, OrchestratorState.FAILED}),
        OrchestratorState.VERIFYING: frozenset({OrchestratorState.ANALYZING, OrchestratorState.FAILED}),
        OrchestratorState.ANALYZING: frozenset({OrchestratorState.DECIDING, OrchestratorState.FAILED}),
        OrchestratorState.DECIDING: frozenset({OrchestratorState.COMPLETED, OrchestratorState.FAILED}),
        OrchestratorState.COMPLETED: frozenset(),
        OrchestratorState.FAILED: frozenset(),
    }

    def transition(self, next_state: OrchestratorState) -> "StateMachine":
        if next_state not in self._legal_transitions[self.state]:
            raise InvalidStateTransition(f"illegal transition from {self.state.value} to {next_state.value}")
        return StateMachine(next_state)
