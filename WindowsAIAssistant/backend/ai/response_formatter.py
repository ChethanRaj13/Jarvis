from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ValidationError


class ResponseFormatter:
    @staticmethod
    def validate(payload: Any, model: type[BaseModel]) -> BaseModel:
        if isinstance(payload, model):
            return payload

        if isinstance(payload, str):
            try:
                parsed = json.loads(payload)
            except json.JSONDecodeError as exc:
                raise ValueError("Invalid JSON response") from exc
            payload = parsed

        try:
            return model.parse_obj(payload)
        except ValidationError as exc:
            repaired = ResponseFormatter._repair(payload)
            return model.parse_obj(repaired)

    @staticmethod
    def _repair(payload: Any) -> Any:
        if isinstance(payload, str):
            try:
                return json.loads(payload)
            except json.JSONDecodeError:
                raise ValueError("Unable to repair malformed JSON")
        return payload
