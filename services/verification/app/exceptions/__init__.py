"""Verification service exceptions."""


class VerificationException(Exception):
    """Base exception for verification service."""
    pass


class SettingsNotFoundError(VerificationException):
    """Auto-verification settings not found."""
    pass


class SettingsAlreadyExistsError(VerificationException):
    """Auto-verification settings already exist for this test code in tenant."""
    pass


class ReviewNotFoundError(VerificationException):
    """Review not found."""
    pass


class SampleNotFoundError(VerificationException):
    """Sample not found."""
    pass


class ResultNotFoundError(VerificationException):
    """Result not found."""
    pass


class ReviewAlreadyExistsError(VerificationException):
    """A review already exists for this sample."""
    pass


class ReviewCannotBeModifiedError(VerificationException):
    """Review cannot be modified after submission."""
    pass


class InvalidReviewDecisionError(VerificationException):
    """Invalid review decision."""
    pass


class InvalidResultDecisionError(VerificationException):
    """Invalid result decision in review."""
    pass


class ReviewStateTransitionError(VerificationException):
    """Invalid state transition for review."""
    pass


class RuleNotFoundError(VerificationException):
    """Verification rule not found."""
    pass


class InsufficientPermissionError(VerificationException):
    """User does not have permission to perform this action."""
    pass


class InvalidConfigurationError(VerificationException):
    """Invalid configuration for verification."""
    pass
