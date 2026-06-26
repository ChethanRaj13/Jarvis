from verification_engine.contracts import AuthorizationRecord
from verification_engine.verification._base import ComparisonOutcome, expected


class ChildProcessScanner:
    def scan(self, authorization: AuthorizationRecord, payload: dict) -> ComparisonOutcome:
        children = tuple(payload.get("child_processes", ()))
        allowed = tuple(expected(authorization, "allowed_child_processes", ()))
        if not children or len(children) <= len(allowed):
            return ComparisonOutcome(rationale=("no unexpected child processes detected",))
        return ComparisonOutcome(
            partial=("child_processes",),
            rationale=("unexpected child processes detected",),
        )
