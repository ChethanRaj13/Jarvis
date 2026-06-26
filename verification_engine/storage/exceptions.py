class StorageError(Exception):
    """Base class for storage layer failures."""


class StoragePathError(StorageError):
    """Raised when a storage path is invalid or inaccessible."""


class StorageItemNotFound(StorageError):
    """Raised when a requested storage item does not exist."""


class StorageItemAlreadyExists(StorageError):
    """Raised when an append-only storage item already exists."""


class StorageImmutableRecordError(StorageError):
    """Raised when an immutable storage record would be modified."""
