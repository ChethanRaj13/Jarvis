from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class ImmutableConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class EvidenceStorageConfig(ImmutableConfig):
    root_path: Path
    append_only: bool = True
    max_evidence_package_bytes: int = Field(gt=0)


class AuditStorageConfig(ImmutableConfig):
    root_path: Path
    append_only: bool = True
    integrity_chain_required: bool = True


class ReplayStorageConfig(ImmutableConfig):
    root_path: Path
    ttl_seconds: int = Field(gt=0)


class DriftStorageConfig(ImmutableConfig):
    root_path: Path
    retention_days: int = Field(gt=0)


class PendingStorageConfig(ImmutableConfig):
    root_path: Path
    expiry_seconds: int = Field(gt=0)


class StorageConfig(ImmutableConfig):
    evidence_storage: EvidenceStorageConfig
    audit_storage: AuditStorageConfig
    replay_storage: ReplayStorageConfig
    drift_storage: DriftStorageConfig
    pending_storage: PendingStorageConfig
