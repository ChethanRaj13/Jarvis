from WindowsAIAssistant.backend.verification_engine.contracts import EvidenceType
from WindowsAIAssistant.backend.verification_engine.evidence.builders import RegistryEvidenceBuilder

from ._base import BaseCollector


class RegistryCollector(BaseCollector):
    evidence_type = EvidenceType.REGISTRY
    builder = RegistryEvidenceBuilder()
