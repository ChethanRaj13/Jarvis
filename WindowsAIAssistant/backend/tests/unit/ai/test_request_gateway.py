import pytest

from backend.config import Settings
from backend.ai.schemas import TaskProcessRequest


def test_task_process_request_validation():
    """Verify TaskProcessRequest schema validation."""
    request = TaskProcessRequest(
        text="install software",
        session_id="test-session",
        include_verification=True
    )
    
    assert request.text == "install software"
    assert request.session_id == "test-session"
    assert request.include_verification is True


def test_settings_load():
    """Verify Settings can be loaded."""
    settings = Settings.load()
    assert settings.api_prefix == "/api/v1"

