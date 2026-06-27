from __future__ import annotations

import os
from pathlib import Path
from string import Template
from typing import Any

from .schemas import TaskProcessRequest


class PromptOrchestrator:
    def __init__(self, prompt_directory: str):
        self.prompt_directory = Path(prompt_directory)
        if not self.prompt_directory.is_absolute():
            self.prompt_directory = Path(__file__).resolve().parent.parent / prompt_directory
        self.templates: dict[str, Template] = {}
        self._load_templates()

    def _load_templates(self) -> None:
        if not self.prompt_directory.exists():
            return

        for prompt_file in self.prompt_directory.glob("*.txt"):
            template_name = prompt_file.stem
            self.templates[template_name] = Template(prompt_file.read_text())

    def build(self, prompt_name: str, variables: dict[str, Any]) -> str:
        template = self.templates.get(prompt_name)
        if template is None:
            raise ValueError(f"Prompt template '{prompt_name}' not found.")

        safe_vars = {k: self._serialize(v) for k, v in variables.items()}
        return template.safe_substitute(safe_vars)

    @staticmethod
    def _serialize(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (list, dict)):
            return str(value)
        return str(value)
