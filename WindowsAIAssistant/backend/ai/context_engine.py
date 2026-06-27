from __future__ import annotations

from typing import List

from .schemas import TaskProcessRequest


class ContextEngine:
    def __init__(self, max_items: int = 10):
        self.max_items = max_items

    def build_prompt_context(self, request: TaskProcessRequest) -> str:
        parts: List[str] = []

        parts.append(f"Session ID: {request.session_id}")
        if request.session_context:
            parts.append(f"Session context:\n{request.session_context}")
        if request.memory_summaries:
            parts.append("Memory summaries:")
            parts.extend(f"- {summary}" for summary in request.memory_summaries[: self.max_items])
        parts.append(f"User request: {request.text}")

        return "\n\n".join(parts)
