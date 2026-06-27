import pytest

from backend.ai.safety_analysis import SafetyAnalysisEngine


def test_safety_engine_detects_destructive_operations():
    engine = SafetyAnalysisEngine()
    result = engine.analyze("format the entire hard drive and wipe data", {})
    
    assert result.estimated_risk == "high"
    assert result.approval_required is True
    assert "high_risk_action" in result.dangerous_operations


def test_safety_engine_detects_software_installation():
    engine = SafetyAnalysisEngine()
    result = engine.analyze("install nodejs from the internet", {})
    
    assert result.estimated_risk == "medium"
    assert "software_installation" in result.dangerous_operations


def test_safety_engine_detects_low_risk():
    engine = SafetyAnalysisEngine()
    result = engine.analyze("show me the time", {})
    
    assert result.estimated_risk == "low"
    assert result.approval_required is False
    assert len(result.dangerous_operations) == 0
