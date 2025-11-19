"""Shared tests for AutoVerificationSettings repository implementations.

Tests both in-memory and PostgreSQL adapters using parametrized fixtures.
"""

import pytest
import uuid
from app.models import AutoVerificationSettings
from app.ports import IAutoVerificationSettingsRepository

TEST_TENANT_ID = "test-tenant-123"
TEST_TEST_CODE = "GLU"
TEST_TEST_NAME = "Glucose"


class TestAutoVerificationSettingsRepository:
    """Contract tests for IAutoVerificationSettingsRepository."""

    def test_create_settings(self, auto_verification_settings_repository):
        """Test creating new verification settings."""
        repo = auto_verification_settings_repository
        settings = AutoVerificationSettings(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            test_code=TEST_TEST_CODE,
            test_name=TEST_TEST_NAME,
            reference_range_low=70.0,
            reference_range_high=100.0,
            critical_range_low=40.0,
            critical_range_high=400.0,
            instrument_flags_to_block='["C"]',
            delta_check_threshold_percent=10.0,
            delta_check_lookback_days=30,
        )

        created = repo.create(settings)

        assert created.id == settings.id
        assert created.tenant_id == TEST_TENANT_ID
        assert created.test_code == TEST_TEST_CODE
        assert created.reference_range_low == 70.0

    def test_create_duplicate_test_code_per_tenant(self, auto_verification_settings_repository):
        """Test that duplicate test codes per tenant are rejected."""
        repo = auto_verification_settings_repository
        settings1 = AutoVerificationSettings(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            test_code=TEST_TEST_CODE,
            test_name=TEST_TEST_NAME,
            reference_range_low=70.0,
            reference_range_high=100.0,
            critical_range_low=40.0,
            critical_range_high=400.0,
            instrument_flags_to_block='[]',
            delta_check_threshold_percent=10.0,
            delta_check_lookback_days=30,
        )
        repo.create(settings1)

        settings2 = AutoVerificationSettings(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            test_code=TEST_TEST_CODE,  # Duplicate
            test_name="Glucose 2",
            reference_range_low=75.0,
            reference_range_high=105.0,
            critical_range_low=45.0,
            critical_range_high=405.0,
            instrument_flags_to_block='[]',
            delta_check_threshold_percent=12.0,
            delta_check_lookback_days=35,
        )

        # Should raise an error for duplicate (test_code, tenant_id)
        with pytest.raises(Exception):  # Could be IntegrityError or ValueError
            repo.create(settings2)

    def test_get_by_id(self, auto_verification_settings_repository):
        """Test retrieving settings by ID."""
        repo = auto_verification_settings_repository
        settings = AutoVerificationSettings(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            test_code="WBC",
            test_name="White Blood Count",
            reference_range_low=4.5,
            reference_range_high=11.0,
            critical_range_low=2.0,
            critical_range_high=30.0,
            instrument_flags_to_block='[]',
            delta_check_threshold_percent=15.0,
            delta_check_lookback_days=45,
        )
        created = repo.create(settings)

        retrieved = repo.get_by_id(created.id, TEST_TENANT_ID)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.test_code == "WBC"

    def test_get_by_id_wrong_tenant(self, auto_verification_settings_repository):
        """Test that get_by_id enforces tenant isolation."""
        repo = auto_verification_settings_repository
        settings = AutoVerificationSettings(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            test_code="HGB",
            test_name="Hemoglobin",
            reference_range_low=12.0,
            reference_range_high=16.0,
            critical_range_low=7.0,
            critical_range_high=20.0,
            instrument_flags_to_block='[]',
            delta_check_threshold_percent=8.0,
            delta_check_lookback_days=30,
        )
        created = repo.create(settings)

        # Try to get with different tenant
        retrieved = repo.get_by_id(created.id, "other-tenant")

        assert retrieved is None

    def test_get_by_test_code(self, auto_verification_settings_repository):
        """Test retrieving settings by test code."""
        repo = auto_verification_settings_repository
        settings = AutoVerificationSettings(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            test_code="PLT",
            test_name="Platelets",
            reference_range_low=150.0,
            reference_range_high=400.0,
            critical_range_low=50.0,
            critical_range_high=1000.0,
            instrument_flags_to_block='["H", "L"]',
            delta_check_threshold_percent=20.0,
            delta_check_lookback_days=60,
        )
        repo.create(settings)

        retrieved = repo.get_by_test_code("PLT", TEST_TENANT_ID)

        assert retrieved is not None
        assert retrieved.test_code == "PLT"
        assert retrieved.test_name == "Platelets"

    def test_get_by_test_code_nonexistent(self, auto_verification_settings_repository):
        """Test retrieving nonexistent test code returns None."""
        repo = auto_verification_settings_repository

        retrieved = repo.get_by_test_code("NONEXISTENT", TEST_TENANT_ID)

        assert retrieved is None

    def test_update_settings(self, auto_verification_settings_repository):
        """Test updating verification settings."""
        repo = auto_verification_settings_repository
        settings = AutoVerificationSettings(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            test_code="NA",
            test_name="Sodium",
            reference_range_low=136.0,
            reference_range_high=145.0,
            critical_range_low=120.0,
            critical_range_high=160.0,
            instrument_flags_to_block='[]',
            delta_check_threshold_percent=5.0,
            delta_check_lookback_days=30,
        )
        created = repo.create(settings)

        # Update the settings
        created.reference_range_low = 135.0
        created.reference_range_high = 146.0
        created.critical_range_high = 165.0

        updated = repo.update(created)

        assert updated.reference_range_low == 135.0
        assert updated.reference_range_high == 146.0
        assert updated.critical_range_high == 165.0

    def test_delete_settings(self, auto_verification_settings_repository):
        """Test deleting verification settings."""
        repo = auto_verification_settings_repository
        settings = AutoVerificationSettings(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            test_code="K",
            test_name="Potassium",
            reference_range_low=3.5,
            reference_range_high=5.0,
            critical_range_low=2.5,
            critical_range_high=6.5,
            instrument_flags_to_block='[]',
            delta_check_threshold_percent=15.0,
            delta_check_lookback_days=30,
        )
        created = repo.create(settings)

        repo.delete(created.id, TEST_TENANT_ID)

        retrieved = repo.get_by_id(created.id, TEST_TENANT_ID)
        assert retrieved is None

    def test_list_all_by_tenant(self, auto_verification_settings_repository):
        """Test listing all settings for a tenant."""
        repo = auto_verification_settings_repository

        # Create multiple settings
        settings_list = [
            AutoVerificationSettings(
                id=str(uuid.uuid4()),
                tenant_id=TEST_TENANT_ID,
                test_code="GLU",
                test_name="Glucose",
                reference_range_low=70.0,
                reference_range_high=100.0,
                critical_range_low=40.0,
                critical_range_high=400.0,
                instrument_flags_to_block='[]',
                delta_check_threshold_percent=10.0,
                delta_check_lookback_days=30,
            ),
            AutoVerificationSettings(
                id=str(uuid.uuid4()),
                tenant_id=TEST_TENANT_ID,
                test_code="WBC",
                test_name="White Blood Count",
                reference_range_low=4.5,
                reference_range_high=11.0,
                critical_range_low=2.0,
                critical_range_high=30.0,
                instrument_flags_to_block='[]',
                delta_check_threshold_percent=15.0,
                delta_check_lookback_days=45,
            ),
        ]

        for settings in settings_list:
            repo.create(settings)

        # List all for tenant
        all_settings = repo.get_by_tenant(TEST_TENANT_ID)

        assert len(all_settings) == 2
        test_codes = {s.test_code for s in all_settings}
        assert test_codes == {"GLU", "WBC"}

    def test_tenant_isolation_in_list(self, auto_verification_settings_repository):
        """Test that list operations are isolated per tenant."""
        repo = auto_verification_settings_repository
        tenant1 = "tenant-1"
        tenant2 = "tenant-2"

        # Create settings for different tenants
        settings1 = AutoVerificationSettings(
            id=str(uuid.uuid4()),
            tenant_id=tenant1,
            test_code="GLU",
            test_name="Glucose",
            reference_range_low=70.0,
            reference_range_high=100.0,
            critical_range_low=40.0,
            critical_range_high=400.0,
            instrument_flags_to_block='[]',
            delta_check_threshold_percent=10.0,
            delta_check_lookback_days=30,
        )
        settings2 = AutoVerificationSettings(
            id=str(uuid.uuid4()),
            tenant_id=tenant2,
            test_code="WBC",
            test_name="White Blood Count",
            reference_range_low=4.5,
            reference_range_high=11.0,
            critical_range_low=2.0,
            critical_range_high=30.0,
            instrument_flags_to_block='[]',
            delta_check_threshold_percent=15.0,
            delta_check_lookback_days=45,
        )

        repo.create(settings1)
        repo.create(settings2)

        # List for tenant1 should only return tenant1 settings
        tenant1_settings = repo.get_by_tenant(tenant1)
        assert len(tenant1_settings) == 1
        assert tenant1_settings[0].tenant_id == tenant1

        # List for tenant2 should only return tenant2 settings
        tenant2_settings = repo.get_by_tenant(tenant2)
        assert len(tenant2_settings) == 1
        assert tenant2_settings[0].tenant_id == tenant2
