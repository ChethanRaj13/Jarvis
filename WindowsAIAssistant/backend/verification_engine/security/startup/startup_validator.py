from dataclasses import dataclass
from typing import Protocol

from .config_integrity_check import StartupCheckResult
from .restricted_mode_enforcer import RestrictedModeEnforcer


class StartupCheck(Protocol):
    def run(self) -> StartupCheckResult:
        ...


@dataclass(frozen=True)
class StartupFailure:
    check_name: str
    mandatory: bool
    messages: tuple[str, ...]


@dataclass(frozen=True)
class StartupResult:
    startup_allowed: bool
    restricted_mode: bool
    checks: tuple[StartupCheckResult, ...]
    failures: tuple[StartupFailure, ...]


class StartupValidator:
    def __init__(
        self,
        checks: tuple[StartupCheck, ...],
        restricted_mode_enforcer: RestrictedModeEnforcer,
    ) -> None:
        self._checks = checks
        self._restricted_mode_enforcer = restricted_mode_enforcer

    def validate(self) -> StartupResult:
        check_results: list[StartupCheckResult] = []
        failures: list[StartupFailure] = []

        for check in self._checks:
            try:
                result = check.run()
            except Exception as exc:
                result = StartupCheckResult(
                    check_name=type(check).__name__,
                    passed=False,
                    mandatory=True,
                    messages=(str(exc),),
                )
            check_results.append(result)
            if not result.passed:
                failures.append(
                    StartupFailure(
                        check_name=result.check_name,
                        mandatory=result.mandatory,
                        messages=result.messages,
                    )
                )

        mandatory_failure = any(failure.mandatory for failure in failures)
        if mandatory_failure:
            self._restricted_mode_enforcer.enable()
        else:
            self._restricted_mode_enforcer.disable()

        return StartupResult(
            startup_allowed=not mandatory_failure,
            restricted_mode=self._restricted_mode_enforcer.is_restricted(),
            checks=tuple(check_results),
            failures=tuple(failures),
        )
