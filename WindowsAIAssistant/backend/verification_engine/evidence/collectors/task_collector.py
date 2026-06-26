from WindowsAIAssistant.backend.verification_engine.contracts import EvidenceType
from WindowsAIAssistant.backend.verification_engine.evidence.builders import TaskEvidenceBuilder

from ._base import BaseCollector


class TaskCollector(BaseCollector):
    evidence_type = EvidenceType.TASK
    builder = TaskEvidenceBuilder()
