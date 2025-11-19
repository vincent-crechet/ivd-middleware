"""Tests for LISConfigService (shared tests run against in-memory and PostgreSQL)."""

import pytest

from app.models import LISType, IntegrationModel, ConnectionStatus
from app.exceptions import LISConfigNotFoundError, LISConfigurationError


TEST_TENANT_ID = "test-tenant-123"


class TestLISConfigServiceCreateConfiguration:
    """Tests for creating LIS configurations."""

    def test_create_push_configuration(self, lis_config_service):
        """Test creating a push model configuration."""
        config = lis_config_service.create_configuration(
            tenant_id=TEST_TENANT_ID,
            lis_type=LISType.REST_API_PUSH,
            integration_model=IntegrationModel.PUSH
        )

        assert config.tenant_id == TEST_TENANT_ID
        assert config.lis_type == LISType.REST_API_PUSH
        assert config.integration_model == IntegrationModel.PUSH
        assert config.tenant_api_key is not None
        assert config.connection_status == ConnectionStatus.INACTIVE

    def test_create_pull_configuration(self, lis_config_service):
        """Test creating a pull model configuration."""
        config = lis_config_service.create_configuration(
            tenant_id=TEST_TENANT_ID,
            lis_type=LISType.REST_API_PULL,
            integration_model=IntegrationModel.PULL,
            api_endpoint_url="https://lis.example.com/api",
            pull_interval_minutes=10
        )

        assert config.integration_model == IntegrationModel.PULL
        assert config.api_endpoint_url == "https://lis.example.com/api"
        assert config.pull_interval_minutes == 10
        assert config.tenant_api_key is None

    def test_create_pull_configuration_without_url_fails(self, lis_config_service):
        """Test that pull model without API endpoint fails."""
        with pytest.raises(LISConfigurationError):
            lis_config_service.create_configuration(
                tenant_id=TEST_TENANT_ID,
                lis_type=LISType.REST_API_PULL,
                integration_model=IntegrationModel.PULL
                # Missing api_endpoint_url
            )

    def test_create_mock_configuration(self, lis_config_service):
        """Test creating mock LIS configuration."""
        config = lis_config_service.create_configuration(
            tenant_id=TEST_TENANT_ID,
            lis_type=LISType.MOCK,
            integration_model=IntegrationModel.PUSH  # Mock ignores this
        )

        assert config.lis_type == LISType.MOCK
        assert config.integration_model == IntegrationModel.PULL
        assert config.api_endpoint_url == "mock://lis"

    def test_create_duplicate_configuration_fails(self, lis_config_service):
        """Test that tenant can only have one configuration."""
        # Create first config
        lis_config_service.create_configuration(
            tenant_id=TEST_TENANT_ID,
            lis_type=LISType.MOCK,
            integration_model=IntegrationModel.PULL
        )

        # Try to create another (should fail)
        with pytest.raises(ValueError):
            lis_config_service.create_configuration(
                tenant_id=TEST_TENANT_ID,
                lis_type=LISType.REST_API_PUSH,
                integration_model=IntegrationModel.PUSH
            )


class TestLISConfigServiceGetConfiguration:
    """Tests for retrieving configurations."""

    def test_get_configuration_success(self, lis_config_service):
        """Test retrieving configuration by tenant."""
        created = lis_config_service.create_configuration(
            tenant_id=TEST_TENANT_ID,
            lis_type=LISType.MOCK,
            integration_model=IntegrationModel.PULL
        )

        retrieved = lis_config_service.get_configuration(TEST_TENANT_ID)

        assert retrieved is not None
        assert retrieved.id == created.id

    def test_get_configuration_not_found(self, lis_config_service):
        """Test that non-existent configuration returns None."""
        result = lis_config_service.get_configuration("nonexistent-tenant")
        assert result is None

    def test_get_configuration_by_api_key(self, lis_config_service):
        """Test retrieving configuration by API key."""
        created = lis_config_service.create_configuration(
            tenant_id=TEST_TENANT_ID,
            lis_type=LISType.REST_API_PUSH,
            integration_model=IntegrationModel.PUSH
        )

        retrieved = lis_config_service.get_configuration_by_api_key(
            created.tenant_api_key
        )

        assert retrieved is not None
        assert retrieved.id == created.id


class TestLISConfigServiceTestConnection:
    """Tests for testing LIS connection."""

    def test_test_connection_success(self, lis_config_service):
        """Test successful connection test."""
        lis_config_service.create_configuration(
            tenant_id=TEST_TENANT_ID,
            lis_type=LISType.MOCK,
            integration_model=IntegrationModel.PULL
        )

        status = lis_config_service.test_connection(TEST_TENANT_ID)

        assert status["is_connected"] is True
        assert status["last_tested_at"] is not None

    def test_test_connection_not_configured(self, lis_config_service):
        """Test connection test for non-configured tenant."""
        with pytest.raises(LISConfigNotFoundError):
            lis_config_service.test_connection("nonexistent-tenant")


class TestLISConfigServiceUpdateConfiguration:
    """Tests for updating configurations."""

    def test_update_configuration_pull_interval(self, lis_config_service):
        """Test updating pull interval."""
        config = lis_config_service.create_configuration(
            tenant_id=TEST_TENANT_ID,
            lis_type=LISType.MOCK,
            integration_model=IntegrationModel.PULL
        )

        assert config.pull_interval_minutes == 5

        updated = lis_config_service.update_configuration(
            tenant_id=TEST_TENANT_ID,
            pull_interval_minutes=10
        )

        assert updated.pull_interval_minutes == 10

    def test_update_configuration_api_endpoint(self, lis_config_service):
        """Test updating API endpoint."""
        lis_config_service.create_configuration(
            tenant_id=TEST_TENANT_ID,
            lis_type=LISType.REST_API_PULL,
            integration_model=IntegrationModel.PULL,
            api_endpoint_url="https://old.example.com/api"
        )

        updated = lis_config_service.update_configuration(
            tenant_id=TEST_TENANT_ID,
            api_endpoint_url="https://new.example.com/api"
        )

        assert updated.api_endpoint_url == "https://new.example.com/api"

    def test_update_nonexistent_configuration(self, lis_config_service):
        """Test updating non-existent configuration."""
        with pytest.raises(LISConfigNotFoundError):
            lis_config_service.update_configuration(
                tenant_id="nonexistent",
                pull_interval_minutes=10
            )


class TestLISConfigServiceUploadSettings:
    """Tests for managing upload settings."""

    def test_update_upload_settings(self, lis_config_service):
        """Test updating upload settings."""
        config = lis_config_service.create_configuration(
            tenant_id=TEST_TENANT_ID,
            lis_type=LISType.MOCK,
            integration_model=IntegrationModel.PULL
        )

        assert config.auto_upload_enabled is False

        updated = lis_config_service.update_upload_settings(
            tenant_id=TEST_TENANT_ID,
            auto_upload_enabled=True,
            upload_verified_results=True,
            upload_rejected_results=True,
            upload_batch_size=50,
            upload_rate_limit=200
        )

        assert updated.auto_upload_enabled is True
        assert updated.upload_batch_size == 50
        assert updated.upload_rate_limit == 200

    def test_record_successful_retrieval(self, lis_config_service):
        """Test recording successful data retrieval."""
        config = lis_config_service.create_configuration(
            tenant_id=TEST_TENANT_ID,
            lis_type=LISType.MOCK,
            integration_model=IntegrationModel.PULL
        )

        assert config.last_successful_retrieval_at is None

        updated = lis_config_service.record_successful_retrieval(TEST_TENANT_ID)

        assert updated.last_successful_retrieval_at is not None
        assert updated.connection_failure_count == 0
        assert updated.connection_status == ConnectionStatus.ACTIVE

    def test_record_retrieval_failure(self, lis_config_service):
        """Test recording failed data retrieval."""
        lis_config_service.create_configuration(
            tenant_id=TEST_TENANT_ID,
            lis_type=LISType.MOCK,
            integration_model=IntegrationModel.PULL
        )

        # First failure
        updated1 = lis_config_service.record_retrieval_failure(TEST_TENANT_ID)
        assert updated1.connection_failure_count == 1
        assert updated1.connection_status == ConnectionStatus.INACTIVE

        # Second failure
        updated2 = lis_config_service.record_retrieval_failure(TEST_TENANT_ID)
        assert updated2.connection_failure_count == 2

        # Third failure (should transition to FAILED)
        updated3 = lis_config_service.record_retrieval_failure(TEST_TENANT_ID)
        assert updated3.connection_failure_count == 3
        assert updated3.connection_status == ConnectionStatus.FAILED

    def test_record_successful_upload(self, lis_config_service):
        """Test recording successful upload."""
        lis_config_service.create_configuration(
            tenant_id=TEST_TENANT_ID,
            lis_type=LISType.MOCK,
            integration_model=IntegrationModel.PULL
        )

        updated = lis_config_service.record_successful_upload(TEST_TENANT_ID)

        assert updated.last_successful_upload_at is not None
        assert updated.upload_failure_count == 0

    def test_record_upload_failure(self, lis_config_service):
        """Test recording upload failure."""
        lis_config_service.create_configuration(
            tenant_id=TEST_TENANT_ID,
            lis_type=LISType.MOCK,
            integration_model=IntegrationModel.PULL
        )

        updated = lis_config_service.record_upload_failure(TEST_TENANT_ID)

        assert updated.last_upload_failure_at is not None
        assert updated.upload_failure_count == 1


class TestLISConfigServiceAPIKeyManagement:
    """Tests for API key management."""

    def test_regenerate_api_key(self, lis_config_service):
        """Test regenerating API key."""
        config = lis_config_service.create_configuration(
            tenant_id=TEST_TENANT_ID,
            lis_type=LISType.REST_API_PUSH,
            integration_model=IntegrationModel.PUSH
        )

        old_key = config.tenant_api_key

        updated = lis_config_service.regenerate_api_key(TEST_TENANT_ID)

        assert updated.tenant_api_key != old_key
        assert updated.tenant_api_key is not None

    def test_regenerate_api_key_for_pull_fails(self, lis_config_service):
        """Test that regenerating API key for pull model fails."""
        lis_config_service.create_configuration(
            tenant_id=TEST_TENANT_ID,
            lis_type=LISType.MOCK,
            integration_model=IntegrationModel.PULL
        )

        with pytest.raises(LISConfigurationError):
            lis_config_service.regenerate_api_key(TEST_TENANT_ID)


class TestLISConfigServiceDelete:
    """Tests for deleting configurations."""

    def test_delete_configuration_success(self, lis_config_service):
        """Test successful configuration deletion."""
        lis_config_service.create_configuration(
            tenant_id=TEST_TENANT_ID,
            lis_type=LISType.MOCK,
            integration_model=IntegrationModel.PULL
        )

        result = lis_config_service.delete_configuration(TEST_TENANT_ID)

        assert result is True

        # Verify it's deleted
        retrieved = lis_config_service.get_configuration(TEST_TENANT_ID)
        assert retrieved is None

    def test_delete_nonexistent_configuration(self, lis_config_service):
        """Test deleting non-existent configuration."""
        result = lis_config_service.delete_configuration("nonexistent")
        assert result is False
