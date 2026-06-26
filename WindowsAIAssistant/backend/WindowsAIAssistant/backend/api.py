from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from WindowsAIAssistant.backend.WindowsAIAssistant.backend.intent_parser import IntentParser
from WindowsAIAssistant.backend.WindowsAIAssistant.backend.task_planner import TaskPlanner

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


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/parse")
def parse_text(request: ParseRequest) -> dict:
    """
    Runs raw text through IntentParser only. Kept around for cases where you
    just want the structured intent without a full plan (e.g. quick UI
    feedback, debugging, or a lighter-weight call).
    """
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
    """
    Full pipeline: text -> IntentParser -> StructuredIntent -> TaskPlanner ->
    TaskPlan. Returns both the intent and the plan so the UI can render either
    or both without a second round trip.
    """
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)