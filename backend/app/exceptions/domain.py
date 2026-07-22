"""Domain-level exceptions used by services without coupling them to FastAPI."""


class DomainError(Exception):
    """Base exception for expected domain failures."""


class EntityNotFoundError(DomainError):
    """Raised when a requested domain entity does not exist."""


class EntityConflictError(DomainError):
    """Raised when a request violates a uniqueness or lifecycle constraint."""


class EntityValidationError(DomainError):
    """Raised when a cross-entity domain invariant is invalid."""

