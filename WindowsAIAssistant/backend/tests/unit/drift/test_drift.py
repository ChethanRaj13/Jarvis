from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from WindowsAIAssistant.backend.verification_engine.contracts import SideEffectSeverity, VerificationDecisionEnum, VerificationResult, VerifierID
from WindowsAIAssistant.backend.verification_engine.drift import DriftAccumulator, DriftAttributor, DriftReportBuilder, InvalidAnalysisInput


def make_result(**overrides) -> VerificationResult:
    values = {
        "result_id": uuid4(),
        "request_id": uuid4(),
        "verifier_id": VerifierID.CONFIGURATION,
        "sub_decision": VerificationDecisionEnum.FAILED,
        "confirmed_attributes": ["config_path"],
        "failed_attributes": ["safety_engine_config_modified"],
        "evidence_reference": uuid4(),
        "sub_decision_rationale": "configuration drift",
        "result_timestamp": datetime.now(timezone.utc),
        "controlling_attribute": "safety-policy.json",
    }
    values.update(overrides)
    return VerificationResult(**values)


def test_accumulator_collects_failed_attribute_drift() -> None:
    accumulation = DriftAccumulator().accumulate((make_result(),))

    assert len(accumulation.observations) == 1
    assert accumulation.observations[0].authorized is False
    assert accumulation.observations[0].severity == SideEffectSeverity.CRITICAL


def test_accumulator_collects_payload_drift_findings() -> None:
    result = make_result(
        failed_attributes=[],
        sub_decision=VerificationDecisionEnum.PARTIAL,
        drift_findings=[
            {
                "attribute": "registry_value_type",
                "expected": "REG_SZ",
                "observed": "REG_DWORD",
                "affected_asset": "HKCU\\Software\\App",
                "authorized": True,
                "expected_drift": True,
            }
        ],
    )

    accumulation = DriftAccumulator().accumulate((result,))

    assert accumulation.observations[0].authorized is True
    assert accumulation.observations[0].expected_drift is True
    assert accumulation.observations[0].observed == "REG_DWORD"


def test_accumulator_rejects_invalid_input() -> None:
    with pytest.raises(InvalidAnalysisInput):
        DriftAccumulator().accumulate((object(),))  # type: ignore[arg-type]


def test_attributor_separates_expected_and_unauthorized_drift() -> None:
    accumulation = DriftAccumulator().accumulate((make_result(),))

    attribution = DriftAttributor().attribute(accumulation)

    assert attribution.expected == ()
    assert len(attribution.unexpected) == 1
    assert len(attribution.unauthorized) == 1
    assert "unexpected" in attribution.rationale[0]


def test_attributor_rejects_invalid_input() -> None:
    with pytest.raises(InvalidAnalysisInput):
        DriftAttributor().attribute(object())  # type: ignore[arg-type]


def test_report_builder_outputs_contract_report() -> None:
    result = make_result()
    accumulation = DriftAccumulator().accumulate((result,))
    attribution = DriftAttributor().attribute(accumulation)

    report = DriftReportBuilder().build(
        session_id="session-1",
        request_id=result.request_id,
        attribution=attribution,
        session_boundary_verified=True,
    )

    assert report.request_id == result.request_id
    assert report.drift_sub_decision == VerificationDecisionEnum.FAILED
    assert report.cumulative_unattributed_count == 1
    assert report.session_boundary_verified is True
    assert report.attribution_findings[0].attributed_to_request_id is None


def test_report_builder_requires_valid_inputs() -> None:
    accumulation = DriftAccumulator().accumulate((make_result(),))
    attribution = DriftAttributor().attribute(accumulation)

    with pytest.raises(InvalidAnalysisInput):
        DriftReportBuilder().build(session_id="", request_id=uuid4(), attribution=attribution)

    with pytest.raises(InvalidAnalysisInput):
        DriftReportBuilder().build(session_id="session-1", request_id=uuid4(), attribution=object())  # type: ignore[arg-type]
