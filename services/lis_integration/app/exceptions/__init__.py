"""Domain exceptions for LIS Integration Service."""


class LISIntegrationError(Exception):
    """Base exception for LIS Integration Service."""
    pass


class SampleNotFoundError(LISIntegrationError):
    """Raised when sample is not found."""
    pass


class ResultNotFoundError(LISIntegrationError):
    """Raised when result is not found."""
    pass


class DuplicateSampleError(LISIntegrationError):
    """Raised when duplicate sample is detected."""
    pass


class DuplicateResultError(LISIntegrationError):
    """Raised when duplicate result is detected."""
    pass


class InvalidSampleDataError(LISIntegrationError):
    """Raised when sample data is invalid."""
    pass


class InvalidResultDataError(LISIntegrationError):
    """Raised when result data is invalid."""
    pass


class LISConfigNotFoundError(LISIntegrationError):
    """Raised when LIS configuration is not found for tenant."""
    pass


class LISConfigurationError(LISIntegrationError):
    """Raised when LIS configuration is invalid."""
    pass


class LISConnectionError(LISIntegrationError):
    """Raised when LIS connection fails."""
    pass


class LISDataFormatError(LISIntegrationError):
    """Raised when LIS data format is invalid."""
    pass


class OrderNotFoundError(LISIntegrationError):
    """Raised when order is not found."""
    pass


class InvalidOrderDataError(LISIntegrationError):
    """Raised when order data is invalid."""
    pass


class ResultImmutableError(LISIntegrationError):
    """Raised when trying to modify an immutable result."""
    pass


class UnauthorizedAPIKeyError(LISIntegrationError):
    """Raised when API key is invalid or missing for push model."""
    pass
