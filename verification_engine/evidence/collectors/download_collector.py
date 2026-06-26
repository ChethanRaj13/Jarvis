from verification_engine.contracts import EvidenceType
from verification_engine.evidence.builders import DownloadEvidenceBuilder

from ._base import BaseCollector


class DownloadCollector(BaseCollector):
    evidence_type = EvidenceType.DOWNLOAD
    builder = DownloadEvidenceBuilder()
