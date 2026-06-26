class CollectorError(Exception):
    """Base class for evidence collector failures."""


class CollectionFailure(CollectorError):
    """Raised when raw evidence collection or package assembly fails."""


class InvalidCollectionRequest(CollectorError):
    """Raised when a collection request is malformed."""


class UnsupportedCollection(CollectorError):
    """Raised when a collector receives an unsupported evidence type."""
