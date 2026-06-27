from __future__ import annotations

from typing import List

from .schemas import SafetyAnalysisResult


class SafetyAnalysisEngine:
    def analyze(self, text: str, plan: dict) -> SafetyAnalysisResult:
        dangerous_operations: List[str] = []
        reasons: List[str] = []
        estimated_risk = "low"
        approval_required = False

        normalized = text.lower()
        if "delete" in normalized or "remove" in normalized:
            dangerous_operations.append("destructive_action")
            estimated_risk = "medium"
            approval_required = True
            reasons.append("Detected a potentially destructive operation.")

        if "install" in normalized or "download" in normalized:
            dangerous_operations.append("software_installation")
            if estimated_risk == "low":
                estimated_risk = "medium"
            reasons.append("Operation may install or download software.")

        if "registry" in normalized or "system" in normalized:
            approval_required = True
            if estimated_risk == "low":
                estimated_risk = "medium"
            reasons.append("System-level action detected.")

        if "format" in normalized or "wipe" in normalized:
            dangerous_operations.append("high_risk_action")
            estimated_risk = "high"
            approval_required = True
            reasons.append("High-risk action detected.")

        return SafetyAnalysisResult(
            estimated_risk=estimated_risk,
            approval_required=approval_required,
            dangerous_operations=dangerous_operations,
            reasons=reasons,
        )
