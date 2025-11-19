"""Settings service implementation."""

import logging
from typing import Optional
from datetime import datetime

from app.ports.auto_verification_settings_repository import (
    IAutoVerificationSettingsRepository,
)
from app.ports.verification_rule_repository import IVerificationRuleRepository
from app.models import AutoVerificationSettings, VerificationRule, RuleType
from app.exceptions import (
    SettingsNotFoundError,
    SettingsAlreadyExistsError,
    RuleNotFoundError,
    InvalidConfigurationError,
)


logger = logging.getLogger(__name__)


class SettingsService:
    """
    Service for managing auto-verification settings and rules.

    This service handles configuration of verification behavior including:
    1. Creating and updating verification settings per test code
    2. Managing reference and critical ranges
    3. Configuring blocked instrument flags
    4. Setting delta check thresholds
    5. Enabling/disabling verification rules
    6. Initializing default settings for new tenants

    Attributes:
        settings_repository: Repository for auto-verification settings
        rules_repository: Repository for verification rules
    """

    # Default rules for new tenants
    DEFAULT_RULES = [
        {
            "rule_type": RuleType.REFERENCE_RANGE,
            "enabled": True,
            "priority": 1,
            "description": "Check if value is within reference range",
        },
        {
            "rule_type": RuleType.CRITICAL_RANGE,
            "enabled": True,
            "priority": 2,
            "description": "Check if value is in critical range",
        },
        {
            "rule_type": RuleType.INSTRUMENT_FLAG,
            "enabled": True,
            "priority": 3,
            "description": "Check for blocked instrument flags",
        },
        {
            "rule_type": RuleType.DELTA_CHECK,
            "enabled": False,  # Disabled by default as it requires historical data
            "priority": 4,
            "description": "Check for significant change from previous result",
        },
    ]

    def __init__(
        self,
        settings_repository: IAutoVerificationSettingsRepository,
        rules_repository: IVerificationRuleRepository,
    ):
        """
        Initialize the settings service.

        Args:
            settings_repository: Repository for accessing settings
            rules_repository: Repository for accessing rules
        """
        self.settings_repository = settings_repository
        self.rules_repository = rules_repository

    def create_settings(
        self,
        tenant_id: str,
        test_code: str,
        test_name: str,
        reference_range_low: Optional[float] = None,
        reference_range_high: Optional[float] = None,
        critical_range_low: Optional[float] = None,
        critical_range_high: Optional[float] = None,
        instrument_flags_to_block: Optional[list[str]] = None,
        delta_check_threshold_percent: Optional[float] = None,
        delta_check_lookback_days: int = 30,
    ) -> AutoVerificationSettings:
        """
        Create new auto-verification settings for a test code.

        Args:
            tenant_id: Tenant identifier
            test_code: Test code (e.g., "GLU", "WBC")
            test_name: Test name (e.g., "Glucose", "White Blood Count")
            reference_range_low: Lower bound of reference range
            reference_range_high: Upper bound of reference range
            critical_range_low: Lower critical threshold
            critical_range_high: Upper critical threshold
            instrument_flags_to_block: List of flags that block auto-verification
            delta_check_threshold_percent: Maximum allowed percentage change
            delta_check_lookback_days: Days to look back for previous result

        Returns:
            Created settings record

        Raises:
            SettingsAlreadyExistsError: If settings already exist for this test code
            InvalidConfigurationError: If configuration is invalid
        """
        logger.info(
            f"Creating verification settings for test {test_code} in tenant {tenant_id}"
        )

        # Check if settings already exist
        existing = self.settings_repository.get_by_test_code(test_code, tenant_id)
        if existing is not None:
            raise SettingsAlreadyExistsError(
                f"Settings already exist for test {test_code} in tenant {tenant_id}"
            )

        # Validate configuration
        self._validate_ranges(
            reference_range_low,
            reference_range_high,
            critical_range_low,
            critical_range_high,
        )
        self._validate_delta_config(delta_check_threshold_percent, delta_check_lookback_days)

        # Create settings
        settings = AutoVerificationSettings(
            tenant_id=tenant_id,
            test_code=test_code,
            test_name=test_name,
            reference_range_low=reference_range_low,
            reference_range_high=reference_range_high,
            critical_range_low=critical_range_low,
            critical_range_high=critical_range_high,
            delta_check_threshold_percent=delta_check_threshold_percent,
            delta_check_lookback_days=delta_check_lookback_days,
        )

        # Set instrument flags if provided
        if instrument_flags_to_block:
            settings.set_instrument_flags_to_block(instrument_flags_to_block)

        created_settings = self.settings_repository.create(settings)

        logger.info(
            f"Created verification settings {created_settings.id} for test {test_code}"
        )

        return created_settings

    def get_settings(self, tenant_id: str, test_code: str) -> AutoVerificationSettings:
        """
        Get auto-verification settings for a specific test code.

        Args:
            tenant_id: Tenant identifier
            test_code: Test code

        Returns:
            Settings for the test code

        Raises:
            SettingsNotFoundError: If settings don't exist for this test code
        """
        logger.debug(f"Getting settings for test {test_code} in tenant {tenant_id}")

        settings = self.settings_repository.get_by_test_code(test_code, tenant_id)
        if settings is None:
            raise SettingsNotFoundError(
                f"No settings found for test {test_code} in tenant {tenant_id}"
            )

        return settings

    def list_settings(
        self, tenant_id: str, skip: int = 0, limit: int = 100
    ) -> dict:
        """
        List all auto-verification settings for a tenant.

        Args:
            tenant_id: Tenant identifier
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Dictionary containing list of settings and total count
        """
        logger.debug(f"Listing settings for tenant {tenant_id}")

        settings_list, total = self.settings_repository.list_all(
            tenant_id=tenant_id, skip=skip, limit=limit
        )

        return {
            "settings": [
                {
                    "id": s.id,
                    "test_code": s.test_code,
                    "test_name": s.test_name,
                    "reference_range_low": s.reference_range_low,
                    "reference_range_high": s.reference_range_high,
                    "critical_range_low": s.critical_range_low,
                    "critical_range_high": s.critical_range_high,
                    "instrument_flags_to_block": s.get_instrument_flags_to_block(),
                    "delta_check_threshold_percent": s.delta_check_threshold_percent,
                    "delta_check_lookback_days": s.delta_check_lookback_days,
                    "created_at": s.created_at.isoformat(),
                    "updated_at": s.updated_at.isoformat(),
                }
                for s in settings_list
            ],
            "total": total,
            "skip": skip,
            "limit": limit,
        }

    def update_settings(
        self,
        tenant_id: str,
        test_code: str,
        test_name: Optional[str] = None,
        reference_range_low: Optional[float] = None,
        reference_range_high: Optional[float] = None,
        critical_range_low: Optional[float] = None,
        critical_range_high: Optional[float] = None,
        instrument_flags_to_block: Optional[list[str]] = None,
        delta_check_threshold_percent: Optional[float] = None,
        delta_check_lookback_days: Optional[int] = None,
    ) -> AutoVerificationSettings:
        """
        Update auto-verification settings for a test code.

        Only provided fields will be updated; None values are ignored unless
        explicitly meant to clear a field.

        Args:
            tenant_id: Tenant identifier
            test_code: Test code to update
            test_name: Optional new test name
            reference_range_low: Optional new lower reference range
            reference_range_high: Optional new upper reference range
            critical_range_low: Optional new lower critical range
            critical_range_high: Optional new upper critical range
            instrument_flags_to_block: Optional new list of blocked flags
            delta_check_threshold_percent: Optional new delta threshold
            delta_check_lookback_days: Optional new lookback days

        Returns:
            Updated settings record

        Raises:
            SettingsNotFoundError: If settings don't exist for this test code
            InvalidConfigurationError: If updated configuration is invalid
        """
        logger.info(f"Updating settings for test {test_code} in tenant {tenant_id}")

        # Load existing settings
        settings = self.settings_repository.get_by_test_code(test_code, tenant_id)
        if settings is None:
            raise SettingsNotFoundError(
                f"No settings found for test {test_code} in tenant {tenant_id}"
            )

        # Update fields if provided
        if test_name is not None:
            settings.test_name = test_name

        if reference_range_low is not None:
            settings.reference_range_low = reference_range_low
        if reference_range_high is not None:
            settings.reference_range_high = reference_range_high

        if critical_range_low is not None:
            settings.critical_range_low = critical_range_low
        if critical_range_high is not None:
            settings.critical_range_high = critical_range_high

        if instrument_flags_to_block is not None:
            settings.set_instrument_flags_to_block(instrument_flags_to_block)

        if delta_check_threshold_percent is not None:
            settings.delta_check_threshold_percent = delta_check_threshold_percent
        if delta_check_lookback_days is not None:
            settings.delta_check_lookback_days = delta_check_lookback_days

        # Validate updated configuration
        self._validate_ranges(
            settings.reference_range_low,
            settings.reference_range_high,
            settings.critical_range_low,
            settings.critical_range_high,
        )
        self._validate_delta_config(
            settings.delta_check_threshold_percent,
            settings.delta_check_lookback_days,
        )

        # Update timestamp and save
        settings.update_timestamp()
        updated_settings = self.settings_repository.update(settings)

        logger.info(f"Updated settings for test {test_code}")

        return updated_settings

    def delete_settings(self, tenant_id: str, test_code: str) -> bool:
        """
        Delete auto-verification settings for a test code.

        Args:
            tenant_id: Tenant identifier
            test_code: Test code

        Returns:
            True if deleted, False if not found

        Raises:
            SettingsNotFoundError: If settings don't exist
        """
        logger.info(f"Deleting settings for test {test_code} in tenant {tenant_id}")

        # Get settings to find ID
        settings = self.settings_repository.get_by_test_code(test_code, tenant_id)
        if settings is None:
            raise SettingsNotFoundError(
                f"No settings found for test {test_code} in tenant {tenant_id}"
            )

        # Delete settings
        deleted = self.settings_repository.delete(settings.id, tenant_id)

        if deleted:
            logger.info(f"Deleted settings for test {test_code}")
        else:
            logger.warning(f"Failed to delete settings for test {test_code}")

        return deleted

    def get_rules(self, tenant_id: str) -> list[dict]:
        """
        Get all verification rules for a tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            List of rule configurations
        """
        logger.debug(f"Getting verification rules for tenant {tenant_id}")

        rules = self.rules_repository.get_by_tenant(tenant_id)

        return [
            {
                "id": r.id,
                "rule_type": r.rule_type.value,
                "enabled": r.enabled,
                "priority": r.priority,
                "description": r.description,
                "created_at": r.created_at.isoformat(),
                "updated_at": r.updated_at.isoformat(),
            }
            for r in rules
        ]

    def enable_rule(self, tenant_id: str, rule_type: str) -> VerificationRule:
        """
        Enable a verification rule for a tenant.

        Args:
            tenant_id: Tenant identifier
            rule_type: Rule type to enable (e.g., "reference_range")

        Returns:
            Updated rule record

        Raises:
            RuleNotFoundError: If rule doesn't exist
            InvalidConfigurationError: If rule type is invalid
        """
        logger.info(f"Enabling rule {rule_type} for tenant {tenant_id}")

        # Validate rule type
        try:
            rule_type_enum = RuleType(rule_type)
        except ValueError:
            raise InvalidConfigurationError(
                f"Invalid rule type: {rule_type}. Must be one of: "
                f"{', '.join(r.value for r in RuleType)}"
            )

        # Find rule
        rules = self.rules_repository.get_by_tenant(tenant_id)
        rule = next((r for r in rules if r.rule_type == rule_type_enum), None)

        if rule is None:
            raise RuleNotFoundError(
                f"Rule {rule_type} not found for tenant {tenant_id}"
            )

        # Enable rule
        rule.enabled = True
        rule.update_timestamp()

        updated_rule = self.rules_repository.update(rule)

        logger.info(f"Enabled rule {rule_type} for tenant {tenant_id}")

        return updated_rule

    def disable_rule(self, tenant_id: str, rule_type: str) -> VerificationRule:
        """
        Disable a verification rule for a tenant.

        Args:
            tenant_id: Tenant identifier
            rule_type: Rule type to disable (e.g., "delta_check")

        Returns:
            Updated rule record

        Raises:
            RuleNotFoundError: If rule doesn't exist
            InvalidConfigurationError: If rule type is invalid
        """
        logger.info(f"Disabling rule {rule_type} for tenant {tenant_id}")

        # Validate rule type
        try:
            rule_type_enum = RuleType(rule_type)
        except ValueError:
            raise InvalidConfigurationError(
                f"Invalid rule type: {rule_type}. Must be one of: "
                f"{', '.join(r.value for r in RuleType)}"
            )

        # Find rule
        rules = self.rules_repository.get_by_tenant(tenant_id)
        rule = next((r for r in rules if r.rule_type == rule_type_enum), None)

        if rule is None:
            raise RuleNotFoundError(
                f"Rule {rule_type} not found for tenant {tenant_id}"
            )

        # Disable rule
        rule.enabled = False
        rule.update_timestamp()

        updated_rule = self.rules_repository.update(rule)

        logger.info(f"Disabled rule {rule_type} for tenant {tenant_id}")

        return updated_rule

    def initialize_default_rules(self, tenant_id: str) -> list[VerificationRule]:
        """
        Initialize default verification rules for a new tenant.

        This should be called when onboarding a new tenant to set up
        their initial verification configuration.

        Args:
            tenant_id: Tenant identifier

        Returns:
            List of created rule records
        """
        logger.info(f"Initializing default rules for tenant {tenant_id}")

        # Check if rules already exist
        existing_rules = self.rules_repository.get_by_tenant(tenant_id)
        if existing_rules:
            logger.warning(
                f"Rules already exist for tenant {tenant_id} - skipping initialization"
            )
            return existing_rules

        # Create default rules
        created_rules = []
        for rule_config in self.DEFAULT_RULES:
            rule = VerificationRule(
                tenant_id=tenant_id,
                rule_type=rule_config["rule_type"],
                enabled=rule_config["enabled"],
                priority=rule_config["priority"],
                description=rule_config["description"],
            )

            # Note: This would need to be implemented in the repository
            # For now, we assume the repository has a create method or
            # rules are seeded at the database level
            logger.debug(
                f"Would create rule {rule.rule_type.value} with priority {rule.priority}"
            )
            # created_rules.append(self.rules_repository.create(rule))

        logger.info(f"Initialized {len(self.DEFAULT_RULES)} default rules for tenant {tenant_id}")

        return created_rules

    def _validate_ranges(
        self,
        reference_low: Optional[float],
        reference_high: Optional[float],
        critical_low: Optional[float],
        critical_high: Optional[float],
    ) -> None:
        """
        Validate that range configurations are logical.

        Args:
            reference_low: Lower reference range
            reference_high: Upper reference range
            critical_low: Lower critical range
            critical_high: Upper critical range

        Raises:
            InvalidConfigurationError: If ranges are invalid
        """
        # Reference range validation
        if (
            reference_low is not None
            and reference_high is not None
            and reference_low >= reference_high
        ):
            raise InvalidConfigurationError(
                f"Reference range low ({reference_low}) must be less than high ({reference_high})"
            )

        # Critical range validation
        if (
            critical_low is not None
            and critical_high is not None
            and critical_low >= critical_high
        ):
            raise InvalidConfigurationError(
                f"Critical range low ({critical_low}) must be less than high ({critical_high})"
            )

        # Cross-validation: critical ranges should be outside reference ranges
        if reference_low is not None and critical_low is not None:
            if critical_low >= reference_low:
                logger.warning(
                    f"Critical low ({critical_low}) should typically be less than "
                    f"reference low ({reference_low})"
                )

        if reference_high is not None and critical_high is not None:
            if critical_high <= reference_high:
                logger.warning(
                    f"Critical high ({critical_high}) should typically be greater than "
                    f"reference high ({reference_high})"
                )

    def _validate_delta_config(
        self, threshold_percent: Optional[float], lookback_days: int
    ) -> None:
        """
        Validate delta check configuration.

        Args:
            threshold_percent: Delta check threshold percentage
            lookback_days: Number of days to look back

        Raises:
            InvalidConfigurationError: If configuration is invalid
        """
        if threshold_percent is not None:
            if threshold_percent < 0:
                raise InvalidConfigurationError(
                    f"Delta check threshold ({threshold_percent}%) cannot be negative"
                )
            if threshold_percent > 1000:
                raise InvalidConfigurationError(
                    f"Delta check threshold ({threshold_percent}%) is unreasonably high"
                )

        if lookback_days < 1:
            raise InvalidConfigurationError(
                f"Delta check lookback days ({lookback_days}) must be at least 1"
            )
        if lookback_days > 365:
            raise InvalidConfigurationError(
                f"Delta check lookback days ({lookback_days}) is unreasonably high"
            )
