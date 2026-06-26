from verification_engine.verification._base import ComparisonOutcome


class SafetyConfigGuard:
    def check(self, payload: dict) -> ComparisonOutcome:
        if payload.get("is_safety_engine_config") and payload.get("unauthorized_changes"):
            return ComparisonOutcome(
                failed=("safety_engine_config_modified",),
                rationale=("Safety Engine configuration was modified outside authorization"),
            )
        return ComparisonOutcome(rationale=("Safety Engine configuration guard passed",))
