from __future__ import annotations

import logging
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .backend_router import RequestGateway
from .config import Settings
from .ai.schemas import (
    ChatRespondRequest,
    ChatRespondResponse,
    MemorySummarizeRequest,
    MemorySummarizeResponse,
    TaskProcessRequest,
    TaskProcessResponse,
    VerificationPlanRequest,
    VerificationPlanResponse,
)

try:
    from backend.intent_parser import IntentParser
    from backend.task_planner import TaskPlanner
except ModuleNotFoundError:  # pragma: no cover - fallback for package-style imports
    from .intent_parser import IntentParser
    from .task_planner import TaskPlanner

# Verification engine imports temporarily disabled - uses absolute WindowsAIAssistant paths
# Will be refactored later
try:
    from backend.verification_engine.api.dependencies import build_execution_context, build_orchestrator
    from backend.verification_engine.api.trigger import VerificationTriggerService
    from backend.verification_engine.contracts import ActionType, AuthorizationRecord, ExecutionCompletionSignal, RiskLevel
    from backend.verification_engine.integrations.completion.completion_adapter import CompletionReportingAdapter
    from backend.verification_engine.integrations.execution_layer.execution_layer_adapter import ExecutionLayerTriggerAdapter
    from backend.verification_engine.integrations.safety_engine.safety_engine_adapter import SafetyEngineAuthorizationAdapter
    VERIFICATION_ENGINE_AVAILABLE = True
except (ModuleNotFoundError, ImportError):
    VERIFICATION_ENGINE_AVAILABLE = False
    # Define dummy classes for type hints
    class ActionType: pass
    class AuthorizationRecord: pass
    class ExecutionCompletionSignal: pass
    class RiskLevel: pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("intent-api")

settings = Settings.load()
app = FastAPI(title="Jarvis AI Service", version="1.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_gateway() -> RequestGateway:
    return RequestGateway(settings)


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


class ExecutionCommand(BaseModel):
    command: str
    description: str
    tool: str | None = None


class ExecutionResponse(BaseModel):
    logs: list[str] = Field(default_factory=list)
    commands: list[ExecutionCommand] = Field(default_factory=list)
    verification: dict[str, Any] = Field(default_factory=dict)
    executed: bool = False


class VerifyResponse(BaseModel):
    final_decision: str = "VERIFIED"
    summary: str
    evidence: dict[str, Any] = Field(default_factory=dict)


@app.get("/api/v1/system/health")
def health(gateway: RequestGateway = Depends(get_gateway)) -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/task/process", response_model=TaskProcessResponse)
def process_task(request: TaskProcessRequest, gateway: RequestGateway = Depends(get_gateway)) -> TaskProcessResponse:
    return gateway.process_task(request)


@app.post("/api/v1/task/verification-plan", response_model=VerificationPlanResponse)
def verification_plan(request: VerificationPlanRequest, gateway: RequestGateway = Depends(get_gateway)) -> VerificationPlanResponse:
    plan = gateway.create_verification_plan(request)
    return VerificationPlanResponse(verification_plan=plan)


@app.post("/api/v1/memory/summarize", response_model=MemorySummarizeResponse)
def summarize_memory(request: MemorySummarizeRequest, gateway: RequestGateway = Depends(get_gateway)) -> MemorySummarizeResponse:
    summary = gateway.summarize_memory(request)
    return MemorySummarizeResponse(summary=summary)


@app.post("/api/v1/chat/respond", response_model=ChatRespondResponse)
def chat_respond(request: ChatRespondRequest, gateway: RequestGateway = Depends(get_gateway)) -> ChatRespondResponse:
    return gateway.chat_respond(request)


@app.post("/parse")
def parse_text(request: ParseRequest) -> dict:
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="`text` must not be empty.")

    try:
        intent = IntentParser().parse(request.text)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Intent parsing failed for: %s", request.text)
        raise HTTPException(status_code=500, detail=f"Intent parsing failed: {exc}") from exc

    return intent.model_dump()


@app.post("/plan")
def plan_text(request: ParseRequest) -> dict:
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="`text` must not be empty.")

    try:
        intent = IntentParser().parse(request.text)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Intent parsing failed for: %s", request.text)
        raise HTTPException(status_code=500, detail=f"Intent parsing failed: {exc}") from exc

    try:
        task_plan = TaskPlanner().plan(intent)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Task planning failed for intent from: %s", request.text)
        raise HTTPException(status_code=500, detail=f"Task planning failed: {exc}") from exc

    return {
        "intent": intent.model_dump(),
        "plan": task_plan.model_dump(),
    }


def _extract_target_path(step: str, fallback: str = "output.txt") -> str:
    normalized = step.strip()
    if not normalized:
        return fallback

    match = re.search(r"named\s+([^\s,.;]+)", normalized, flags=re.IGNORECASE)
    if match:
        return match.group(1)

    if "file" in normalized.lower():
        candidate = normalized.split("file", 1)[-1].strip(" .,:;")
        if candidate:
            return candidate

    if "directory" in normalized.lower() or "folder" in normalized.lower():
        candidate = normalized.split("directory", 1)[-1].strip(" .,:;") if "directory" in normalized.lower() else normalized.split("folder", 1)[-1].strip(" .,:;")
        if candidate:
            return candidate

    return fallback


def _build_command(step: str) -> tuple[str, str, str]:
    normalized = step.strip()
    lower_step = normalized.lower()

    if "create" in lower_step and "file" in lower_step:
        target_name = _extract_target_path(normalized, "output.txt")
        command = f"New-Item -ItemType File -Path '{target_name}' -Force | Out-Null"
        description = "Create a file for the requested task"
    elif "show" in lower_step or "read" in lower_step or "contents" in lower_step:
        command = "Get-ChildItem"
        description = "Inspect the current working directory contents"
    elif "folder" in lower_step or "directory" in lower_step:
        target_name = _extract_target_path(normalized, "workspace")
        command = f"New-Item -ItemType Directory -Path '{target_name}' -Force | Out-Null"
        description = "Create a working directory"
    else:
        command = f"Write-Output '{normalized}'"
        description = "Emit the requested action as a command"

    return command, "powershell", description


def _run_command(command: str, tool: str) -> tuple[bool, str]:
    if tool != "powershell":
        return False, "Unsupported tool"

    completed = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = "\n".join(part for part in [completed.stdout.strip(), completed.stderr.strip()] if part).strip()
    return completed.returncode == 0, output or "Command completed"


def execute_steps(request: ExecuteRequest) -> ExecutionResponse:
    if not request.steps:
        return ExecutionResponse(logs=["No execution steps were provided."], commands=[], executed=False)

    commands: list[ExecutionCommand] = []
    logs: list[str] = []

    for index, step in enumerate(request.steps, start=1):
        normalized = step.strip()
        if not normalized:
            continue

        command, tool, description = _build_command(normalized)
        commands.append(ExecutionCommand(command=command, description=description, tool=tool))
        logs.append(f"Step {index}: {normalized}")
        logs.append(f"Generated command: {command}")
        logs.append(f"Tool: {tool}")

    verification_payload: dict[str, Any] = {
        "verify": request.verify,
        "target_resource": request.target_resource,
        "status": "ready",
    }

    if request.verify:
        verification_payload["message"] = "Verification requested for the generated execution plan."
        verification_payload["evidence"] = {
            "resource": request.target_resource,
            "commands_generated": len(commands),
            "executed": False,
        }

    logs.append("Backend generated the commands but did not execute them. Frontend should run the returned commands locally.")

    return ExecutionResponse(logs=logs, commands=commands, verification=verification_payload, executed=False)


app.add_api_route("/execute", execute_steps, methods=["POST"], response_model=ExecutionResponse)
app.add_api_route("/api/v1/execute", execute_steps, methods=["POST"], response_model=ExecutionResponse)


@app.post("/verify", response_model=VerifyResponse)
def verify_steps(request: VerifyRequest) -> VerifyResponse:
    evidence: list[dict[str, Any]] = []
    target_root = Path(request.target_resource).expanduser()
    if not target_root.is_absolute():
        target_root = (Path.cwd() / target_root).resolve()

    for step in request.steps:
        normalized = step.strip()
        lower_step = normalized.lower()
        if "create" in lower_step and "file" in lower_step:
            target_path = target_root / _extract_target_path(normalized, "output.txt")
            exists = target_path.exists()
            evidence.append({"step": normalized, "status": "verified" if exists else "missing", "path": str(target_path)})
        elif "folder" in lower_step or "directory" in lower_step:
            target_path = target_root / _extract_target_path(normalized, "workspace")
            exists = target_path.exists()
            evidence.append({"step": normalized, "status": "verified" if exists else "missing", "path": str(target_path)})
        else:
            evidence.append({"step": normalized, "status": "verified", "path": str(target_root)})

    failed = [item for item in evidence if item["status"] != "verified"]
    if failed:
        return VerifyResponse(
            final_decision="FAILED",
            summary=f"Verification failed for {len(failed)} step(s).",
            evidence={"items": evidence, "target_resource": str(target_root)},
        )

    return VerifyResponse(
        final_decision="VERIFIED",
        summary="Verification completed successfully for the executed work.",
        evidence={"items": evidence, "target_resource": str(target_root)},
    )


app.add_api_route("/verify", verify_steps, methods=["POST"], response_model=VerifyResponse)
app.add_api_route("/api/v1/verify", verify_steps, methods=["POST"], response_model=VerifyResponse)


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