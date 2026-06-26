from verification_engine.contracts import AuthorizationRecord
from verification_engine.verification._base import ComparisonOutcome, expected


class TypeInspector:
    def inspect(self, authorization: AuthorizationRecord, payload: dict) -> ComparisonOutcome:
        expected_type = expected(authorization, "declared_file_type", expected(authorization, "detected_file_type"))
        outcomes: list[ComparisonOutcome] = []
        if expected_type is not None:
            if payload.get("detected_file_type") == expected_type:
                outcomes.append(ComparisonOutcome(confirmed=("detected_file_type",), rationale=("file type matched")))
            else:
                outcomes.append(ComparisonOutcome(failed=("detected_file_type",), rationale=("file type mismatch")))
        if payload.get("type_mismatch"):
            outcomes.append(ComparisonOutcome(failed=("type_mismatch",), rationale=("declared and detected types differ")))
        if not outcomes:
            return ComparisonOutcome()
        return ComparisonOutcome(
            confirmed=tuple(item for outcome in outcomes for item in outcome.confirmed),
            failed=tuple(item for outcome in outcomes for item in outcome.failed),
            rationale=tuple(item for outcome in outcomes for item in outcome.rationale),
        )
