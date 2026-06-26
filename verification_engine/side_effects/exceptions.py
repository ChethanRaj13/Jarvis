class SideEffectError(Exception):
    """Base exception for side-effect analysis failures."""


class InvalidAnalysisInput(SideEffectError):
    """Raised when side-effect analysis receives invalid input."""


class AnalysisFailure(SideEffectError):
    """Raised when side-effect analysis cannot complete safely."""
