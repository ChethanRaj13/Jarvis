from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class TaskProcessRequest(BaseModel):
    text: str
    session_id: str = Field(default="default-session")
    session_context: Optional[str] = Field(default=None)
    memory_summaries: List[str] = Field(default_factory=list)
    include_verification: bool = Field(default=False)


class TaskProcessResponse(BaseModel):
    intent: dict
    plan: dict
    safety: dict


class VerificationPlanRequest(BaseModel):
    plan: dict
    task_description: Optional[str] = Field(default=None)


class VerificationStep(BaseModel):
    step_number: int
    description: str
    target: Optional[str] = Field(default=None)
    verification_type: Optional[str] = Field(default=None)


class VerificationPlan(BaseModel):
    plan_id: str
    steps: List[VerificationStep] = Field(default_factory=list)


class VerificationPlanResponse(BaseModel):
    verification_plan: VerificationPlan


class MemorySummarizeRequest(BaseModel):
    documents: List[str] = Field(default_factory=list)


class MemorySummarizeResponse(BaseModel):
    summary: str


class ChatRespondRequest(BaseModel):
    message: str
    session_id: str = Field(default="default-session")
    session_context: Optional[str] = Field(default=None)
    memory_summaries: List[str] = Field(default_factory=list)


class ChatRespondResponse(BaseModel):
    response: str
    metadata: Optional[dict] = Field(default_factory=dict)


class SafetyAnalysisResult(BaseModel):
    estimated_risk: str
    approval_required: bool
    dangerous_operations: List[str] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)
