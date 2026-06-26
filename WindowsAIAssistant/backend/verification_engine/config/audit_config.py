from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ImmutableConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class AuditRetentionConfig(ImmutableConfig):
    retention_days: int = Field(gt=0)
    minimum_records_to_keep: int = Field(default=1, ge=1)


class AuditHashingConfig(ImmutableConfig):
    algorithm: Literal["SHA256"]
    digest_length: Literal[64]


class AuditChainConfig(ImmutableConfig):
    enabled: Literal[True]
    verify_on_startup: bool = True
    verification_interval_seconds: int = Field(gt=0)


class AuditPersistenceConfig(ImmutableConfig):
    enabled: Literal[True]
    append_only: Literal[True]
    audit_record_path: Path


class AuditConfig(ImmutableConfig):
    retention: AuditRetentionConfig
    hashing: AuditHashingConfig
    chain: AuditChainConfig
    persistence: AuditPersistenceConfig
