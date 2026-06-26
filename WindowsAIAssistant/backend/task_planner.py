"""
Task Planner
============

Architecture:
    Intent (input, a StructuredIntent from intent_parser.py)
        -> goal decomposition   (LLM: break goal into sub-goals + dependencies)
        -> task planner          (LLM: step-by-step plan per sub-goal)
        -> TaskPlan               (output)

Uses LangChain's `langchain-ollama` integration to talk to a local
Ollama server running the `llama3.2:latest` model.

Usage:
    from task_planner import TaskPlanner
    from intent_parser import IntentParser

    intent = IntentParser().parse("plan a birthday party for my friend next week")
    plan = TaskPlanner().plan(intent)
    print(plan.model_dump_json(indent=2))
"""

from __future__ import annotations

import re
from typing import List

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from schemas import (
    GoalDecomposition,
    PlanStep,
    StructuredIntent,
    SubGoal,
    SubGoalPlan,
    TaskPlan,
)


class _SubGoalSteps(PydanticOutputParser):
    """Thin alias kept for clarity at call sites; behaves like PydanticOutputParser."""


class TaskPlanner:
    """
    Runs a StructuredIntent through: goal decomposition -> per-sub-goal
    step planning, and assembles a TaskPlan.
    """

    def __init__(
        self,
        model: str = "llama3.2:latest",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.0,
    ):
        self.llm = ChatOllama(model=model, base_url=base_url, temperature=temperature)

        self._decomposition_parser = PydanticOutputParser(pydantic_object=GoalDecomposition)

        # For the per-sub-goal plan, we reuse a small inline schema via
        # a list of PlanStep wrapped in a one-off pydantic model defined
        # in schemas.py (SubGoalPlan) but only need the `steps` part here,
        # so we parse into a lightweight wrapper.
        from pydantic import BaseModel, Field

        class _StepsOnly(BaseModel):
            steps: List[PlanStep] = Field(default_factory=list)

        self._StepsOnly = _StepsOnly
        self._steps_parser = PydanticOutputParser(pydantic_object=_StepsOnly)

        self._decomposition_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a goal decomposition engine. Given a user's intent "
                    "(including its type, extracted entities, and risk level), break "
                    "the underlying goal into a small set of clear, actionable "
                    "sub-goals. For each sub-goal, give it a short id (e.g. 'sg1', "
                    "'sg2') and list the ids of any other sub-goals it depends on "
                    "(must complete first). If there are no dependencies, use an "
                    "empty list. Keep the number of sub-goals reasonable (typically 2-6).\n"
                    "Respond ONLY with JSON matching this schema, no extra text:\n"
                    "{format_instructions}",
                ),
                (
                    "human",
                    "Intent type: {intent_type}\n"
                    "Normalized request: {normalized_text}\n"
                    "Entities: {entities}\n"
                    "Risk level: {risk_level}\n",
                ),
            ]
        ).partial(format_instructions=self._decomposition_parser.get_format_instructions())

        self._steps_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a task planning engine. Given a single sub-goal, "
                    "produce a clear, ordered, step-by-step plan to accomplish it. "
                    "Each step should have a step_number starting at 1, an action "
                    "description, and optionally a tool_or_method if a specific "
                    "tool, API, or method would be used.\n"
                    "Respond ONLY with JSON matching this schema, no extra text:\n"
                    "{format_instructions}",
                ),
                (
                    "human",
                    "Overall request: {normalized_text}\n"
                    "Sub-goal to plan: {sub_goal_description}\n",
                ),
            ]
        ).partial(format_instructions=self._steps_parser.get_format_instructions())

    # -- helpers ------------------------------------------------------------

    def _invoke_structured(self, prompt: ChatPromptTemplate, parser, variables: dict):
        chain = prompt | self.llm | parser
        try:
            return chain.invoke(variables)
        except Exception:
            raw_chain = prompt | self.llm
            raw_output = raw_chain.invoke(variables)
            content = raw_output.content if hasattr(raw_output, "content") else str(raw_output)
            cleaned = self._extract_json_block(content)
            return parser.parse(cleaned)

    @staticmethod
    def _extract_json_block(content: str) -> str:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            return match.group(0)
        return content

    # -- main entry point -----------------------------------------------------

    def plan(self, intent: StructuredIntent) -> TaskPlan:
        entities_str = ", ".join(f"{e.type}={e.value}" for e in intent.entities) or "none"

        decomposition: GoalDecomposition = self._invoke_structured(
            self._decomposition_prompt,
            self._decomposition_parser,
            {
                "intent_type": intent.intent_type.value,
                "normalized_text": intent.normalized_text,
                "entities": entities_str,
                "risk_level": intent.risk_level.value,
            },
        )

        sub_goal_plans: List[SubGoalPlan] = []
        for sub_goal in decomposition.sub_goals:
            steps_result = self._invoke_structured(
                self._steps_prompt,
                self._steps_parser,
                {
                    "normalized_text": intent.normalized_text,
                    "sub_goal_description": sub_goal.description,
                },
            )
            sub_goal_plans.append(
                SubGoalPlan(
                    sub_goal_id=sub_goal.id,
                    sub_goal_description=sub_goal.description,
                    depends_on=sub_goal.depends_on,
                    steps=steps_result.steps,
                )
            )

        return TaskPlan(original_intent=intent, sub_goal_plans=sub_goal_plans)


if __name__ == "__main__":
    from intent_parser import IntentParser

    parser = IntentParser()
    planner = TaskPlanner()

    sample_text = "Plan a small birthday party for my friend next Saturday"
    intent = parser.parse(sample_text)
    task_plan = planner.plan(intent)
    print(task_plan.model_dump_json(indent=2))