"""LIS Configuration repository port."""

import abc
from typing import Optional
from app.models import LISConfig


class ILISConfigRepository(abc.ABC):
    """
    Port: Abstract contract for LIS configuration persistence with multi-tenant support.

    Each tenant has exactly one LIS configuration (unique constraint).
    """

    @abc.abstractmethod
    def create(self, config: LISConfig) -> LISConfig:
        """
        Create a new LIS configuration for a tenant.

        Args:
            config: LISConfig entity to create (must have tenant_id set)

        Returns:
            Created config with generated ID

        Raises:
            ValueError: If tenant already has a LIS configuration
            ValueError: If config doesn't have tenant_id set
        """
        pass

    @abc.abstractmethod
    def get_by_tenant(self, tenant_id: str) -> Optional[LISConfig]:
        """
        Retrieve LIS configuration for a specific tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            LIS configuration if found, None otherwise
        """
        pass

    @abc.abstractmethod
    def get_by_id(self, config_id: str, tenant_id: str) -> Optional[LISConfig]:
        """
        Retrieve LIS configuration by ID, ensuring it belongs to the tenant.

        Args:
            config_id: Configuration identifier
            tenant_id: Tenant identifier for isolation

        Returns:
            LIS configuration if found and belongs to tenant, None otherwise
        """
        pass

    @abc.abstractmethod
    def get_by_api_key(self, api_key: str) -> Optional[LISConfig]:
        """
        Retrieve LIS configuration by tenant API key (for push model validation).

        Args:
            api_key: Tenant API key (encrypted)

        Returns:
            LIS configuration if found, None otherwise
        """
        pass

    @abc.abstractmethod
    def list_all(self, skip: int = 0, limit: int = 100) -> tuple[list[LISConfig], int]:
        """
        List all LIS configurations (admin only).

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (list of configurations, total count)
        """
        pass

    @abc.abstractmethod
    def list_with_pull_model(self, skip: int = 0, limit: int = 100) -> list[LISConfig]:
        """
        List all LIS configurations using pull model (for background jobs).

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of LIS configurations using pull model
        """
        pass

    @abc.abstractmethod
    def update(self, config: LISConfig) -> LISConfig:
        """
        Update an existing LIS configuration.

        Args:
            config: LISConfig with updated fields

        Returns:
            Updated configuration

        Raises:
            LISConfigNotFoundError: If configuration doesn't exist
        """
        pass

    @abc.abstractmethod
    def delete(self, config_id: str, tenant_id: str) -> bool:
        """
        Delete a LIS configuration, ensuring it belongs to the tenant.

        Args:
            config_id: ID of configuration to delete
            tenant_id: Tenant identifier for isolation

        Returns:
            True if deleted, False if not found
        """
        pass
