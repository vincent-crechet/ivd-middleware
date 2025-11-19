"""Verification engine implementation."""

import logging
from typing import Optional
from datetime import datetime, timedelta

from app.ports.verification_engine import (
    IVerificationEngine,
    VerificationDecision,
    ResultData,
)
from app.ports.auto_verification_settings_repository import (
    IAutoVerificationSettingsRepository,
)
from app.ports.verification_rule_repository import IVerificationRuleRepository
from app.models import AutoVerificationSettings, VerificationRule, RuleType
from app.exceptions import SettingsNotFoundError

# Note: We import from LIS integration service for result history lookup
# In production, this would be done via service-to-service communication
try:
    from services.lis_integration.app.ports.result_repository import IResultRepository
except ImportError:
    # Fallback for when running in isolation
    from typing import Protocol

    class IResultRepository(Protocol):
        """Protocol for result repository when LIS service is not available."""

        def list_by_sample(self, sample_id: str, tenant_id: str) -> list:
            """List results by sample."""
            ...


logger = logging.getLogger(__name__)


class VerificationEngine(IVerificationEngine):
    """
    Implementation of the verification engine that applies rules to results.

    This engine evaluates test results against configured verification rules to
    determine if they can be automatically verified or require manual review.

    Implements a short-circuit evaluation strategy: stops processing as soon as
    any rule fails. Rules are evaluated in priority order.

    Attributes:
        settings_repository: Repository for auto-verification settings
        rules_repository: Repository for verification rules
        result_repository: Repository for historical results (for delta checks)
    """

    def __init__(
        self,
        settings_repository: IAutoVerificationSettingsRepository,
        rules_repository: IVerificationRuleRepository,
        result_repository: Optional[IResultRepository] = None,
    ):
        """
        Initialize the verification engine.

        Args:
            settings_repository: Repository for accessing verification settings
            rules_repository: Repository for accessing verification rules
            result_repository: Optional repository for accessing historical results
                             (required only if delta check rule is enabled)
        """
        self.settings_repository = settings_repository
        self.rules_repository = rules_repository
        self.result_repository = result_repository

    def verify_result(
        self,
        result: ResultData,
        tenant_id: str,
        settings: Optional[AutoVerificationSettings] = None,
        rules: Optional[list[VerificationRule]] = None,
    ) -> VerificationDecision:
        """
        Apply verification rules to a result and determine if it can be auto-verified.

        Uses short-circuit evaluation: stops at the first failed rule.
        Rules are evaluated in priority order (lowest priority number first).

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
        logger.info(
            f"Verifying result {result.result_id} for test {result.test_code} "
            f"in tenant {tenant_id}"
        )

        # Validate result data
        if not result.test_code:
            raise ValueError("Result must have a test_code")
        if not result.result_id:
            raise ValueError("Result must have a result_id")

        # Load settings if not provided
        if settings is None:
            settings = self.settings_repository.get_by_test_code(
                result.test_code, tenant_id
            )
            if settings is None:
                raise SettingsNotFoundError(
                    f"No auto-verification settings found for test code "
                    f"{result.test_code} in tenant {tenant_id}"
                )

        # Load rules if not provided
        if rules is None:
            rules = self.rules_repository.get_by_tenant(tenant_id)

        # Filter to only enabled rules and sort by priority
        enabled_rules = [r for r in rules if r.enabled]
        enabled_rules.sort(key=lambda r: r.priority)

        logger.debug(
            f"Applying {len(enabled_rules)} enabled rules to result {result.result_id}"
        )

        # Apply each rule in order (short-circuit on first failure)
        failed_rules = []
        failure_reasons = []

        for rule in enabled_rules:
            passes, reason = self._apply_rule(rule, result, tenant_id, settings)

            if not passes:
                logger.info(
                    f"Result {result.result_id} failed rule {rule.rule_type}: {reason}"
                )
                failed_rules.append(rule.rule_type.value)
                failure_reasons.append(reason)
                # Short-circuit: stop on first failure
                break

        # Determine if result can be auto-verified
        can_auto_verify = len(failed_rules) == 0

        if can_auto_verify:
            logger.info(
                f"Result {result.result_id} passed all verification rules - can auto-verify"
            )
        else:
            logger.info(
                f"Result {result.result_id} failed verification - needs manual review"
            )

        return VerificationDecision(
            can_auto_verify=can_auto_verify,
            failed_rules=failed_rules,
            failure_reasons=failure_reasons,
        )

    def verify_batch(
        self, results: list[ResultData], tenant_id: str
    ) -> dict[str, VerificationDecision]:
        """
        Apply verification rules to multiple results in batch.

        More efficient than calling verify_result individually as it loads
        settings and rules once and caches them for all results.

        Args:
            results: List of result data to verify
            tenant_id: Tenant identifier for rule and settings lookup

        Returns:
            Dictionary mapping result_id to VerificationDecision

        Raises:
            ValueError: If results data is invalid
        """
        logger.info(
            f"Batch verifying {len(results)} results for tenant {tenant_id}"
        )

        if not results:
            return {}

        # Load rules once for all results
        rules = self.rules_repository.get_by_tenant(tenant_id)

        # Group results by test code to batch load settings
        results_by_test = {}
        for result in results:
            if result.test_code not in results_by_test:
                results_by_test[result.test_code] = []
            results_by_test[result.test_code].append(result)

        # Load settings for each unique test code
        settings_cache = {}
        for test_code in results_by_test.keys():
            settings = self.settings_repository.get_by_test_code(test_code, tenant_id)
            if settings:
                settings_cache[test_code] = settings

        # Verify each result using cached settings and rules
        decisions = {}
        for result in results:
            try:
                settings = settings_cache.get(result.test_code)
                if settings is None:
                    # No settings for this test code - cannot auto-verify
                    logger.warning(
                        f"No settings found for test {result.test_code} - "
                        f"result {result.result_id} cannot be auto-verified"
                    )
                    decisions[result.result_id] = VerificationDecision(
                        can_auto_verify=False,
                        failed_rules=["settings_missing"],
                        failure_reasons=[
                            f"No verification settings configured for test {result.test_code}"
                        ],
                    )
                else:
                    decisions[result.result_id] = self.verify_result(
                        result, tenant_id, settings=settings, rules=rules
                    )
            except Exception as e:
                logger.error(
                    f"Error verifying result {result.result_id}: {str(e)}",
                    exc_info=True,
                )
                decisions[result.result_id] = VerificationDecision(
                    can_auto_verify=False,
                    failed_rules=["verification_error"],
                    failure_reasons=[f"Verification error: {str(e)}"],
                )

        logger.info(
            f"Batch verification complete: {sum(1 for d in decisions.values() if d.can_auto_verify)} "
            f"of {len(results)} results can be auto-verified"
        )

        return decisions

    def check_reference_range(
        self, value: float, settings: AutoVerificationSettings
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
        # If no range configured, pass by default
        if (
            settings.reference_range_low is None
            and settings.reference_range_high is None
        ):
            return True, None

        # Check lower bound
        if (
            settings.reference_range_low is not None
            and value < settings.reference_range_low
        ):
            return (
                False,
                f"Value {value} below reference range minimum {settings.reference_range_low}",
            )

        # Check upper bound
        if (
            settings.reference_range_high is not None
            and value > settings.reference_range_high
        ):
            return (
                False,
                f"Value {value} above reference range maximum {settings.reference_range_high}",
            )

        return True, None

    def check_critical_range(
        self, value: float, settings: AutoVerificationSettings
    ) -> tuple[bool, Optional[str]]:
        """
        Check if a value is within critical range limits.

        Critical ranges represent dangerous values. If a value is in the critical range,
        it should NOT be auto-verified.

        Args:
            value: Numeric test result value
            settings: Auto-verification settings containing critical ranges

        Returns:
            Tuple of (passes_check, failure_reason)
            - passes_check: True if value is not in critical range or no range is configured
            - failure_reason: None if passes, explanation if fails
        """
        # If no critical range configured, pass by default
        if (
            settings.critical_range_low is None
            and settings.critical_range_high is None
        ):
            return True, None

        # Check if value is critically low
        if (
            settings.critical_range_low is not None
            and value <= settings.critical_range_low
        ):
            return (
                False,
                f"Value {value} in critical range (critically low, <= {settings.critical_range_low})",
            )

        # Check if value is critically high
        if (
            settings.critical_range_high is not None
            and value >= settings.critical_range_high
        ):
            return (
                False,
                f"Value {value} in critical range (critically high, >= {settings.critical_range_high})",
            )

        return True, None

    def check_instrument_flags(
        self, lis_flags: Optional[str], settings: AutoVerificationSettings
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
        # If no flags on result, pass
        if not lis_flags:
            return True, None

        # Get list of blocked flags from settings
        blocked_flags = settings.get_instrument_flags_to_block()
        if not blocked_flags:
            return True, None

        # Parse flags from result (handle comma, semicolon, or space separated)
        result_flags = [
            f.strip().upper()
            for f in lis_flags.replace(";", ",").replace(" ", ",").split(",")
            if f.strip()
        ]

        # Check for any blocked flags
        blocked_flags_upper = [f.upper() for f in blocked_flags]
        found_blocked = [f for f in result_flags if f in blocked_flags_upper]

        if found_blocked:
            return (
                False,
                f"Result has blocked instrument flags: {', '.join(found_blocked)}",
            )

        return True, None

    def check_delta(
        self,
        result: ResultData,
        tenant_id: str,
        settings: AutoVerificationSettings,
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
        # If no delta threshold configured, pass
        if settings.delta_check_threshold_percent is None:
            return True, None

        # Verify result repository is available
        if self.result_repository is None:
            logger.warning(
                "Delta check requested but no result repository available - skipping"
            )
            return True, None

        # Parse current value
        try:
            current_value = float(result.value)
        except (TypeError, ValueError):
            logger.debug(
                f"Cannot perform delta check on non-numeric value: {result.value}"
            )
            return True, None  # Can't do delta check on non-numeric values

        # Find previous result for the same test and sample
        try:
            previous_results = self.result_repository.list_by_sample(
                result.sample_id, tenant_id
            )

            # Filter to same test code, exclude current result, get most recent
            previous_results = [
                r
                for r in previous_results
                if r.test_code == result.test_code and r.id != result.result_id
            ]

            # Filter by lookback days if configured
            if settings.delta_check_lookback_days:
                cutoff_date = datetime.utcnow() - timedelta(
                    days=settings.delta_check_lookback_days
                )
                previous_results = [
                    r for r in previous_results if r.created_at >= cutoff_date
                ]

            if not previous_results:
                logger.debug(
                    f"No previous result found for delta check on result {result.result_id}"
                )
                return True, None  # No previous result to compare

            # Get most recent previous result
            previous_result = max(previous_results, key=lambda r: r.created_at)

            # Parse previous value
            try:
                previous_value = float(previous_result.value)
            except (TypeError, ValueError):
                logger.debug(
                    f"Cannot parse previous value for delta check: {previous_result.value}"
                )
                return True, None

            # Calculate percentage change
            # Avoid division by zero
            if previous_value == 0:
                if current_value == 0:
                    percent_change = 0.0
                else:
                    # If previous was 0 and current is not, consider it a significant change
                    return (
                        False,
                        f"Value changed from {previous_value} to {current_value} "
                        f"(infinite change from zero)",
                    )
            else:
                percent_change = abs(
                    (current_value - previous_value) / previous_value * 100
                )

            # Check if change exceeds threshold
            if percent_change > settings.delta_check_threshold_percent:
                return (
                    False,
                    f"Value changed by {percent_change:.1f}% "
                    f"(from {previous_value} to {current_value}), "
                    f"exceeds threshold of {settings.delta_check_threshold_percent}%",
                )

            return True, None

        except Exception as e:
            logger.error(f"Error performing delta check: {str(e)}", exc_info=True)
            # On error, fail safe by passing (don't block verification due to technical issues)
            return True, None

    def _apply_rule(
        self,
        rule: VerificationRule,
        result: ResultData,
        tenant_id: str,
        settings: AutoVerificationSettings,
    ) -> tuple[bool, Optional[str]]:
        """
        Apply a single verification rule to a result.

        Args:
            rule: The rule to apply
            result: Result data to check
            tenant_id: Tenant identifier
            settings: Verification settings for the test

        Returns:
            Tuple of (passes, failure_reason)
        """
        # Parse value if needed for numeric checks
        numeric_value = None
        if rule.rule_type in (RuleType.REFERENCE_RANGE, RuleType.CRITICAL_RANGE):
            try:
                numeric_value = float(result.value)
            except (TypeError, ValueError):
                # Non-numeric value for numeric check - cannot verify
                return (
                    False,
                    f"Cannot apply {rule.rule_type.value} check to non-numeric value: {result.value}",
                )

        # Apply the appropriate rule check
        if rule.rule_type == RuleType.REFERENCE_RANGE:
            return self.check_reference_range(numeric_value, settings)

        elif rule.rule_type == RuleType.CRITICAL_RANGE:
            return self.check_critical_range(numeric_value, settings)

        elif rule.rule_type == RuleType.INSTRUMENT_FLAG:
            return self.check_instrument_flags(result.lis_flags, settings)

        elif rule.rule_type == RuleType.DELTA_CHECK:
            return self.check_delta(result, tenant_id, settings)

        else:
            logger.warning(f"Unknown rule type: {rule.rule_type}")
            return True, None  # Unknown rule type - pass by default
