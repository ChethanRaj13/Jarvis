from verification_engine.contracts import AuthorizationRecord
from verification_engine.verification._base import ComparisonOutcome, expected


class BaselineComparator:
    def compare(self, authorization: AuthorizationRecord, payload: dict) -> ComparisonOutcome:
        expected_values = expected(authorization, "expected_values", {})
        if not expected_values:
            return ComparisonOutcome(escalations=("expected_values",), rationale=("expected configuration values are absent"))
        observed = payload.get("all_key_value_pairs", {})
        confirmed = []
        failed = []
        rationale = []
        for key, expected_value in expected_values.items():
            if observed.get(key) == expected_value:
                confirmed.append(f"config:{key}")
                rationale.append(f"configuration value matched: {key}")
            else:
                failed.append(f"config:{key}")
                rationale.append(f"configuration value mismatch: {key}")
        unauthorized = tuple(payload.get("unauthorized_changes", ()))
        partial = ("unauthorized_configuration_drift",) if unauthorized else ()
        if unauthorized:
            rationale.append("unauthorized configuration drift detected")
        return ComparisonOutcome(tuple(confirmed), tuple(failed), partial, (), tuple(rationale))
