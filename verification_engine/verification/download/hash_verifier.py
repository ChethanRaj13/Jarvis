from verification_engine.contracts import AuthorizationRecord
from verification_engine.verification._base import ComparisonOutcome, expected


class HashVerifier:
    def verify(self, authorization: AuthorizationRecord, payload: dict) -> ComparisonOutcome:
        expected_hash = expected(authorization, "sha256_hash", expected(authorization, "expected_hash"))
        if expected_hash is None:
            return ComparisonOutcome(escalations=("sha256_hash",), rationale=("expected hash is absent"))
        if payload.get("sha256_hash") == expected_hash:
            return ComparisonOutcome(confirmed=("sha256_hash",), rationale=("hash matched"))
        return ComparisonOutcome(failed=("sha256_hash",), rationale=("hash mismatch"))
