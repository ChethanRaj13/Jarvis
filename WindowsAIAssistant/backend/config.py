import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    name: str = Field(default="llama3.2:latest")
    base_url: str = Field(default="http://localhost:11434")
    temperature: float = Field(default=0.0)
    timeout_seconds: int = Field(default=30)
    max_retries: int = Field(default=2)


class PromptConfig(BaseModel):
    directory: str = Field(default="prompts")
    context_window_tokens: int = Field(default=2048)
    max_context_items: int = Field(default=10)


class FeatureFlags(BaseModel):
    enable_safety_analysis: bool = Field(default=True)
    enable_verification_planning: bool = Field(default=True)


class Settings(BaseModel):
    model: ModelConfig = ModelConfig()
    prompt: PromptConfig = PromptConfig()
    feature_flags: FeatureFlags = FeatureFlags()
    api_prefix: str = Field(default="/api/v1")
    health_check_prompt: str = Field(default="You are a model health check agent. Respond with OK.")
    config_path: str | None = Field(default=None)

    @classmethod
    def load(cls, path: str | None = None) -> "Settings":
        config_path = Path(path or os.getenv("JARVIS_CONFIG_PATH", "."))
        if config_path.is_dir():
            config_path = config_path / "config.json"

        if config_path.exists():
            try:
                payload = json.loads(config_path.read_text())
            except Exception:
                payload = {}
            return cls(**payload)

        return cls()
