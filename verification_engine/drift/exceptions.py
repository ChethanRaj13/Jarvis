class DriftError(Exception):
    """Base exception for drift analysis failures."""


class InvalidAnalysisInput(DriftError):
    """Raised when drift analysis receives invalid input."""


class AnalysisFailure(DriftError):
    """Raised when drift analysis cannot complete safely."""
