from verification_engine.contracts import EvidenceType
from verification_engine.evidence.builders import TaskEvidenceBuilder

from ._base import BaseCollector


class TaskCollector(BaseCollector):
    evidence_type = EvidenceType.TASK
    builder = TaskEvidenceBuilder()
