import pytest

from backend.ai.context_engine import ContextEngine
from backend.ai.schemas import TaskProcessRequest


def test_context_engine_builds_prompt():
    engine = ContextEngine(max_items=5)
    request = TaskProcessRequest(
        text="install python",
        session_id="test-session",
        session_context="User is on Windows 10",
        memory_summaries=["Previous: installed git", "Previous: used powershell"]
    )
    
    context = engine.build_prompt_context(request)
    assert "test-session" in context
    assert "install python" in context
    assert "Windows 10" in context
    assert "git" in context


def test_context_engine_handles_empty_memory():
    engine = ContextEngine()
    request = TaskProcessRequest(text="hello", session_id="default")
    
    context = engine.build_prompt_context(request)
    assert "hello" in context
    assert "default" in context
