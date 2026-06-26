from verification_engine.verification._base import ComparisonOutcome


class PersistenceDetector:
    def detect(self, payload: dict) -> ComparisonOutcome:
        persistence = tuple(payload.get("unauthorized_persistence_entries", ()))
        if persistence:
            return ComparisonOutcome(
                failed=("unauthorized_persistence_entries",),
                rationale=("unauthorized persistence entries detected",),
            )
        adjacent = tuple(payload.get("adjacent_tasks_created", ()))
        if adjacent:
            return ComparisonOutcome(
                partial=("adjacent_tasks_created",),
                rationale=("adjacent scheduled tasks detected",),
            )
        return ComparisonOutcome(rationale=("no unauthorized persistence detected",))
