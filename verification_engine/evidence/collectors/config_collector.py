from verification_engine.contracts import EvidenceType
from verification_engine.evidence.builders import ConfigurationEvidenceBuilder

from ._base import BaseCollector


class ConfigurationCollector(BaseCollector):
    evidence_type = EvidenceType.CONFIGURATION
    builder = ConfigurationEvidenceBuilder()
