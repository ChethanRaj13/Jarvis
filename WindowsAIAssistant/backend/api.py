from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

BACKEND_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_ROOT.parent
for path in (BACKEND_ROOT, PROJECT_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import types

if "WindowsAIAssistant" not in sys.modules:
    windows_pkg = types.ModuleType("WindowsAIAssistant")
    windows_pkg.__path__ = [str(PROJECT_ROOT)]
    sys.modules["WindowsAIAssistant"] = windows_pkg

if "WindowsAIAssistant.backend" not in sys.modules:
    backend_pkg = types.ModuleType("WindowsAIAssistant.backend")
    backend_pkg.__path__ = [str(BACKEND_ROOT)]
    sys.modules["WindowsAIAssistant.backend"] = backend_pkg

try:
    from intent_parser import IntentParser
    from task_planner import TaskPlanner
except ModuleNotFoundError:  # pragma: no cover - fallback for package-style imports
    from .intent_parser import IntentParser
    from .task_planner import TaskPlanner

try:
    from verification_engine.api.dependencies import build_execution_context, build_orchestrator
    from verification_engine.api.trigger import VerificationTriggerService
    from verification_engine.contracts import ActionType, AuthorizationRecord, ExecutionCompletionSignal, RiskLevel
    from verification_engine.integrations.completion.completion_adapter import CompletionReportingAdapter
    from verification_engine.integrations.execution_layer.execution_layer_adapter import ExecutionLayerTriggerAdapter
    from verification_engine.integrations.safety_engine.safety_engine_adapter import SafetyEngineAuthorizationAdapter
except ModuleNotFoundError:  # pragma: no cover - fallback for package-style imports
    from .verification_engine.api.dependencies import build_execution_context, build_orchestrator
    from .verification_engine.api.trigger import VerificationTriggerService
    from .verification_engine.contracts import ActionType, AuthorizationRecord, ExecutionCompletionSignal, RiskLevel
    from .verification_engine.integrations.completion.completion_adapter import CompletionReportingAdapter
    from .verification_engine.integrations.execution_layer.execution_layer_adapter import ExecutionLayerTriggerAdapter
    from .verification_engine.integrations.safety_engine.safety_engine_adapter import SafetyEngineAuthorizationAdapter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("intent-api")

app = FastAPI(title="Jarvis Intent + Planning API", version="1.1.0")

# Allow the WPF app (running locally, no browser origin) to call this freely.
# Tighten allow_origins if you ever expose this beyond localhost.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Build both once at startup, not per-request — each holds its own ChatOllama
# connection, which is reused across calls instead of being re-created every time.
intent_parser = IntentParser()
task_planner = TaskPlanner()


class ParseRequest(BaseModel):
    text: str


class ExecuteRequest(BaseModel):
    steps: list[str] = Field(default_factory=list)
    verify: bool = False
    target_resource: str = "."


class VerifyRequest(BaseModel):
    request_id: str | None = None
    steps: list[str] = Field(default_factory=list)
    action_type: str = "FILE_CREATE"
    target_resource: str = "."
    expected_outcome_specification: dict[str, Any] = Field(default_factory=dict)
    risk_level: str = "low"
    session_id: str = "ui-session"


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/parse")
def parse_text(request: ParseRequest) -> dict:
    """Runs raw text through IntentParser only."""
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="`text` must not be empty.")

    try:
        intent = intent_parser.parse(request.text)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Intent parsing failed for: %s", request.text)
        raise HTTPException(status_code=500, detail=f"Intent parsing failed: {exc}") from exc

    return intent.model_dump()


@app.post("/plan")
def plan_text(request: ParseRequest) -> dict:
    """Full pipeline: text -> IntentParser -> StructuredIntent -> TaskPlanner -> TaskPlan."""
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="`text` must not be empty.")

    try:
        intent = intent_parser.parse(request.text)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Intent parsing failed for: %s", request.text)
        raise HTTPException(status_code=500, detail=f"Intent parsing failed: {exc}") from exc

    try:
        task_plan = task_planner.plan(intent)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Task planning failed for intent from: %s", request.text)
        raise HTTPException(status_code=500, detail=f"Task planning failed: {exc}") from exc

    return {
        "intent": intent.model_dump(),
        "plan": task_plan.model_dump(),
    }


@app.post("/execute")
def execute_plan(request: ExecuteRequest) -> dict:
    """Executes a simple plan locally and optionally verifies it with the verification engine."""
    logs = [f"Executing: {step}" for step in request.steps]
    logs.append("Execution completed")

    verification = None
    if request.verify and request.steps:
        verification = verify_with_engine(
            request_id=str(uuid4()),
            steps=request.steps,
            target_resource=request.target_resource,
        )

    return {"logs": logs, "verification": verification}


@app.post("/verify")
def verify_text(request: VerifyRequest) -> dict:
    """Runs the verification engine for a plan execution request."""
    return verify_with_engine(
        request_id=request.request_id or str(uuid4()),
        steps=request.steps,
        action_type=request.action_type,
        target_resource=request.target_resource,
        expected_outcome_specification=request.expected_outcome_specification,
        risk_level=request.risk_level,
        session_id=request.session_id,
    )


def verify_with_engine(
    *,
    request_id: str,
    steps: list[str],
    action_type: str = "FILE_CREATE",
    target_resource: str = ".",
    expected_outcome_specification: dict[str, Any] | None = None,
    risk_level: str = "low",
    session_id: str = "ui-session",
) -> dict[str, Any]:
    try:
        parsed_action_type = ActionType(action_type.upper())
    except ValueError:
        parsed_action_type = ActionType.FILE_CREATE

    try:
        parsed_risk_level = RiskLevel(risk_level.lower())
    except ValueError:
        parsed_risk_level = RiskLevel.LOW

    request_uuid = UUID(request_id)
    signal = ExecutionCompletionSignal(
        request_id=request_uuid,
        action_type=parsed_action_type,
        execution_timestamp=datetime.now(timezone.utc),
        execution_layer_id="ui-execution-service",
        action_subtype="plan-execution",
    )

    authorization = AuthorizationRecord(
        authorization_id=f"auth-{request_uuid}",
        request_id=request_uuid,
        action_type=parsed_action_type,
        target_resource=target_resource,
        authorized_scope={"steps": steps},
        risk_level=parsed_risk_level,
        authorization_timestamp=datetime.now(timezone.utc),
        expected_outcome_specification=expected_outcome_specification or {"raw_evidence": {"steps": steps}},
        explicit_verification_requirements=["validate execution plan"],
        tool_ids_used=["ui-planning-service"],
        session_id=session_id,
    )

    service = VerificationTriggerService(
        execution_adapter=ExecutionLayerTriggerAdapter(),
        safety_adapter=SafetyEngineAuthorizationAdapter(authorization_records={request_uuid: authorization}),
        completion_adapter=CompletionReportingAdapter(),
        context_factory=build_execution_context,
        orchestrator_factory=build_orchestrator,
    )

    decision = service.verify(signal)
    return decision.model_dump()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)