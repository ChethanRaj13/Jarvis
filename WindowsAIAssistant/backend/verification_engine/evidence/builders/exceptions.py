class EvidenceBuilderError(Exception):
    """Base class for evidence builder failures."""


class EvidenceBuilderValidationError(EvidenceBuilderError):
    """Raised when raw evidence cannot be converted into a typed evidence package."""
