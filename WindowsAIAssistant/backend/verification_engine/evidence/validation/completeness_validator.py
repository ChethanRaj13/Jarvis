from WindowsAIAssistant.backend.verification_engine.contracts import EvidencePackage, EvidenceType

from ._base import BaseValidator, ValidationContext, ValidationResult
from .exceptions import CompletenessValidationError


DEFAULT_REQUIRED_FIELDS: dict[EvidenceType, tuple[str, ...]] = {
    EvidenceType.FILESYSTEM: (
        "file_path",
        "exists",
        "file_size_bytes",
        "sha256_hash",
        "creation_timestamp_utc",
        "last_modified_timestamp_utc",
        "file_attributes",
        "owner_sid",
        "dacl_summary",
    ),
    EvidenceType.REGISTRY: (
        "key_path",
        "key_exists",
        "value_name",
        "value_type",
        "value_data",
        "key_last_written_timestamp",
        "subkey_names",
        "parent_key_last_written_timestamp",
        "is_in_protected_hive",
    ),
    EvidenceType.PROCESS: (
        "process_id",
        "process_name",
        "executable_path",
        "command_line_parameters",
        "parent_process_id",
        "session_id",
        "integrity_level",
        "token_elevation_type",
        "process_creation_timestamp",
        "child_processes",
        "process_exists",
    ),
    EvidenceType.TASK: (
        "task_name",
        "task_exists",
        "executable_path",
        "arguments",
        "working_directory",
        "run_as_user",
        "highest_run_level",
        "triggers",
        "task_state",
        "creation_date",
        "last_run_time",
        "adjacent_tasks",
    ),
    EvidenceType.DOWNLOAD: (
        "file_path",
        "file_exists",
        "sha256_hash",
        "file_size_bytes",
        "detected_file_type",
        "declared_file_type",
        "type_mismatch",
        "has_been_executed",
        "additional_write_paths",
    ),
    EvidenceType.CONFIGURATION: (
        "config_source_type",
        "config_path",
        "config_format",
        "all_key_value_pairs",
        "last_modified_timestamp",
        "is_safety_engine_config",
        "is_policy_enforcement_config",
    ),
}


class CompletenessValidator(BaseValidator):
    name = "completeness"
    exception_type = CompletenessValidationError

    def _execute(self, evidence: EvidencePackage, context: ValidationContext) -> ValidationResult:
        required_fields = self._required_fields(evidence, context)
        missing = tuple(
            field_name
            for field_name in required_fields
            if field_name not in evidence.evidence_payload or evidence.evidence_payload[field_name] is None
        )
        return ValidationResult(
            validator_name=self.name,
            passed=not missing,
            reason=None if not missing else "evidence payload is incomplete",
            details={"missing_fields": missing},
        )

    def _required_fields(
        self,
        evidence: EvidencePackage,
        context: ValidationContext,
    ) -> tuple[str, ...]:
        override = context.required_fields.get(evidence.evidence_type.value)
        if override is not None:
            return override
        return DEFAULT_REQUIRED_FIELDS[evidence.evidence_type]
