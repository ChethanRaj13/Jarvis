from __future__ import annotations

from dataclasses import dataclass

from .._base import DriftAccumulationResult, DriftObservation
from ..exceptions import InvalidAnalysisInput


@dataclass(frozen=True)
class DriftAttributionResult:
    expected: tuple[DriftObservation, ...]
    unexpected: tuple[DriftObservation, ...]
    authorized: tuple[DriftObservation, ...]
    unauthorized: tuple[DriftObservation, ...]
    rationale: tuple[str, ...]


class DriftAttributor:
    def attribute(self, accumulation: DriftAccumulationResult) -> DriftAttributionResult:
        if not isinstance(accumulation, DriftAccumulationResult):
            raise InvalidAnalysisInput("drift attribution requires accumulated drift observations")
        expected = tuple(observation for observation in accumulation.observations if observation.expected_drift)
        unexpected = tuple(observation for observation in accumulation.observations if not observation.expected_drift)
        authorized = tuple(observation for observation in accumulation.observations if observation.authorized)
        unauthorized = tuple(observation for observation in accumulation.observations if not observation.authorized)
        rationale = tuple(self._rationale(observation) for observation in accumulation.observations) or (
            "no drift requiring attribution",
        )
        return DriftAttributionResult(expected, unexpected, authorized, unauthorized, rationale)

    def _rationale(self, observation: DriftObservation) -> str:
        expectation = "expected" if observation.expected_drift else "unexpected"
        authorization = "authorized" if observation.authorized else "unauthorized"
        return f"{observation.attribute} is {expectation} and {authorization}"
