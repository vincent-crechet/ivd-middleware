"""Custom exceptions for Instrument Integration Service."""


class InstrumentError(Exception):
    """Base exception for Instrument Integration Service."""
    pass


class InstrumentNotFoundError(InstrumentError):
    """Raised when an instrument cannot be found."""
    pass


class InstrumentAlreadyExistsError(InstrumentError):
    """Raised when trying to create a duplicate instrument."""
    pass


class InvalidApiTokenError(InstrumentError):
    """Raised when an API token is invalid or unauthorized."""
    pass


class OrderNotFoundError(InstrumentError):
    """Raised when an order cannot be found."""
    pass


class OrderAlreadyExistsError(InstrumentError):
    """Raised when trying to create a duplicate order."""
    pass


class InvalidOrderDataError(InstrumentError):
    """Raised when order data is invalid."""
    pass


class InstrumentResultNotFoundError(InstrumentError):
    """Raised when a result cannot be found."""
    pass


class InstrumentResultAlreadyExistsError(InstrumentError):
    """Raised when trying to create a duplicate result."""
    pass


class InvalidResultDataError(InstrumentError):
    """Raised when result data is invalid."""
    pass


class InstrumentConfigurationError(InstrumentError):
    """Raised when instrument configuration is invalid."""
    pass
