from verification_engine.contracts import AuthorizationRecord
from verification_engine.verification._base import ComparisonOutcome, expected


class RegistryHiveProtector:
    def check(self, authorization: AuthorizationRecord, payload: dict) -> ComparisonOutcome:
        if not payload.get("is_in_protected_hive"):
            return ComparisonOutcome(rationale=("registry key is not in protected hive",))
        if expected(authorization, "allow_protected_hive", False):
            return ComparisonOutcome(confirmed=("protected_hive_authorized",), rationale=("protected hive access authorized",))
        return ComparisonOutcome(failed=("protected_hive",), rationale=("protected hive access is not authorized",))
