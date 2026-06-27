import pytest
import tempfile
from pathlib import Path

from backend.ai.prompt_orchestrator import PromptOrchestrator


def test_prompt_orchestrator_loads_templates(tmp_path):
    template_file = tmp_path / "test.txt"
    template_file.write_text("Hello $name")
    orchestrator = PromptOrchestrator(str(tmp_path))

    assert orchestrator.build("test", {"name": "world"}) == "Hello world"
