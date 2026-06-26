from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from verification_engine.contracts import (
    SideEffectSeverity,
    SideEffectSurface,
    VerificationDecisionEnum,
    VerificationResult,
    VerifierID,
)
from verification_engine.side_effects import (
    DetectedSideEffect,
    InvalidAnalysisInput,
    SideEffectClassification,
    SideEffectClassifier,
    SideEffectDetector,
    SideEffectReportBuilder,
)


def make_result(**overrides) -> VerificationResult:
    values = {
        "result_id": uuid4(),
        "request_id": uuid4(),
        "verifier_id": VerifierID.FILESYSTEM,
        "sub_decision": VerificationDecisionEnum.FAILED,
        "confirmed_attributes": ["path"],
        "failed_attributes": ["unexpected_filesystem_entries"],
        "evidence_reference": uuid4(),
        "sub_decision_rationale": "unexpected side effect",
        "result_timestamp": datetime.now(timezone.utc),
        "controlling_attribute": "C:\\Temp\\artifact.txt",
    }
    values.update(overrides)
    return VerificationResult(**values)


def test_detector_uses_reported_side_effect_payload() -> None:
    result = make_result(
        detected_side_effects=[
            {
                "surface": "REGISTRY",
                "affected_resource": "HKCU\\Software\\Run",
                "change_type": "created startup entry",
                "severity": "CRITICAL",
                "rationale": "persistence entry outside scope",
            }
        ],
        failed_attributes=[],
        sub_decision=VerificationDecisionEnum.PARTIAL,
    )

    detection = SideEffectDetector().detect(result)

    assert detection.fail_closed is False
    assert detection.effects[0].surface == SideEffectSurface.REGISTRY
    assert detection.effects[0].severity == SideEffectSeverity.CRITICAL
    assert "persistence" in detection.effects[0].rationale


def test_detector_infers_effects_from_failed_attributes() -> None:
    detection = SideEffectDetector().detect(make_result())

    assert len(detection.effects) == 1
    assert detection.effects[0].surface == SideEffectSurface.FILESYSTEM
    assert detection.effects[0].affected_resource == "C:\\Temp\\artifact.txt"


def test_detector_rejects_invalid_input() -> None:
    with pytest.raises(InvalidAnalysisInput):
        SideEffectDetector().detect(object())  # type: ignore[arg-type]


def test_classifier_returns_none_for_empty_effects() -> None:
    classification = SideEffectClassifier().classify(())

    assert classification.classification == SideEffectClassification.NONE


def test_classifier_returns_highest_effect_severity() -> None:
    effects = (
        DetectedSideEffect(
            surface=SideEffectSurface.FILESYSTEM,
            affected_resource="C:\\Temp\\a.txt",
            change_type="created",
            severity=SideEffectSeverity.LOW,
            rationale="file created",
            source_result_id=str(uuid4()),
        ),
        DetectedSideEffect(
            surface=SideEffectSurface.PERSISTENCE,
            affected_resource="StartupTask",
            change_type="persistence",
            severity=SideEffectSeverity.CRITICAL,
            rationale="startup persistence",
            source_result_id=str(uuid4()),
        ),
    )

    classification = SideEffectClassifier().classify(effects)

    assert classification.classification == SideEffectClassification.CRITICAL


def test_classifier_requires_tuple() -> None:
    with pytest.raises(InvalidAnalysisInput):
        SideEffectClassifier().classify([])  # type: ignore[arg-type]


def test_report_builder_creates_contract_report() -> None:
    request_id = uuid4()
    effect = DetectedSideEffect(
        surface=SideEffectSurface.PROCESS,
        affected_resource="powershell.exe",
        change_type="spawned child process",
        severity=SideEffectSeverity.HIGH,
        rationale="unexpected child process",
        source_result_id=str(uuid4()),
    )

    report = SideEffectReportBuilder().build(
        request_id=request_id,
        effects=(effect,),
        classification=SideEffectClassification.HIGH,
        detection_scope="process descendants",
        tool_registry_informed_scope=True,
    )

    assert report.request_id == request_id
    assert report.side_effect_sub_decision == VerificationDecisionEnum.FAILED
    assert report.unauthorized_changes[0].surface == SideEffectSurface.PROCESS
    assert report.tool_registry_informed_scope is True


def test_report_builder_requires_scope_and_tuple() -> None:
    with pytest.raises(InvalidAnalysisInput):
        SideEffectReportBuilder().build(
            request_id=uuid4(),
            effects=(),  # type: ignore[arg-type]
            classification=SideEffectClassification.NONE,
            detection_scope="",
        )
