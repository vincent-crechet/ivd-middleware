"""Unit tests for SettingsService."""

import pytest
import uuid
from app.services import SettingsService
from app.models import AutoVerificationSettings, VerificationRule, RuleType
from app.ports import (
    IAutoVerificationSettingsRepository,
    IVerificationRuleRepository,
)

TEST_TENANT_ID = "test-tenant-123"


class TestSettingsService:
    """Tests for SettingsService settings management."""

    @pytest.fixture
    def service(
        self,
        auto_verification_settings_repository: IAutoVerificationSettingsRepository,
        verification_rule_repository: IVerificationRuleRepository,
    ):
        """Create a SettingsService with parametrized repositories."""
        return SettingsService(
            settings_repo=auto_verification_settings_repository,
            rule_repo=verification_rule_repository,
        )

    # ========================================================================
    # Settings Creation Tests
    # ========================================================================

    def test_create_settings(self, service):
        """Test creating new verification settings."""
        settings = service.create_settings(
            tenant_id=TEST_TENANT_ID,
            test_code="GLU",
            test_name="Glucose",
            reference_range_low=70.0,
            reference_range_high=100.0,
            critical_range_low=40.0,
            critical_range_high=400.0,
            instrument_flags_to_block=["C", "H"],
            delta_check_threshold_percent=10.0,
            delta_check_lookback_days=30,
        )

        assert settings.tenant_id == TEST_TENANT_ID
        assert settings.test_code == "GLU"
        assert settings.reference_range_low == 70.0
        assert settings.reference_range_high == 100.0

    def test_create_settings_with_invalid_reference_range(self, service):
        """Test that creating settings with invalid reference range fails."""
        with pytest.raises(ValueError):
            service.create_settings(
                tenant_id=TEST_TENANT_ID,
                test_code="GLU",
                test_name="Glucose",
                reference_range_low=100.0,  # High is greater than low
                reference_range_high=70.0,  # This is invalid
                critical_range_low=40.0,
                critical_range_high=400.0,
                instrument_flags_to_block=[],
                delta_check_threshold_percent=10.0,
                delta_check_lookback_days=30,
            )

    def test_create_settings_with_invalid_critical_range(self, service):
        """Test that creating settings with invalid critical range fails."""
        with pytest.raises(ValueError):
            service.create_settings(
                tenant_id=TEST_TENANT_ID,
                test_code="GLU",
                test_name="Glucose",
                reference_range_low=70.0,
                reference_range_high=100.0,
                critical_range_low=400.0,  # High is greater than low
                critical_range_high=40.0,  # This is invalid
                instrument_flags_to_block=[],
                delta_check_threshold_percent=10.0,
                delta_check_lookback_days=30,
            )

    def test_create_settings_with_invalid_delta_threshold(self, service):
        """Test that creating settings with invalid delta threshold fails."""
        with pytest.raises(ValueError):
            service.create_settings(
                tenant_id=TEST_TENANT_ID,
                test_code="GLU",
                test_name="Glucose",
                reference_range_low=70.0,
                reference_range_high=100.0,
                critical_range_low=40.0,
                critical_range_high=400.0,
                instrument_flags_to_block=[],
                delta_check_threshold_percent=-5.0,  # Negative percentage
                delta_check_lookback_days=30,
            )

    # ========================================================================
    # Settings Retrieval Tests
    # ========================================================================

    def test_get_settings_by_test_code(self, service):
        """Test retrieving settings by test code."""
        created = service.create_settings(
            tenant_id=TEST_TENANT_ID,
            test_code="WBC",
            test_name="White Blood Count",
            reference_range_low=4.5,
            reference_range_high=11.0,
            critical_range_low=2.0,
            critical_range_high=30.0,
            instrument_flags_to_block=[],
            delta_check_threshold_percent=15.0,
            delta_check_lookback_days=45,
        )

        retrieved = service.get_settings_by_test_code(TEST_TENANT_ID, "WBC")

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.test_code == "WBC"

    def test_get_settings_by_test_code_nonexistent(self, service):
        """Test retrieving nonexistent settings returns None."""
        result = service.get_settings_by_test_code(TEST_TENANT_ID, "NONEXISTENT")

        assert result is None

    def test_list_settings_for_tenant(self, service):
        """Test listing all settings for a tenant."""
        # Create multiple settings
        service.create_settings(
            tenant_id=TEST_TENANT_ID,
            test_code="GLU",
            test_name="Glucose",
            reference_range_low=70.0,
            reference_range_high=100.0,
            critical_range_low=40.0,
            critical_range_high=400.0,
            instrument_flags_to_block=[],
            delta_check_threshold_percent=10.0,
            delta_check_lookback_days=30,
        )
        service.create_settings(
            tenant_id=TEST_TENANT_ID,
            test_code="WBC",
            test_name="White Blood Count",
            reference_range_low=4.5,
            reference_range_high=11.0,
            critical_range_low=2.0,
            critical_range_high=30.0,
            instrument_flags_to_block=[],
            delta_check_threshold_percent=15.0,
            delta_check_lookback_days=45,
        )

        all_settings = service.list_settings(TEST_TENANT_ID)

        assert len(all_settings) >= 2
        test_codes = {s.test_code for s in all_settings}
        assert "GLU" in test_codes
        assert "WBC" in test_codes

    # ========================================================================
    # Settings Update Tests
    # ========================================================================

    def test_update_settings(self, service):
        """Test updating verification settings."""
        created = service.create_settings(
            tenant_id=TEST_TENANT_ID,
            test_code="NA",
            test_name="Sodium",
            reference_range_low=136.0,
            reference_range_high=145.0,
            critical_range_low=120.0,
            critical_range_high=160.0,
            instrument_flags_to_block=[],
            delta_check_threshold_percent=5.0,
            delta_check_lookback_days=30,
        )

        # Update the settings
        updated = service.update_settings(
            tenant_id=TEST_TENANT_ID,
            test_code="NA",
            reference_range_low=135.0,
            reference_range_high=146.0,
            critical_range_low=120.0,
            critical_range_high=165.0,
            instrument_flags_to_block=["H"],
            delta_check_threshold_percent=6.0,
            delta_check_lookback_days=35,
        )

        assert updated.reference_range_low == 135.0
        assert updated.reference_range_high == 146.0
        assert updated.critical_range_high == 165.0

    # ========================================================================
    # Settings Deletion Tests
    # ========================================================================

    def test_delete_settings(self, service):
        """Test deleting verification settings."""
        created = service.create_settings(
            tenant_id=TEST_TENANT_ID,
            test_code="K",
            test_name="Potassium",
            reference_range_low=3.5,
            reference_range_high=5.0,
            critical_range_low=2.5,
            critical_range_high=6.5,
            instrument_flags_to_block=[],
            delta_check_threshold_percent=15.0,
            delta_check_lookback_days=30,
        )

        service.delete_settings(TEST_TENANT_ID, "K")

        retrieved = service.get_settings_by_test_code(TEST_TENANT_ID, "K")
        assert retrieved is None

    # ========================================================================
    # Rule Management Tests
    # ========================================================================

    def test_get_rules_for_tenant(self, service):
        """Test retrieving all rules for a tenant."""
        service.initialize_default_rules(TEST_TENANT_ID)

        rules = service.get_rules(TEST_TENANT_ID)

        assert len(rules) >= 4  # At least 4 default rule types
        rule_types = {r.rule_type for r in rules}
        assert RuleType.REFERENCE_RANGE in rule_types
        assert RuleType.CRITICAL_RANGE in rule_types

    def test_enable_rule(self, service):
        """Test enabling a rule."""
        service.initialize_default_rules(TEST_TENANT_ID)

        # Disable delta check first
        service.disable_rule(TEST_TENANT_ID, RuleType.DELTA_CHECK)

        # Now enable it
        updated = service.enable_rule(TEST_TENANT_ID, RuleType.DELTA_CHECK)

        assert updated.enabled is True

    def test_disable_rule(self, service):
        """Test disabling a rule."""
        service.initialize_default_rules(TEST_TENANT_ID)

        updated = service.disable_rule(TEST_TENANT_ID, RuleType.DELTA_CHECK)

        assert updated.enabled is False

    def test_get_enabled_rules(self, service):
        """Test retrieving only enabled rules."""
        service.initialize_default_rules(TEST_TENANT_ID)

        # Disable some rules
        service.disable_rule(TEST_TENANT_ID, RuleType.DELTA_CHECK)

        enabled_rules = service.get_enabled_rules(TEST_TENANT_ID)

        # Should have 3 enabled, 1 disabled (delta check)
        enabled_types = {r.rule_type for r in enabled_rules}
        assert RuleType.DELTA_CHECK not in enabled_types
        assert RuleType.REFERENCE_RANGE in enabled_types

    # ========================================================================
    # Default Settings Tests
    # ========================================================================

    def test_initialize_default_rules(self, service):
        """Test initializing default rules for a tenant."""
        service.initialize_default_rules(TEST_TENANT_ID)

        rules = service.get_rules(TEST_TENANT_ID)

        assert len(rules) >= 4
        rule_types = {r.rule_type for r in rules}
        assert RuleType.REFERENCE_RANGE in rule_types
        assert RuleType.CRITICAL_RANGE in rule_types
        assert RuleType.INSTRUMENT_FLAG in rule_types
        assert RuleType.DELTA_CHECK in rule_types

    def test_default_rules_configuration(self, service):
        """Test that default rules have expected configuration."""
        service.initialize_default_rules(TEST_TENANT_ID)

        rules = service.get_rules(TEST_TENANT_ID)

        # Reference range should be enabled
        ref_rule = next(
            (r for r in rules if r.rule_type == RuleType.REFERENCE_RANGE), None
        )
        assert ref_rule is not None
        assert ref_rule.enabled is True

        # Critical range should be enabled
        crit_rule = next(
            (r for r in rules if r.rule_type == RuleType.CRITICAL_RANGE), None
        )
        assert crit_rule is not None
        assert crit_rule.enabled is True

        # Instrument flag should be enabled
        flag_rule = next(
            (r for r in rules if r.rule_type == RuleType.INSTRUMENT_FLAG), None
        )
        assert flag_rule is not None
        assert flag_rule.enabled is True

        # Delta check should be disabled by default
        delta_rule = next(
            (r for r in rules if r.rule_type == RuleType.DELTA_CHECK), None
        )
        assert delta_rule is not None
        assert delta_rule.enabled is False

    # ========================================================================
    # Tenant Isolation Tests
    # ========================================================================

    def test_settings_tenant_isolation(self, service):
        """Test that settings are isolated per tenant."""
        tenant1 = "tenant-1"
        tenant2 = "tenant-2"

        # Create settings for each tenant
        service.create_settings(
            tenant_id=tenant1,
            test_code="GLU",
            test_name="Glucose",
            reference_range_low=70.0,
            reference_range_high=100.0,
            critical_range_low=40.0,
            critical_range_high=400.0,
            instrument_flags_to_block=[],
            delta_check_threshold_percent=10.0,
            delta_check_lookback_days=30,
        )
        service.create_settings(
            tenant_id=tenant2,
            test_code="WBC",
            test_name="White Blood Count",
            reference_range_low=4.5,
            reference_range_high=11.0,
            critical_range_low=2.0,
            critical_range_high=30.0,
            instrument_flags_to_block=[],
            delta_check_threshold_percent=15.0,
            delta_check_lookback_days=45,
        )

        # List for each tenant should return only their settings
        tenant1_settings = service.list_settings(tenant1)
        tenant2_settings = service.list_settings(tenant2)

        assert any(s.test_code == "GLU" for s in tenant1_settings)
        assert any(s.test_code == "WBC" for s in tenant2_settings)
        assert not any(s.test_code == "WBC" for s in tenant1_settings)
