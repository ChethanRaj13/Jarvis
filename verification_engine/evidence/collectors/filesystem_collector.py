from verification_engine.contracts import EvidenceType
from verification_engine.evidence.builders import FilesystemEvidenceBuilder

from ._base import BaseCollector


class FilesystemCollector(BaseCollector):
    evidence_type = EvidenceType.FILESYSTEM
    builder = FilesystemEvidenceBuilder()
