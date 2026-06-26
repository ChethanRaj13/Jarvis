from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from WindowsAIAssistant.backend.verification_engine.contracts import SideEffectSurface, VerifierID


class ImmutableConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class EvidenceCollectionConfig(ImmutableConfig):
    evidence_window_seconds: int = Field(gt=0)
    collection_timeout_seconds: int = Field(gt=0)
    max_collection_retries: int = Field(default=0, ge=0)


class SideEffectDetectionConfig(ImmutableConfig):
    enabled: bool
    default_scopes: list[SideEffectSurface] = Field(min_length=1)
    protected_paths: list[Path] = Field(default_factory=list)


class ConfigurationVerificationConfig(ImmutableConfig):
    safety_config_paths: list[Path] = Field(default_factory=list)
    policy_config_paths: list[Path] = Field(default_factory=list)
    require_pre_execution_baseline: bool = True


class VerificationConfig(ImmutableConfig):
    evidence_collection: EvidenceCollectionConfig
    side_effect_detection: SideEffectDetectionConfig
    configuration_verification: ConfigurationVerificationConfig
    enabled_verifiers: list[VerifierID] = Field(min_length=1)
    verification_policy_file_locations: list[Path] = Field(default_factory=list)
