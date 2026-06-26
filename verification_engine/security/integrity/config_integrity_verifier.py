from dataclasses import dataclass
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError


ConfigModel = TypeVar("ConfigModel", bound=BaseModel)


@dataclass(frozen=True)
class ConfigurationValidationResult:
    valid: bool
    model_name: str
    errors: tuple[str, ...] = ()


class ConfigIntegrityVerifier:
    def validate_model(self, config: BaseModel) -> ConfigurationValidationResult:
        return ConfigurationValidationResult(valid=True, model_name=type(config).__name__)

    def validate_data(
        self,
        config_data: dict[str, Any],
        model_type: type[ConfigModel],
    ) -> ConfigurationValidationResult:
        try:
            model_type.model_validate(config_data)
        except ValidationError as exc:
            return ConfigurationValidationResult(
                valid=False,
                model_name=model_type.__name__,
                errors=tuple(error["msg"] for error in exc.errors()),
            )
        return ConfigurationValidationResult(valid=True, model_name=model_type.__name__)
