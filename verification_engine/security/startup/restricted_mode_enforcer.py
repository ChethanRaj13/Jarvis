from dataclasses import dataclass
from enum import Enum
from threading import RLock


class RestrictedModeState(str, Enum):
    NORMAL = "NORMAL"
    RESTRICTED = "RESTRICTED"


@dataclass(frozen=True)
class RestrictedModeStatus:
    state: RestrictedModeState

    @property
    def is_restricted(self) -> bool:
        return self.state == RestrictedModeState.RESTRICTED


class RestrictedModeEnforcer:
    def __init__(self, initial_state: RestrictedModeState = RestrictedModeState.NORMAL) -> None:
        self._state = initial_state
        self._lock = RLock()

    def enable(self) -> RestrictedModeStatus:
        with self._lock:
            self._state = RestrictedModeState.RESTRICTED
            return self.status()

    def disable(self) -> RestrictedModeStatus:
        with self._lock:
            self._state = RestrictedModeState.NORMAL
            return self.status()

    def is_restricted(self) -> bool:
        with self._lock:
            return self._state == RestrictedModeState.RESTRICTED

    def status(self) -> RestrictedModeStatus:
        with self._lock:
            return RestrictedModeStatus(state=self._state)
