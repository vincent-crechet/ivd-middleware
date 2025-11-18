"""Domain-specific exceptions for Platform Service."""


class PlatformServiceError(Exception):
    """Base exception for Platform Service."""
    pass


class TenantNotFoundError(PlatformServiceError):
    """Raised when a tenant doesn't exist."""
    pass


class DuplicateTenantError(PlatformServiceError):
    """Raised when attempting to create a tenant with duplicate name."""
    pass


class UserNotFoundError(PlatformServiceError):
    """Raised when a user doesn't exist."""
    pass


class DuplicateUserError(PlatformServiceError):
    """Raised when attempting to create a user with duplicate email in tenant."""
    pass


class InvalidCredentialsError(PlatformServiceError):
    """Raised when authentication fails."""
    pass


class InvalidPasswordError(PlatformServiceError):
    """Raised when password doesn't meet requirements."""
    pass


class UnauthorizedError(PlatformServiceError):
    """Raised when user lacks permissions for an operation."""
    pass
