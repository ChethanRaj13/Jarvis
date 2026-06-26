from WindowsAIAssistant.backend.verification_engine.contracts import EvidenceType
from WindowsAIAssistant.backend.verification_engine.evidence.builders import ProcessEvidenceBuilder

from ._base import BaseCollector


class ProcessCollector(BaseCollector):
    evidence_type = EvidenceType.PROCESS
    builder = ProcessEvidenceBuilder()
