from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel

from WindowsAIAssistant.backend.verification_engine.config.exceptions import ConfigurationError
from WindowsAIAssistant.backend.verification_engine.config.loader import JsonConfigLoader

from WindowsAIAssistant.backend.verification_engine.security.integrity.config_integrity_verifier import (
    ConfigIntegrityVerifier,
)


@dataclass(frozen=True)
class RequiredConfiguration:
    name: str
    path: Path
    model_type: type[BaseModel]


@dataclass(frozen=True)
class StartupCheckResult:
    check_name: str
    passed: bool
    mandatory: bool
    messages: tuple[str, ...] = ()


class ConfigIntegrityCheck:
    def __init__(
        self,
        required_configurations: tuple[RequiredConfiguration, ...],
        loader: JsonConfigLoader | None = None,
        verifier: ConfigIntegrityVerifier | None = None,
        mandatory: bool = True,
    ) -> None:
        self._required_configurations = required_configurations
        self._loader = loader or JsonConfigLoader()
        self._verifier = verifier or ConfigIntegrityVerifier()
        self._mandatory = mandatory

    def run(self) -> StartupCheckResult:
        messages: list[str] = []
        for required in self._required_configurations:
            path = Path(required.path).expanduser().resolve()
            if not path.exists():
                messages.append(f"{required.name}: configuration file does not exist")
                continue
            if not path.is_file():
                messages.append(f"{required.name}: configuration path is not a file")
                continue
            try:
                with path.open("r", encoding="utf-8"):
                    pass
            except OSError:
                messages.append(f"{required.name}: configuration file is not readable")
                continue
            try:
                data = dict(self._loader.load_json(path))
            except ConfigurationError as exc:
                messages.append(f"{required.name}: {exc}")
                continue
            validation = self._verifier.validate_data(data, required.model_type)
            if not validation.valid:
                messages.extend(f"{required.name}: {error}" for error in validation.errors)

        return StartupCheckResult(
            check_name="configuration_integrity",
            passed=not messages,
            mandatory=self._mandatory,
            messages=tuple(messages),
        )
