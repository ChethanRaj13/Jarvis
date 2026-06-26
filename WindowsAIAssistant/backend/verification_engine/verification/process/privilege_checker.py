from WindowsAIAssistant.backend.verification_engine.contracts import AuthorizationRecord
from WindowsAIAssistant.backend.verification_engine.verification._base import ComparisonOutcome, expected


class PrivilegeChecker:
    def check(self, authorization: AuthorizationRecord, payload: dict) -> ComparisonOutcome:
        authorized = expected(authorization, "integrity_level")
        if authorized is None:
            return ComparisonOutcome()
        observed = payload.get("integrity_level")
        if observed == authorized:
            return ComparisonOutcome(confirmed=("integrity_level",), rationale=("integrity level matched",))
        return ComparisonOutcome(failed=("integrity_level",), rationale=("integrity level mismatch",))
