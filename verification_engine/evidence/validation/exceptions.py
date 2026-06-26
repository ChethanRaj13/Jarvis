class ValidationError(Exception):
    """Base class for evidence validation failures."""


class WindowValidationError(ValidationError):
    """Raised when window validation cannot be executed."""


class BindingValidationError(ValidationError):
    """Raised when binding validation cannot be executed."""


class CompletenessValidationError(ValidationError):
    """Raised when completeness validation cannot be executed."""
