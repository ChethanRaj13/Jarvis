class VerificationError(Exception):
    """Base class for verification domain failures."""


class InvalidAuthorizationError(VerificationError):
    """Raised when an authorization record cannot support verification."""


class InvalidEvidenceError(VerificationError):
    """Raised when evidence is missing or not applicable to a verifier."""
