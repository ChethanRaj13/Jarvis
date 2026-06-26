from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .enums import (
    ActionType,
    ChainIntegrityStatus,
    EvidenceResolutionStatus,
    EvidenceType,
    ReviewDecision,
    RiskLevel,
    SideEffectSeverity,
    SideEffectSurface,
    ValidationStatus,
    VerificationDecisionEnum,
    VerifierID,
)


HexDigest = str
NonEmptyString = str


class ImmutableContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


def _is_utc(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() == timezone.utc.utcoffset(value)


class ExecutionCompletionSignal(ImmutableContract):
    request_id: UUID = Field(description="Verification request identifier from the Execution Layer.")
    action_type: ActionType = Field(description="Authorized action type that completed execution.")
    execution_timestamp: datetime = Field(description="UTC timestamp for execution completion.")
    execution_layer_id: NonEmptyString = Field(min_length=1, description="Identifier of the sending Execution Layer component.")
    action_subtype: str | None = Field(default=None, description="Optional subtype for bulk or recursive operations.")

    @field_validator("execution_timestamp")
    @classmethod
    def execution_timestamp_must_be_utc(cls, value: datetime) -> datetime:
        if not _is_utc(value):
            raise ValueError("execution_timestamp must be UTC")
        return value


class VerificationRequest(ImmutableContract):
    request_id: UUID = Field(description="Verification request identifier.")
    action_type: ActionType = Field(description="Action type under verification.")
    execution_timestamp: datetime = Field(description="UTC execution completion timestamp.")
    trigger_received_timestamp: datetime = Field(description="UTC timestamp when the trigger was received.")
    session_id: NonEmptyString = Field(min_length=1, description="Active verification session identifier.")
    execution_layer_id: str | None = Field(default=None, description="Optional Execution Layer component identifier.")
    action_subtype: str | None = Field(default=None, description="Optional subtype for bulk or recursive operations.")

    @field_validator("execution_timestamp", "trigger_received_timestamp")
    @classmethod
    def timestamps_must_be_utc(cls, value: datetime) -> datetime:
        if not _is_utc(value):
            raise ValueError("timestamps must be UTC")
        return value

    @model_validator(mode="after")
    def trigger_must_not_precede_execution(self) -> "VerificationRequest":
        if self.trigger_received_timestamp < self.execution_timestamp:
            raise ValueError("trigger_received_timestamp must be greater than or equal to execution_timestamp")
        return self


class AuthorizationRecord(ImmutableContract):
    authorization_id: NonEmptyString = Field(min_length=1, description="Safety Engine authorization record identifier.")
    request_id: UUID = Field(description="Verification request identifier matched to the authorization.")
    action_type: ActionType = Field(description="Authorized action type.")
    target_resource: NonEmptyString = Field(min_length=1, description="Authorized target resource.")
    authorized_scope: dict[str, Any] = Field(min_length=1, description="Complete authorized attribute scope.")
    risk_level: RiskLevel = Field(description="Safety Engine risk level for the authorized action.")
    authorization_timestamp: datetime = Field(description="UTC timestamp of Safety Engine authorization.")
    expected_outcome_specification: dict[str, Any] = Field(min_length=1, description="Expected outcome specification from authorization.")
    explicit_verification_requirements: list[str] | None = Field(default=None, description="Optional explicit verification requirements.")
    tool_ids_used: list[str] | None = Field(default=None, description="Optional Safety Engine tool identifiers used for authorization.")
    session_id: str | None = Field(default=None, description="Optional session identifier.")

    @field_validator("authorization_timestamp")
    @classmethod
    def authorization_timestamp_must_be_utc(cls, value: datetime) -> datetime:
        if not _is_utc(value):
            raise ValueError("authorization_timestamp must be UTC")
        return value


class AuthorizationRetrievalRequest(ImmutableContract):
    request_id: UUID = Field(description="Request identifier whose authorization record should be retrieved.")
    requester_id: NonEmptyString = Field(min_length=1, description="Verification Engine component requesting authorization.")
    retrieval_timestamp: datetime | None = Field(default=None, description="Optional UTC retrieval timestamp.")

    @field_validator("retrieval_timestamp")
    @classmethod
    def retrieval_timestamp_must_be_utc(cls, value: datetime | None) -> datetime | None:
        if value is not None and not _is_utc(value):
            raise ValueError("retrieval_timestamp must be UTC")
        return value


class EvidencePackage(ImmutableContract):
    evidence_id: UUID = Field(description="Globally unique evidence package identifier.")
    request_id: UUID = Field(description="Verification request identifier.")
    evidence_type: EvidenceType = Field(description="Evidence domain type.")
    collection_timestamp: datetime = Field(description="UTC evidence collection timestamp.")
    collection_window_open: bool = Field(description="Whether the evidence collection window was open.")
    binding_token: NonEmptyString = Field(min_length=1, description="Binding token for request, timestamp, and evidence type.")
    collector_id: NonEmptyString = Field(min_length=1, description="Evidence collector identifier.")
    evidence_payload: dict[str, Any] = Field(description="Typed evidence payload content.")
    pre_execution_baseline_id: UUID | None = Field(default=None, description="Optional baseline evidence identifier.")
    collection_duration_ms: int | None = Field(default=None, ge=0, description="Optional non-negative collection duration in milliseconds.")

    @field_validator("collection_timestamp")
    @classmethod
    def collection_timestamp_must_be_utc(cls, value: datetime) -> datetime:
        if not _is_utc(value):
            raise ValueError("collection_timestamp must be UTC")
        return value


class EvidenceMetadata(ImmutableContract):
    evidence_id: UUID = Field(description="Evidence package identifier.")
    request_id: UUID = Field(description="Verification request identifier.")
    collection_timestamp: datetime = Field(description="UTC evidence collection timestamp.")
    evidence_window_seconds: int = Field(gt=0, description="Configured evidence window in seconds.")
    time_since_execution_ms: int = Field(ge=0, description="Elapsed milliseconds from execution to collection.")
    within_window: bool = Field(description="Whether collection occurred within the permitted window.")
    binding_token: NonEmptyString = Field(min_length=1, description="Evidence binding token.")
    evidence_type: EvidenceType = Field(description="Evidence domain type.")
    collection_api: NonEmptyString = Field(min_length=1, description="Collection API or mechanism used.")
    validation_status: ValidationStatus = Field(description="Evidence validation lifecycle status.")
    validation_timestamp: datetime = Field(description="UTC validation timestamp.")
    rejection_reason: str | None = Field(default=None, description="Reason for invalid evidence.")
    replay_check_timestamp: datetime | None = Field(default=None, description="Optional UTC replay check timestamp.")
    integrity_hash: HexDigest | None = Field(default=None, pattern=r"^[0-9a-fA-F]{64}$", description="Optional SHA-256 integrity hash.")

    @field_validator("collection_timestamp", "validation_timestamp", "replay_check_timestamp")
    @classmethod
    def evidence_metadata_timestamps_must_be_utc(cls, value: datetime | None) -> datetime | None:
        if value is not None and not _is_utc(value):
            raise ValueError("evidence metadata timestamps must be UTC")
        return value

    @model_validator(mode="after")
    def invalid_status_requires_rejection_reason(self) -> "EvidenceMetadata":
        if self.validation_status == ValidationStatus.INVALID and not self.rejection_reason:
            raise ValueError("rejection_reason is required when validation_status is INVALID")
        return self


class FilesystemEvidence(ImmutableContract):
    file_path: NonEmptyString = Field(min_length=1, description="Canonical filesystem path.")
    exists: bool = Field(description="Whether the file exists.")
    file_size_bytes: int = Field(ge=0, description="File size in bytes.")
    sha256_hash: HexDigest = Field(pattern=r"^[0-9a-fA-F]{64}$", description="SHA-256 content hash.")
    creation_timestamp_utc: datetime = Field(description="UTC creation timestamp.")
    last_modified_timestamp_utc: datetime = Field(description="UTC last modified timestamp.")
    file_attributes: dict[str, Any] = Field(description="Collected filesystem attributes.")
    owner_sid: NonEmptyString = Field(min_length=1, description="Owner security identifier.")
    dacl_summary: dict[str, Any] = Field(description="Discretionary ACL summary.")
    is_in_recycle_bin: bool | None = Field(default=None, description="Whether the file is in the recycle bin.")
    shadow_copy_exists: bool | None = Field(default=None, description="Whether a shadow copy exists.")
    directory_listing: list[str] | None = Field(default=None, description="Containing directory listing for side-effect detection.")

    @field_validator("creation_timestamp_utc", "last_modified_timestamp_utc")
    @classmethod
    def filesystem_timestamps_must_be_utc(cls, value: datetime) -> datetime:
        if not _is_utc(value):
            raise ValueError("filesystem timestamps must be UTC")
        return value


class RegistryEvidence(ImmutableContract):
    key_path: NonEmptyString = Field(min_length=1, description="Canonical registry key path with hive prefix.")
    key_exists: bool = Field(description="Whether the registry key exists.")
    value_name: NonEmptyString = Field(min_length=1, description="Registry value name.")
    value_type: NonEmptyString = Field(min_length=1, pattern=r"^REG_", description="Registry value type.")
    value_data: Any = Field(description="Registry value data.")
    key_last_written_timestamp: datetime = Field(description="UTC key last-write timestamp.")
    subkey_names: list[str] = Field(description="Enumerated subkey names.")
    parent_key_last_written_timestamp: datetime = Field(description="UTC parent key last-write timestamp.")
    is_in_protected_hive: bool = Field(description="Whether the key is in a protected hive.")
    sibling_key_last_modified_timestamps: dict[str, datetime] | None = Field(default=None, description="Optional sibling key timestamps.")

    @field_validator("key_last_written_timestamp", "parent_key_last_written_timestamp")
    @classmethod
    def registry_timestamps_must_be_utc(cls, value: datetime) -> datetime:
        if not _is_utc(value):
            raise ValueError("registry timestamps must be UTC")
        return value

    @field_validator("key_path")
    @classmethod
    def key_path_must_include_hive(cls, value: str) -> str:
        if not (value.startswith("HKLM\\") or value.startswith("HKCU\\")):
            raise ValueError("key_path must include HKLM or HKCU hive prefix")
        return value


class ProcessEvidence(ImmutableContract):
    process_id: int = Field(ge=0, description="Process identifier.")
    process_name: NonEmptyString = Field(min_length=1, description="Process image name.")
    executable_path: NonEmptyString = Field(min_length=1, description="Canonical executable path.")
    command_line_parameters: list[str] = Field(description="Command-line parameters.")
    parent_process_id: int = Field(ge=0, description="Parent process identifier.")
    session_id: NonEmptyString = Field(min_length=1, description="OS session identifier.")
    integrity_level: NonEmptyString = Field(pattern=r"^(Low|Medium|High|System)$", description="Observed process integrity level.")
    token_elevation_type: NonEmptyString = Field(min_length=1, description="Token elevation type.")
    process_creation_timestamp: datetime = Field(description="UTC process creation timestamp.")
    child_processes: list[dict[str, Any]] = Field(description="Recursive child process observations.")
    process_exists: bool = Field(description="Whether the process exists.")
    open_handles_summary: dict[str, Any] | None = Field(default=None, description="Optional open handle summary.")

    @field_validator("process_creation_timestamp")
    @classmethod
    def process_timestamp_must_be_utc(cls, value: datetime) -> datetime:
        if not _is_utc(value):
            raise ValueError("process_creation_timestamp must be UTC")
        return value


class TaskEvidence(ImmutableContract):
    task_name: NonEmptyString = Field(min_length=1, description="Full scheduled task path with folder.")
    task_exists: bool = Field(description="Whether the scheduled task exists.")
    executable_path: NonEmptyString = Field(min_length=1, description="Task executable path.")
    arguments: list[str] = Field(description="Task arguments.")
    working_directory: NonEmptyString = Field(min_length=1, description="Task working directory.")
    run_as_user: NonEmptyString = Field(min_length=1, description="Run-as user.")
    highest_run_level: bool = Field(description="Whether highest run level is enabled.")
    triggers: list[dict[str, Any]] = Field(min_length=1, description="Complete trigger specifications.")
    task_state: NonEmptyString = Field(min_length=1, description="Task state.")
    creation_date: datetime = Field(description="UTC task creation date.")
    last_run_time: datetime = Field(description="UTC last run time.")
    adjacent_tasks: list[str] = Field(description="Tasks in the same folder.")
    task_xml: str | None = Field(default=None, description="Optional full task XML definition.")

    @field_validator("creation_date", "last_run_time")
    @classmethod
    def task_timestamps_must_be_utc(cls, value: datetime) -> datetime:
        if not _is_utc(value):
            raise ValueError("task timestamps must be UTC")
        return value

    @field_validator("task_name")
    @classmethod
    def task_name_must_include_folder(cls, value: str) -> str:
        if "\\" not in value:
            raise ValueError("task_name must include folder path")
        return value


class DownloadEvidence(ImmutableContract):
    file_path: NonEmptyString = Field(min_length=1, description="Downloaded file destination path.")
    file_exists: bool = Field(description="Whether the downloaded file exists.")
    sha256_hash: HexDigest = Field(pattern=r"^[0-9a-fA-F]{64}$", description="SHA-256 content hash.")
    file_size_bytes: int = Field(ge=0, description="File size in bytes.")
    detected_file_type: NonEmptyString = Field(min_length=1, description="Content-derived file type.")
    declared_file_type: NonEmptyString = Field(min_length=1, description="Authorized declared file type.")
    type_mismatch: bool = Field(description="Whether detected and declared types differ.")
    has_been_executed: bool = Field(description="Whether the file executed during the evidence window.")
    additional_write_paths: list[str] = Field(description="Additional paths where file content was written.")
    execution_flag_in_filesystem: bool | None = Field(default=None, description="Optional filesystem execution marker.")


class ConfigurationSnapshot(ImmutableContract):
    config_source_type: NonEmptyString = Field(pattern=r"^(FILE|REGISTRY)$", description="Configuration source type.")
    config_path: NonEmptyString = Field(min_length=1, description="Configuration path.")
    config_format: NonEmptyString = Field(min_length=1, description="Parseable configuration format.")
    all_key_value_pairs: dict[str, Any] = Field(description="Collected configuration key/value pairs.")
    last_modified_timestamp: datetime = Field(description="UTC last modified timestamp.")
    is_safety_engine_config: bool = Field(description="Whether this is Safety Engine configuration.")
    is_policy_enforcement_config: bool = Field(description="Whether this is policy enforcement configuration.")
    file_hash: HexDigest | None = Field(default=None, pattern=r"^[0-9a-fA-F]{64}$", description="Optional file hash for file-based configuration.")
    parsed_at_timestamp: datetime | None = Field(default=None, description="Optional UTC parse timestamp.")

    @field_validator("last_modified_timestamp", "parsed_at_timestamp")
    @classmethod
    def config_timestamps_must_be_utc(cls, value: datetime | None) -> datetime | None:
        if value is not None and not _is_utc(value):
            raise ValueError("configuration timestamps must be UTC")
        return value


class VerificationResult(ImmutableContract):
    result_id: UUID = Field(description="Verification result identifier.")
    request_id: UUID = Field(description="Verification request identifier.")
    verifier_id: VerifierID = Field(description="Verifier that produced the result.")
    sub_decision: VerificationDecisionEnum = Field(description="Per-verifier decision.")
    confirmed_attributes: list[str] = Field(description="Attributes confirmed by the verifier.")
    failed_attributes: list[str] = Field(description="Attributes failed by the verifier.")
    evidence_reference: UUID = Field(description="Referenced evidence identifier.")
    sub_decision_rationale: NonEmptyString = Field(min_length=1, description="Human-readable sub-decision rationale.")
    result_timestamp: datetime = Field(description="UTC result timestamp.")
    detected_side_effects: list[dict[str, Any]] | None = Field(default=None, description="Optional detected side effects.")
    drift_findings: list[dict[str, Any]] | None = Field(default=None, description="Optional drift findings.")
    controlling_attribute: str | None = Field(default=None, description="Optional controlling attribute.")

    @field_validator("result_timestamp")
    @classmethod
    def result_timestamp_must_be_utc(cls, value: datetime) -> datetime:
        if not _is_utc(value):
            raise ValueError("result_timestamp must be UTC")
        return value

    @model_validator(mode="after")
    def attribute_lists_must_match_decision(self) -> "VerificationResult":
        if self.sub_decision == VerificationDecisionEnum.VERIFIED and self.failed_attributes:
            raise ValueError("VERIFIED results require failed_attributes to be empty")
        if self.sub_decision == VerificationDecisionEnum.FAILED and not self.failed_attributes:
            raise ValueError("FAILED results require at least one failed attribute")
        if self.sub_decision != VerificationDecisionEnum.ESCALATE and not (self.confirmed_attributes or self.failed_attributes):
            raise ValueError("non-ESCALATE results require confirmed or failed attributes")
        return self


class VerificationDecision(ImmutableContract):
    decision_id: UUID = Field(description="Final decision identifier.")
    request_id: UUID = Field(description="Verification request identifier.")
    final_decision: VerificationDecisionEnum = Field(description="Final aggregated decision.")
    controlling_results: list[UUID] = Field(min_length=1, description="Result identifiers that controlled the decision.")
    full_rationale: NonEmptyString = Field(min_length=1, description="Full final decision rationale.")
    all_results: list[UUID] = Field(min_length=1, description="All result identifiers considered.")
    decision_timestamp: datetime = Field(description="UTC decision timestamp.")
    decision_engine_version: NonEmptyString = Field(min_length=1, description="Decision engine version.")
    escalation_expiry: datetime | None = Field(default=None, description="Required UTC expiry timestamp for ESCALATE decisions.")
    partial_scope_description: str | None = Field(default=None, description="Scope description for PARTIAL decisions.")

    @field_validator("decision_timestamp", "escalation_expiry")
    @classmethod
    def decision_timestamps_must_be_utc(cls, value: datetime | None) -> datetime | None:
        if value is not None and not _is_utc(value):
            raise ValueError("decision timestamps must be UTC")
        return value

    @model_validator(mode="after")
    def decision_references_must_be_consistent(self) -> "VerificationDecision":
        if not set(self.controlling_results).issubset(set(self.all_results)):
            raise ValueError("controlling_results must be a subset of all_results")
        if self.final_decision == VerificationDecisionEnum.ESCALATE and self.escalation_expiry is None:
            raise ValueError("escalation_expiry is required for ESCALATE decisions")
        return self


class SideEffectChange(ImmutableContract):
    path_or_key: NonEmptyString = Field(min_length=1, description="Affected path or registry key.")
    change_type: NonEmptyString = Field(min_length=1, description="Observed change type.")
    surface: SideEffectSurface = Field(description="Affected side-effect surface.")


class UnauthorizedSideEffectChange(SideEffectChange):
    severity: SideEffectSeverity = Field(description="Severity of the unauthorized change.")


class SideEffectReport(ImmutableContract):
    report_id: UUID = Field(description="Side-effect report identifier.")
    request_id: UUID = Field(description="Verification request identifier.")
    detection_scope: NonEmptyString = Field(min_length=1, description="Scope inspected for side effects.")
    authorized_changes: list[SideEffectChange] = Field(description="Authorized changes observed.")
    unauthorized_changes: list[UnauthorizedSideEffectChange] = Field(description="Unauthorized changes observed.")
    side_effect_sub_decision: VerificationDecisionEnum = Field(description="Side-effect sub-decision.")
    detection_timestamp: datetime = Field(description="UTC side-effect detection timestamp.")
    tool_registry_informed_scope: bool | None = Field(default=None, description="Whether scope was informed by tool registry.")
    scope_expansion_reason: str | None = Field(default=None, description="Optional reason detection scope expanded.")

    @field_validator("detection_timestamp")
    @classmethod
    def side_effect_timestamp_must_be_utc(cls, value: datetime) -> datetime:
        if not _is_utc(value):
            raise ValueError("detection_timestamp must be UTC")
        return value


class DriftAttributionFinding(ImmutableContract):
    change_description: NonEmptyString = Field(min_length=1, description="Observed change description.")
    attributed_to_request_id: UUID | None = Field(default=None, description="Request attributed to this change; absent means unattributed.")
    affected_asset: NonEmptyString = Field(min_length=1, description="Affected asset.")
    severity: SideEffectSeverity = Field(description="Severity of the finding.")


class DriftFinding(ImmutableContract):
    expected_attribute: NonEmptyString = Field(min_length=1, description="Expected attribute.")
    observed_attribute: NonEmptyString = Field(min_length=1, description="Observed attribute.")
    delta_description: NonEmptyString = Field(min_length=1, description="Delta between expected and observed values.")


class DriftReport(ImmutableContract):
    report_id: UUID = Field(description="Drift report identifier.")
    session_id: NonEmptyString = Field(min_length=1, description="Verification session identifier.")
    request_id: UUID = Field(description="Verification request identifier.")
    attribution_findings: list[DriftAttributionFinding] = Field(description="Authorization-to-outcome attribution findings.")
    drift_findings: list[DriftFinding] = Field(description="Observed drift findings.")
    drift_sub_decision: VerificationDecisionEnum = Field(description="Drift sub-decision.")
    detection_timestamp: datetime = Field(description="UTC drift detection timestamp.")
    session_boundary_verified: bool | None = Field(default=None, description="Whether the session boundary was verified.")
    cumulative_unattributed_count: int | None = Field(default=None, ge=0, description="Optional cumulative count of unattributed findings.")

    @field_validator("detection_timestamp")
    @classmethod
    def drift_timestamp_must_be_utc(cls, value: datetime) -> datetime:
        if not _is_utc(value):
            raise ValueError("detection_timestamp must be UTC")
        return value


class EvidenceReference(ImmutableContract):
    evidence_id: UUID = Field(description="Referenced evidence package identifier.")
    evidence_type: EvidenceType = Field(description="Evidence domain type.")
    collection_timestamp: datetime = Field(description="UTC evidence collection timestamp.")
    within_window: bool = Field(description="Whether collection occurred within the permitted window.")
    binding_token_valid: bool = Field(description="Whether the binding token was valid.")
    resolution_status: EvidenceResolutionStatus | None = Field(default=None, description="Evidence store resolution status.")

    @field_validator("collection_timestamp")
    @classmethod
    def evidence_reference_timestamp_must_be_utc(cls, value: datetime) -> datetime:
        if not _is_utc(value):
            raise ValueError("collection_timestamp must be UTC")
        return value


class VerificationRecord(ImmutableContract):
    record_id: UUID = Field(description="Audit record identifier assigned by the Audit Service.")
    request_id: UUID = Field(description="Verification request identifier.")
    authorization_reference: NonEmptyString = Field(min_length=1, description="Authorization record identifier.")
    final_decision: VerificationDecisionEnum = Field(description="Final verification decision.")
    decision_rationale: NonEmptyString = Field(min_length=1, description="Decision rationale.")
    all_verification_results: list[VerificationResult] = Field(min_length=1, description="Embedded verification results.")
    evidence_references: list[EvidenceReference] = Field(min_length=1, description="Evidence store references.")
    side_effect_report: SideEffectReport = Field(description="Embedded side-effect report.")
    drift_report: DriftReport = Field(description="Embedded drift report.")
    stage_timestamps: dict[str, datetime] = Field(min_length=1, description="Lifecycle stage timestamps.")
    integrity_hash: HexDigest = Field(pattern=r"^[0-9a-fA-F]{64}$", description="SHA-256 hash of record content excluding this field.")
    previous_record_hash: HexDigest = Field(pattern=r"^[0-9a-fA-F]{64}$", description="Previous audit record hash.")
    record_schema_version: NonEmptyString = Field(min_length=1, description="Verification record schema version.")
    escalation_routing_id: str | None = Field(default=None, description="Optional escalation routing identifier.")
    human_reviewer_id: str | None = Field(default=None, description="Optional human reviewer identifier.")
    review_timestamp: datetime | None = Field(default=None, description="Optional UTC human review timestamp.")
    review_decision: ReviewDecision | None = Field(default=None, description="Optional human review decision.")

    @field_validator("review_timestamp")
    @classmethod
    def review_timestamp_must_be_utc(cls, value: datetime | None) -> datetime | None:
        if value is not None and not _is_utc(value):
            raise ValueError("review_timestamp must be UTC")
        return value

    @field_validator("stage_timestamps")
    @classmethod
    def stage_timestamps_must_be_utc(cls, value: dict[str, datetime]) -> dict[str, datetime]:
        if any(not _is_utc(timestamp) for timestamp in value.values()):
            raise ValueError("all stage_timestamps must be UTC")
        return value


class IntegrityChainEntry(ImmutableContract):
    record_id: UUID = Field(description="Audit record identifier.")
    record_hash: HexDigest = Field(pattern=r"^[0-9a-fA-F]{64}$", description="SHA-256 hash of record content.")
    previous_record_hash: HexDigest = Field(pattern=r"^[0-9a-fA-F]{64}$", description="Previous record hash.")
    chain_position: int = Field(ge=0, description="Monotonic chain sequence position.")
    write_timestamp: datetime = Field(description="UTC audit write timestamp.")
    chain_verification_timestamp: datetime | None = Field(default=None, description="Optional UTC chain verification timestamp.")

    @field_validator("write_timestamp", "chain_verification_timestamp")
    @classmethod
    def chain_timestamps_must_be_utc(cls, value: datetime | None) -> datetime | None:
        if value is not None and not _is_utc(value):
            raise ValueError("chain timestamps must be UTC")
        return value


class WriteConfirmation(ImmutableContract):
    record_id: UUID = Field(description="Audit record identifier just written.")
    integrity_hash: HexDigest = Field(pattern=r"^[0-9a-fA-F]{64}$", description="Integrity hash for the written record.")
    write_timestamp: datetime = Field(description="UTC audit write timestamp.")
    chain_position: int = Field(ge=0, description="Integrity chain sequence position.")
    chain_integrity_status: ChainIntegrityStatus | None = Field(default=None, description="Optional chain integrity status.")

    @field_validator("write_timestamp")
    @classmethod
    def write_timestamp_must_be_utc(cls, value: datetime) -> datetime:
        if not _is_utc(value):
            raise ValueError("write_timestamp must be UTC")
        return value


class VerificationOutcomeMessage(ImmutableContract):
    request_id: UUID = Field(description="Verification request identifier.")
    final_decision: VerificationDecisionEnum = Field(description="Audited final decision.")
    record_id: UUID = Field(description="Audit record identifier.")
    audit_integrity_hash: HexDigest = Field(pattern=r"^[0-9a-fA-F]{64}$", description="Audit record integrity hash.")
    decision_timestamp: datetime = Field(description="UTC final decision timestamp.")
    escalation_expiry: datetime | None = Field(default=None, description="Optional UTC escalation expiry.")
    partial_scope_description: str | None = Field(default=None, description="Optional PARTIAL scope description.")

    @field_validator("decision_timestamp", "escalation_expiry")
    @classmethod
    def outcome_timestamps_must_be_utc(cls, value: datetime | None) -> datetime | None:
        if value is not None and not _is_utc(value):
            raise ValueError("outcome timestamps must be UTC")
        return value

    @model_validator(mode="after")
    def outcome_details_must_match_decision(self) -> "VerificationOutcomeMessage":
        if self.final_decision == VerificationDecisionEnum.ESCALATE and self.escalation_expiry is None:
            raise ValueError("escalation_expiry is required for ESCALATE outcome messages")
        if self.final_decision == VerificationDecisionEnum.PARTIAL and not self.partial_scope_description:
            raise ValueError("partial_scope_description is required for PARTIAL outcome messages")
        return self
