from verification_engine.contracts import AuthorizationRecord
from verification_engine.verification._base import (
    ComparisonOutcome,
    compare_field,
    expected,
    merge_outcomes,
    normalize_path,
)


class FilesystemAttributeComparator:
    def compare(self, authorization: AuthorizationRecord, payload: dict) -> ComparisonOutcome:
        return merge_outcomes(
            compare_field(payload, "file_path", authorization.target_resource, normalizer=normalize_path, required=True),
            compare_field(payload, "exists", expected(authorization, "exists")),
            compare_field(payload, "file_size_bytes", expected(authorization, "file_size_bytes")),
            compare_field(payload, "sha256_hash", expected(authorization, "sha256_hash")),
            compare_field(payload, "owner_sid", expected(authorization, "owner_sid")),
            compare_field(payload, "dacl_summary", expected(authorization, "dacl_summary")),
            compare_field(payload, "file_attributes", expected(authorization, "file_attributes")),
            compare_field(payload, "creation_timestamp_utc", expected(authorization, "creation_timestamp_utc")),
            compare_field(payload, "last_modified_timestamp_utc", expected(authorization, "last_modified_timestamp_utc")),
            compare_field(payload, "filename", expected(authorization, "filename")),
        )
