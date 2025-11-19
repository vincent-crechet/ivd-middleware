"""Auto-verification settings repository port."""

import abc
from typing import Optional
from app.models import AutoVerificationSettings


class IAutoVerificationSettingsRepository(abc.ABC):
    """
    Port: Abstract contract for auto-verification settings data persistence with multi-tenant support.

    All queries automatically filter by tenant_id to ensure data isolation.
    Settings define the rules and thresholds for automatic result verification per test code.
    """

    @abc.abstractmethod
    def create(self, settings: AutoVerificationSettings) -> AutoVerificationSettings:
        """
        Create new auto-verification settings.

        Args:
            settings: Settings entity to create (must have tenant_id and test_code set)

        Returns:
            Created settings with generated ID

        Raises:
            DuplicateSettingsError: If settings for same tenant_id and test_code already exist
            ValueError: If required fields are missing
        """
        pass

    @abc.abstractmethod
    def get_by_id(self, settings_id: str, tenant_id: str) -> Optional[AutoVerificationSettings]:
        """
        Retrieve settings by ID, ensuring it belongs to the tenant.

        Args:
            settings_id: Unique settings identifier
            tenant_id: Tenant identifier for isolation

        Returns:
            Settings if found and belongs to tenant, None otherwise
        """
        pass

    @abc.abstractmethod
    def get_by_tenant(self, tenant_id: str) -> list[AutoVerificationSettings]:
        """
        List all auto-verification settings for a tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            List of all settings for the tenant
        """
        pass

    @abc.abstractmethod
    def get_by_test_code(self, test_code: str, tenant_id: str) -> Optional[AutoVerificationSettings]:
        """
        Retrieve settings for a specific test code within a tenant.

        Args:
            test_code: Test code identifier (e.g., "GLU", "WBC")
            tenant_id: Tenant identifier for isolation

        Returns:
            Settings for the test code if found in tenant, None otherwise
        """
        pass

    @abc.abstractmethod
    def update(self, settings: AutoVerificationSettings) -> AutoVerificationSettings:
        """
        Update existing auto-verification settings.

        Args:
            settings: Settings with updated fields (must have ID)

        Returns:
            Updated settings

        Raises:
            SettingsNotFoundError: If settings doesn't exist
        """
        pass

    @abc.abstractmethod
    def delete(self, settings_id: str, tenant_id: str) -> bool:
        """
        Delete auto-verification settings, ensuring it belongs to the tenant.

        Args:
            settings_id: ID of settings to delete
            tenant_id: Tenant identifier for isolation

        Returns:
            True if deleted, False if not found
        """
        pass

    @abc.abstractmethod
    def list_all(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[AutoVerificationSettings], int]:
        """
        List all auto-verification settings for a tenant with pagination.

        Args:
            tenant_id: Tenant identifier
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (list of settings, total count)
        """
        pass
