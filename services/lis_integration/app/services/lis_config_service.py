"""LIS Configuration business logic service."""

from typing import Optional
from datetime import datetime
import uuid

from app.models import LISConfig, LISType, IntegrationModel, ConnectionStatus
from app.ports import ILISConfigRepository, ILISAdapter
from app.exceptions import (
    LISConfigNotFoundError,
    LISConfigurationError,
)


class LISConfigService:
    """
    Service for managing LIS configurations with business logic.

    Handles creation, updating, and management of LIS connections
    including authentication credentials and upload settings.
    Depends on ILISConfigRepository and ILISAdapter ports.
    """

    def __init__(
        self,
        config_repo: ILISConfigRepository,
        lis_adapter: ILISAdapter
    ):
        """
        Initialize LIS config service.

        Args:
            config_repo: LIS config repository
            lis_adapter: LIS adapter for connection testing
        """
        self._config_repo = config_repo
        self._lis_adapter = lis_adapter

    def create_configuration(
        self,
        tenant_id: str,
        lis_type: LISType,
        integration_model: IntegrationModel,
        api_endpoint_url: Optional[str] = None,
        api_auth_credentials: Optional[str] = None,
        pull_interval_minutes: int = 5
    ) -> LISConfig:
        """
        Create a new LIS configuration for a tenant.

        Args:
            tenant_id: Tenant identifier
            lis_type: Type of LIS
            integration_model: Push or pull model
            api_endpoint_url: URL for REST API (pull model)
            api_auth_credentials: Encrypted credentials for pull model
            pull_interval_minutes: Minutes between pulls (default: 5)

        Returns:
            Created LIS configuration

        Raises:
            LISConfigurationError: If configuration is invalid
        """
        # Handle MOCK type first (it overrides everything)
        if lis_type == LISType.MOCK:
            integration_model = IntegrationModel.PULL
            api_endpoint_url = "mock://lis"

        # Validate configuration after handling MOCK
        if integration_model == IntegrationModel.PULL and not api_endpoint_url:
            raise LISConfigurationError(
                "Pull model requires api_endpoint_url"
            )

        # Create config
        config = LISConfig(
            tenant_id=tenant_id,
            lis_type=lis_type,
            integration_model=integration_model,
            api_endpoint_url=api_endpoint_url,
            api_auth_credentials=api_auth_credentials,
            tenant_api_key=self._generate_api_key() if integration_model == IntegrationModel.PUSH else None,
            pull_interval_minutes=pull_interval_minutes,
            connection_status=ConnectionStatus.INACTIVE
        )

        return self._config_repo.create(config)

    def get_configuration(self, tenant_id: str) -> Optional[LISConfig]:
        """
        Get LIS configuration for a tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            LIS configuration if found, None otherwise
        """
        return self._config_repo.get_by_tenant(tenant_id)

    def get_configuration_by_api_key(self, api_key: str) -> Optional[LISConfig]:
        """
        Get LIS configuration by API key (for push model authentication).

        Args:
            api_key: Tenant API key

        Returns:
            LIS configuration if found, None otherwise
        """
        return self._config_repo.get_by_api_key(api_key)

    def test_connection(self, tenant_id: str) -> dict:
        """
        Test LIS connection.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Dictionary with connection status

        Raises:
            LISConfigNotFoundError: If tenant has no LIS configuration
        """
        config = self.get_configuration(tenant_id)
        if not config:
            raise LISConfigNotFoundError(f"No LIS configuration for tenant '{tenant_id}'")

        # Test connection via adapter
        status = self._lis_adapter.test_connection()

        # Update config with connection status
        config.connection_status = ConnectionStatus.ACTIVE if status.is_connected else ConnectionStatus.FAILED
        if status.is_connected:
            config.connection_failure_count = 0
        else:
            config.connection_failure_count += 1

        self._config_repo.update(config)

        return {
            "is_connected": status.is_connected,
            "last_tested_at": status.last_tested_at,
            "error_message": status.error_message,
            "details": status.details
        }

    def update_configuration(
        self,
        tenant_id: str,
        lis_type: Optional[LISType] = None,
        integration_model: Optional[IntegrationModel] = None,
        api_endpoint_url: Optional[str] = None,
        api_auth_credentials: Optional[str] = None,
        pull_interval_minutes: Optional[int] = None
    ) -> LISConfig:
        """
        Update LIS configuration.

        Args:
            tenant_id: Tenant identifier
            lis_type: Optional new LIS type
            integration_model: Optional new integration model
            api_endpoint_url: Optional new API endpoint URL
            api_auth_credentials: Optional new credentials
            pull_interval_minutes: Optional new pull interval

        Returns:
            Updated configuration

        Raises:
            LISConfigNotFoundError: If configuration not found
        """
        config = self.get_configuration(tenant_id)
        if not config:
            raise LISConfigNotFoundError(f"No LIS configuration for tenant '{tenant_id}'")

        # Update fields
        if lis_type:
            config.lis_type = lis_type
        if integration_model:
            config.integration_model = integration_model
            # Generate new API key if switching to push model
            if integration_model == IntegrationModel.PUSH and not config.tenant_api_key:
                config.tenant_api_key = self._generate_api_key()
        if api_endpoint_url:
            config.api_endpoint_url = api_endpoint_url
        if api_auth_credentials:
            config.api_auth_credentials = api_auth_credentials
        if pull_interval_minutes:
            config.pull_interval_minutes = pull_interval_minutes

        config.update_timestamp()
        return self._config_repo.update(config)

    def update_upload_settings(
        self,
        tenant_id: str,
        auto_upload_enabled: bool,
        upload_verified_results: bool = True,
        upload_rejected_results: bool = False,
        upload_batch_size: int = 100,
        upload_rate_limit: int = 100
    ) -> LISConfig:
        """
        Update result upload settings.

        Args:
            tenant_id: Tenant identifier
            auto_upload_enabled: Enable automatic upload
            upload_verified_results: Upload verified results
            upload_rejected_results: Upload rejected results
            upload_batch_size: Batch size for uploads
            upload_rate_limit: Max results per minute

        Returns:
            Updated configuration

        Raises:
            LISConfigNotFoundError: If configuration not found
        """
        config = self.get_configuration(tenant_id)
        if not config:
            raise LISConfigNotFoundError(f"No LIS configuration for tenant '{tenant_id}'")

        config.auto_upload_enabled = auto_upload_enabled
        config.upload_verified_results = upload_verified_results
        config.upload_rejected_results = upload_rejected_results
        config.upload_batch_size = upload_batch_size
        config.upload_rate_limit = upload_rate_limit
        config.update_timestamp()

        return self._config_repo.update(config)

    def record_successful_retrieval(self, tenant_id: str) -> LISConfig:
        """
        Record a successful data retrieval (pull model).

        Args:
            tenant_id: Tenant identifier

        Returns:
            Updated configuration
        """
        config = self.get_configuration(tenant_id)
        if not config:
            raise LISConfigNotFoundError(f"No LIS configuration for tenant '{tenant_id}'")

        config.last_successful_retrieval_at = datetime.utcnow()
        config.connection_failure_count = 0
        config.connection_status = ConnectionStatus.ACTIVE
        config.update_timestamp()

        return self._config_repo.update(config)

    def record_retrieval_failure(self, tenant_id: str) -> LISConfig:
        """
        Record a failed data retrieval attempt (pull model).

        Args:
            tenant_id: Tenant identifier

        Returns:
            Updated configuration
        """
        config = self.get_configuration(tenant_id)
        if not config:
            raise LISConfigNotFoundError(f"No LIS configuration for tenant '{tenant_id}'")

        config.connection_failure_count += 1
        if config.connection_failure_count >= 3:
            config.connection_status = ConnectionStatus.FAILED
        else:
            config.connection_status = ConnectionStatus.INACTIVE
        config.update_timestamp()

        return self._config_repo.update(config)

    def record_successful_upload(self, tenant_id: str) -> LISConfig:
        """
        Record a successful upload to LIS.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Updated configuration
        """
        config = self.get_configuration(tenant_id)
        if not config:
            raise LISConfigNotFoundError(f"No LIS configuration for tenant '{tenant_id}'")

        config.last_successful_upload_at = datetime.utcnow()
        config.upload_failure_count = 0
        config.update_timestamp()

        return self._config_repo.update(config)

    def record_upload_failure(self, tenant_id: str) -> LISConfig:
        """
        Record a failed upload to LIS.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Updated configuration
        """
        config = self.get_configuration(tenant_id)
        if not config:
            raise LISConfigNotFoundError(f"No LIS configuration for tenant '{tenant_id}'")

        config.last_upload_failure_at = datetime.utcnow()
        config.upload_failure_count += 1
        config.update_timestamp()

        return self._config_repo.update(config)

    def regenerate_api_key(self, tenant_id: str) -> LISConfig:
        """
        Regenerate API key for push model.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Updated configuration with new API key

        Raises:
            LISConfigNotFoundError: If configuration not found
            LISConfigurationError: If not using push model
        """
        config = self.get_configuration(tenant_id)
        if not config:
            raise LISConfigNotFoundError(f"No LIS configuration for tenant '{tenant_id}'")

        if config.integration_model != IntegrationModel.PUSH:
            raise LISConfigurationError(
                f"Cannot regenerate API key: tenant is using {config.integration_model} model"
            )

        config.tenant_api_key = self._generate_api_key()
        config.update_timestamp()

        return self._config_repo.update(config)

    def delete_configuration(self, tenant_id: str) -> bool:
        """
        Delete LIS configuration.

        Args:
            tenant_id: Tenant identifier

        Returns:
            True if deleted, False if not found
        """
        config = self.get_configuration(tenant_id)
        if not config:
            return False

        return self._config_repo.delete(config.id, tenant_id)

    @staticmethod
    def _generate_api_key() -> str:
        """Generate a new API key (UUID)."""
        return str(uuid.uuid4())
