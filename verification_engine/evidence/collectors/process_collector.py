from verification_engine.contracts import EvidenceType
from verification_engine.evidence.builders import ProcessEvidenceBuilder

from ._base import BaseCollector


class ProcessCollector(BaseCollector):
    evidence_type = EvidenceType.PROCESS
    builder = ProcessEvidenceBuilder()
