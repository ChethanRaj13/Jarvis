from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel

try:
    from langchain_ollama import ChatOllama
except ImportError:  # pragma: no cover
    ChatOllama = None

from ..config import Settings


class ModelManagerConfig(BaseModel):
    model_name: str
    base_url: str
    temperature: float
    timeout_seconds: int
    max_retries: int


class ModelManager:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.config = ModelManagerConfig(
            model_name=self.settings.model.name,
            base_url=self.settings.model.base_url,
            temperature=self.settings.model.temperature,
            timeout_seconds=self.settings.model.timeout_seconds,
            max_retries=self.settings.model.max_retries,
        )
        self.client: ChatOllama | None = None

    def _load_model(self) -> None:
        if ChatOllama is None:
            raise ImportError(
                "The langchain_ollama dependency is required for LLM model inference. "
                "Install it or configure a stub model for testing."
            )

        self.client = ChatOllama(
            model=self.config.model_name,
            base_url=self.config.base_url,
            temperature=self.config.temperature,
        )

    def health_check(self) -> bool:
        if self.client is None:
            self._load_model()
        try:
            response = self.client.predict("ping")
            return bool(response is not None)
        except Exception:
            return False

    def infer(self, prompt: str) -> str:
        if self.client is None:
            self._load_model()

        last_exception: Exception | None = None
        for attempt in range(self.config.max_retries + 1):
            try:
                result = self.client.predict(prompt)
                return result.content if hasattr(result, "content") else str(result)
            except Exception as exc:
                last_exception = exc
                time.sleep(0.5)

        raise RuntimeError(f"LLM inference failed after {self.config.max_retries + 1} attempts") from last_exception
