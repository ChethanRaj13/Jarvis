from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any


class PipelineState(str, Enum):
    INITIALIZED = "INITIALIZED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    EARLY_EXIT = "EARLY_EXIT"


@dataclass(frozen=True)
class PipelineStep:
    name: str
    action: Callable[[Any], Any]
    fail_closed: bool = True


@dataclass(frozen=True)
class EarlyExit:
    value: Any
    reason: str


@dataclass(frozen=True)
class PipelineResult:
    state: PipelineState
    value: Any
    completed_steps: tuple[str, ...]
    failed_step: str | None = None
    error: Exception | None = None
    fail_closed: bool = False
    early_exit_reason: str | None = None


class ExecutionPipeline:
    def run(self, initial_value: Any, steps: tuple[PipelineStep, ...]) -> PipelineResult:
        value = initial_value
        completed: list[str] = []
        for step in steps:
            try:
                next_value = step.action(value)
            except Exception as exc:
                return PipelineResult(
                    state=PipelineState.FAILED,
                    value=value,
                    completed_steps=tuple(completed),
                    failed_step=step.name,
                    error=exc,
                    fail_closed=step.fail_closed,
                )
            if isinstance(next_value, EarlyExit):
                return PipelineResult(
                    state=PipelineState.EARLY_EXIT,
                    value=next_value.value,
                    completed_steps=tuple(completed + [step.name]),
                    early_exit_reason=next_value.reason,
                )
            completed.append(step.name)
            value = next_value
        return PipelineResult(PipelineState.COMPLETED, value, tuple(completed))
