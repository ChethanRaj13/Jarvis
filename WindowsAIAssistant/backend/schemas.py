"""
Shared Pydantic schemas for the Intent Parser -> Task Planner pipeline.

Keeping these in one place means both modules speak the exact same
"contract": the StructuredIntent object produced by intent_parser.py
is the only thing task_planner.py needs to accept as input.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Intent Parser schemas
# ---------------------------------------------------------------------------

class IntentType(str, Enum):
    COMMAND = "command"
    QUERY = "query"
    CHAT = "chat"
    UNKNOWN = "unknown"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Entity(BaseModel):
    """A single extracted entity, e.g. a tool name, a date, a file path."""

    type: str = Field(..., description="Entity category, e.g. 'tool', 'date', 'time', 'file', 'person'")
    value: str = Field(..., description="The literal extracted value")


class IntentClassification(BaseModel):
    """Raw output of the intent-classifier LLM call."""

    intent_type: IntentType
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str = Field(default="", description="Short justification from the LLM")


class EntityExtraction(BaseModel):
    """Raw output of the entity-extractor LLM call."""

    entities: List[Entity] = Field(default_factory=list)


class RiskAssessment(BaseModel):
    """Raw output of the risk-detection LLM call."""

    risk_level: RiskLevel
    risk_reasons: List[str] = Field(default_factory=list)


class StructuredIntent(BaseModel):
    """
    Final output of the Intent Parser pipeline.
    This is the single object handed off to the Task Planner.
    """

    raw_text: str
    normalized_text: str
    intent_type: IntentType
    confidence: float = Field(..., ge=0.0, le=1.0)
    entities: List[Entity] = Field(default_factory=list)
    risk_level: RiskLevel
    risk_reasons: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Task Planner schemas
# ---------------------------------------------------------------------------

class SubGoal(BaseModel):
    """A single decomposed sub-goal with its dependency info."""

    id: str = Field(..., description="Short unique id, e.g. 'sg1'")
    description: str
    depends_on: List[str] = Field(
        default_factory=list,
        description="ids of other sub-goals that must complete before this one",
    )


class GoalDecomposition(BaseModel):
    """Raw output of the goal-decomposition LLM call."""

    sub_goals: List[SubGoal] = Field(default_factory=list)


class PlanStep(BaseModel):
    """A single actionable step within a sub-goal's plan."""

    step_number: int
    action: str
    tool_or_method: Optional[str] = Field(
        default=None, description="Tool, API, or method to use for this step, if any"
    )


class SubGoalPlan(BaseModel):
    """The step-by-step plan generated for one sub-goal."""

    sub_goal_id: str
    sub_goal_description: str
    depends_on: List[str] = Field(default_factory=list)
    steps: List[PlanStep] = Field(default_factory=list)


class TaskPlan(BaseModel):
    """
    Final output of the Task Planner.
    Contains the full decomposition plus a step-by-step plan per sub-goal.
    """

    original_intent: StructuredIntent
    sub_goal_plans: List[SubGoalPlan] = Field(default_factory=list)