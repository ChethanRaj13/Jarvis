from verification_engine.contracts import AuthorizationRecord
from verification_engine.verification._base import ComparisonOutcome, expected


class TriggerComparator:
    def compare(self, authorization: AuthorizationRecord, payload: dict) -> ComparisonOutcome:
        authorized = expected(authorization, "triggers")
        if authorized is None:
            return ComparisonOutcome()
        if payload.get("triggers") == authorized:
            return ComparisonOutcome(confirmed=("triggers",), rationale=("task triggers matched"))
        return ComparisonOutcome(failed=("triggers",), rationale=("task triggers mismatch"))
