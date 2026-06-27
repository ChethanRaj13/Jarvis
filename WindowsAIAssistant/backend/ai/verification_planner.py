from __future__ import annotations

import json
import re
from typing import Any

from .schemas import VerificationPlan, VerificationStep


class VerificationPlanner:
    def build_plan(self, plan: dict, task_description: str | None = None) -> VerificationPlan:
        raw_steps = self._extract_steps(plan)
        verification_steps = []

        for index, step in enumerate(raw_steps, start=1):
            verification_steps.append(
                VerificationStep(
                    step_number=index,
                    description=self._build_description(step),
                    target=self._detect_target(step),
                    verification_type=self._detect_verification_type(step),
                )
            )

        return VerificationPlan(plan_id=self._build_plan_id(task_description), steps=verification_steps)

    @staticmethod
    def _extract_steps(plan: dict) -> list[dict[str, Any]]:
        if not isinstance(plan, dict):
            return []

        sub_goals = plan.get("sub_goal_plans") or []
        steps = []
        for sub_goal in sub_goals:
            for step in sub_goal.get("steps", []):
                steps.append(step)
        return steps

    @staticmethod
    def _build_description(step: dict[str, Any]) -> str:
        action = step.get("action") or step.get("description") or "Verify step"
        return f"Verify that the following action can complete successfully: {action}"

    @staticmethod
    def _detect_target(step: dict[str, Any]) -> str | None:
        return step.get("tool_or_method") or step.get("target")

    @staticmethod
    def _detect_verification_type(step: dict[str, Any]) -> str:
        description = (step.get("action") or "").lower()
        if "install" in description or "download" in description:
            return "software_installation"
        if "registry" in description:
            return "registry_modification"
        if "path" in description or "executable" in description:
            return "path_check"
        return "generic_check"

    @staticmethod
    def _build_plan_id(task_description: str | None) -> str:
        if task_description:
            normalized = re.sub(r"\W+", "-", task_description.lower()).strip("-")
            return f"verification-{normalized}"[:64]
        return "verification-plan"
