from verification_engine.contracts import EvidenceType
from verification_engine.evidence.builders import RegistryEvidenceBuilder

from ._base import BaseCollector


class RegistryCollector(BaseCollector):
    evidence_type = EvidenceType.REGISTRY
    builder = RegistryEvidenceBuilder()
