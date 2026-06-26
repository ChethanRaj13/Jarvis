from datetime import timezone

import pytest

from verification_engine.security.alerts.security_alert_emitter import (
    SecurityAlertEmitter,
    SecurityAlertSeverity,
)


def test_security_alert_emitter_creates_structured_alert():
    alert = SecurityAlertEmitter().create_alert(
        severity=SecurityAlertSeverity.CRITICAL,
        title="Startup blocked",
        message="Audit store is unavailable",
        context={"check": "audit_store"},
    )

    assert alert.severity == SecurityAlertSeverity.CRITICAL
    assert alert.title == "Startup blocked"
    assert alert.context == {"check": "audit_store"}
    assert alert.created_at.tzinfo == timezone.utc


def test_security_alert_emitter_validates_severity():
    with pytest.raises(ValueError):
        SecurityAlertEmitter().create_alert(
            severity="SEVERE",
            title="Invalid severity",
            message="This severity is unsupported",
        )
