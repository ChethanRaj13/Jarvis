class ConfigurationError(Exception):
    """Base class for configuration layer failures."""


class ConfigurationFileNotFound(ConfigurationError):
    """Raised when a configuration file does not exist."""


class ConfigurationParseError(ConfigurationError):
    """Raised when a configuration file cannot be parsed as JSON."""


class ConfigurationValidationError(ConfigurationError):
    """Raised when configuration content fails model validation."""
