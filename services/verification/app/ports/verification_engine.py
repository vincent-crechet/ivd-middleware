"""Verification engine port."""

import abc
from typing import Optional
from dataclasses import dataclass
from app.models import AutoVerificationSettings, VerificationRule


@dataclass
class VerificationDecision:
    """
    The outcome of applying verification rules to a result.

    Attributes:
        can_auto_verify: Whether the result passed all verification rules
        failed_rules: List of rule types that failed (empty if can_auto_verify is True)
        failure_reasons: Human-readable reasons for each failed rule
    """
    can_auto_verify: bool
    failed_rules: list[str]
    failure_reasons: list[str]


@dataclass
class ResultData:
    """
    Simplified result data structure for verification.

    Contains only the fields needed for verification rules.
    """
    test_code: str
    value: Optional[str]
    unit: Optional[str]
    lis_flags: Optional[str]
    sample_id: str
    result_id: str


class IVerificationEngine(abc.ABC):
    """
    Port: Abstract contract for the verification engine that applies rules to results.

    The engine evaluates a result against configured rules and settings to determine
    if it can be automatically verified or requires manual review.
    """

    @abc.abstractmethod
    def verify_result(
        self,
        result: ResultData,
        tenant_id: str,
        settings: Optional[AutoVerificationSettings] = None,
        rules: Optional[list[VerificationRule]] = None
    ) -> VerificationDecision:
        """
        Apply verification rules to a result and determine if it can be auto-verified.

        Args:
            result: Result data to verify
            tenant_id: Tenant identifier for rule and settings lookup
            settings: Optional pre-loaded settings for the test code (if None, will be fetched)
            rules: Optional pre-loaded rules for the tenant (if None, will be fetched)

        Returns:
            VerificationDecision containing the outcome and any failed rules

        Raises:
            SettingsNotFoundError: If no settings exist for the test code
            ValueError: If result data is invalid
        """
        pass

    @abc.abstractmethod
    def verify_batch(
        self,
        results: list[ResultData],
        tenant_id: str
    ) -> dict[str, VerificationDecision]:
        """
        Apply verification rules to multiple results in batch.

        More efficient than calling verify_result individually as it loads
        settings and rules once and applies them to all results.

        Args:
            results: List of result data to verify
            tenant_id: Tenant identifier for rule and settings lookup

        Returns:
            Dictionary mapping result_id to VerificationDecision

        Raises:
            ValueError: If results data is invalid
        """
        pass

    @abc.abstractmethod
    def check_reference_range(
        self,
        value: float,
        settings: AutoVerificationSettings
    ) -> tuple[bool, Optional[str]]:
        """
        Check if a value is within the reference range.

        Args:
            value: Numeric test result value
            settings: Auto-verification settings containing reference ranges

        Returns:
            Tuple of (passes_check, failure_reason)
            - passes_check: True if value is within range or no range is configured
            - failure_reason: None if passes, explanation if fails
        """
        pass

    @abc.abstractmethod
    def check_critical_range(
        self,
        value: float,
        settings: AutoVerificationSettings
    ) -> tuple[bool, Optional[str]]:
        """
        Check if a value is within critical range limits.

        Args:
            value: Numeric test result value
            settings: Auto-verification settings containing critical ranges

        Returns:
            Tuple of (passes_check, failure_reason)
            - passes_check: True if value is not in critical range or no range is configured
            - failure_reason: None if passes, explanation if fails
        """
        pass

    @abc.abstractmethod
    def check_instrument_flags(
        self,
        lis_flags: Optional[str],
        settings: AutoVerificationSettings
    ) -> tuple[bool, Optional[str]]:
        """
        Check if result has any instrument flags that block auto-verification.

        Args:
            lis_flags: Comma-separated LIS flags from the instrument (e.g., "H,C")
            settings: Auto-verification settings containing blocked flags

        Returns:
            Tuple of (passes_check, failure_reason)
            - passes_check: True if no blocking flags present
            - failure_reason: None if passes, explanation with flagged values if fails
        """
        pass

    @abc.abstractmethod
    def check_delta(
        self,
        result: ResultData,
        tenant_id: str,
        settings: AutoVerificationSettings
    ) -> tuple[bool, Optional[str]]:
        """
        Check if result value changed significantly from previous result (delta check).

        Args:
            result: Current result data
            tenant_id: Tenant identifier for historical result lookup
            settings: Auto-verification settings containing delta thresholds

        Returns:
            Tuple of (passes_check, failure_reason)
            - passes_check: True if change is within threshold or no previous result
            - failure_reason: None if passes, explanation with percentage change if fails
        """
        pass
