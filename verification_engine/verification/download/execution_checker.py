from verification_engine.verification._base import ComparisonOutcome


class ExecutionChecker:
    def check(self, payload: dict) -> ComparisonOutcome:
        if payload.get("has_been_executed"):
            return ComparisonOutcome(failed=("has_been_executed",), rationale=("downloaded file was executed"))
        return ComparisonOutcome(confirmed=("has_been_executed",), rationale=("downloaded file was not executed"))
