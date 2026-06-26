from WindowsAIAssistant.backend.verification_engine.contracts.enums import (
    ActionType,
    EvidenceType,
    ReviewDecision,
    RiskLevel,
    SideEffectSeverity,
    SideEffectSurface,
    ValidationStatus,
    VerificationDecisionEnum,
    VerifierID,
)


def values(enum_cls):
    return [item.value for item in enum_cls]


def test_action_type_values():
    assert values(ActionType) == [
        "FILE_CREATE",
        "FILE_DELETE",
        "FILE_MODIFY",
        "FILE_MOVE",
        "REGISTRY_CREATE",
        "REGISTRY_MODIFY",
        "REGISTRY_DELETE",
        "PROCESS_LAUNCH",
        "PROCESS_TERMINATE",
        "TASK_CREATE",
        "TASK_MODIFY",
        "TASK_DELETE",
        "DOWNLOAD",
        "CONFIG_MODIFY",
    ]


def test_core_enum_values():
    assert values(VerificationDecisionEnum) == ["VERIFIED", "FAILED", "PARTIAL", "ESCALATE"]
    assert values(EvidenceType) == ["FILESYSTEM", "REGISTRY", "PROCESS", "TASK", "DOWNLOAD", "CONFIGURATION"]
    assert values(ValidationStatus) == ["PENDING", "VALID", "INVALID", "INCOMPLETE"]
    assert values(SideEffectSeverity) == ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    assert values(SideEffectSurface) == ["FILESYSTEM", "REGISTRY", "PROCESS", "NETWORK", "PERSISTENCE"]
    assert values(RiskLevel) == ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert values(VerifierID) == ["FILESYSTEM", "REGISTRY", "PROCESS", "TASK", "DOWNLOAD", "CONFIGURATION", "SIDE_EFFECT", "DRIFT"]
    assert values(ReviewDecision) == ["ACCEPTED", "REJECTED", "FURTHER_INVESTIGATION"]
