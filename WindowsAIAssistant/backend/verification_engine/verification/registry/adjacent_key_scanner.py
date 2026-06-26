from WindowsAIAssistant.backend.verification_engine.verification._base import ComparisonOutcome


class AdjacentKeyScanner:
    def scan(self, payload: dict) -> ComparisonOutcome:
        modified = tuple(payload.get("adjacent_key_modifications", ()))
        if not modified:
            return ComparisonOutcome(rationale=("no adjacent key modifications detected",))
        return ComparisonOutcome(
            partial=("adjacent_key_modifications",),
            rationale=(f"adjacent key modifications detected: {len(modified)}",),
        )
