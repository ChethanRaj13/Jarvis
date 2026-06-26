from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from .config_integrity_check import StartupCheckResult


@dataclass(frozen=True)
class AuditStoreRequirement:
    path: Path


class AuditStoreCheck:
    def __init__(self, requirement: AuditStoreRequirement, mandatory: bool = True) -> None:
        self._requirement = requirement
        self._mandatory = mandatory

    def run(self) -> StartupCheckResult:
        path = Path(self._requirement.path).expanduser().resolve()
        messages: list[str] = []

        if not path.exists():
            messages.append("audit store location does not exist")
        elif not path.is_dir():
            messages.append("audit store location is not a directory")
        else:
            try:
                probe_path = path / f".verification_engine_write_probe_{uuid4().hex}"
                probe_path.write_text("", encoding="utf-8")
                probe_path.unlink()
            except OSError:
                messages.append("audit store location is not writable")

        return StartupCheckResult(
            check_name="audit_store",
            passed=not messages,
            mandatory=self._mandatory,
            messages=tuple(messages),
        )
