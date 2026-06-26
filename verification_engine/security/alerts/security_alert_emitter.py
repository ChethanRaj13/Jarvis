from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class SecurityAlertSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class SecurityAlert:
    alert_id: UUID
    severity: SecurityAlertSeverity
    title: str
    message: str
    created_at: datetime
    context: dict[str, Any] = field(default_factory=dict)


class SecurityAlertEmitter:
    def create_alert(
        self,
        severity: SecurityAlertSeverity | str,
        title: str,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> SecurityAlert:
        parsed_severity = SecurityAlertSeverity(severity)
        return SecurityAlert(
            alert_id=uuid4(),
            severity=parsed_severity,
            title=title,
            message=message,
            created_at=datetime.now(timezone.utc),
            context=dict(context or {}),
        )
