from __future__ import annotations

from fastapi import HTTPException

from .ai.schemas import (
    ChatRespondRequest,
    ChatRespondResponse,
    MemorySummarizeRequest,
    TaskProcessRequest,
    TaskProcessResponse,
    VerificationPlanRequest,
)
from .ai.context_engine import ContextEngine
from .ai.model_manager import ModelManager
from .ai.prompt_orchestrator import PromptOrchestrator
from .ai.response_formatter import ResponseFormatter
from .ai.safety_analysis import SafetyAnalysisEngine
from .ai.verification_planner import VerificationPlanner
from .config import Settings
from .intent_parser import IntentParser
from .task_planner import TaskPlanner


class RequestGateway:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.intent_parser = IntentParser()
        self.task_planner = TaskPlanner()
        self.model_manager = ModelManager(settings)
        self.context_engine = ContextEngine(max_items=settings.prompt.max_context_items)
        self.prompt_orchestrator = PromptOrchestrator(settings.prompt.directory)
        self.safety_engine = SafetyAnalysisEngine()
        self.verification_planner = VerificationPlanner()
        self.response_formatter = ResponseFormatter()

    def process_task(self, request: TaskProcessRequest) -> TaskProcessResponse:
        if not request.text or not request.text.strip():
            raise HTTPException(status_code=400, detail="`text` must not be empty.")

        intent = self.intent_parser.parse(request.text)
        context = self.context_engine.build_prompt_context(request)

        plan = self.task_planner.plan(intent)

        safety = self.safety_engine.analyze(request.text, plan.model_dump())

        return TaskProcessResponse(
            intent=intent.model_dump(),
            plan=plan.model_dump(),
            safety=safety.model_dump(),
        )

    def create_verification_plan(self, request: VerificationPlanRequest) -> dict:
        verification_plan = self.verification_planner.build_plan(request.plan, request.task_description)
        return verification_plan.model_dump()

    def summarize_memory(self, request: MemorySummarizeRequest) -> str:
        if not request.documents:
            raise HTTPException(status_code=400, detail="`documents` must not be empty.")

        prompt = self.prompt_orchestrator.build("summarization", {"documents": "\n\n".join(request.documents)})
        result = self.model_manager.infer(prompt)
        return result.strip()

    def chat_respond(self, request: ChatRespondRequest) -> ChatRespondResponse:
        if not request.message or not request.message.strip():
            raise HTTPException(status_code=400, detail="`message` must not be empty.")

        prompt = self.prompt_orchestrator.build(
            "chat_respond",
            {
                "context": request.session_context or "",
                "memory_summaries": "\n".join(request.memory_summaries),
                "user_text": request.message,
            },
        )
        response = self.model_manager.infer(prompt)
        return self.response_formatter.validate({"response": response, "metadata": {}}, ChatRespondResponse)
