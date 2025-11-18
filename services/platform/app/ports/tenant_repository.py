"""Tenant repository port."""

import abc
from typing import Optional
from app.models import Tenant


class ITenantRepository(abc.ABC):
    """
    Port: Abstract contract for tenant data persistence.

    All implementations must provide these methods with the exact same signature.
    """

    @abc.abstractmethod
    def create(self, tenant: Tenant) -> Tenant:
        """
        Create a new tenant.

        Args:
            tenant: Tenant entity to create

        Returns:
            Created tenant with generated ID

        Raises:
            DuplicateTenantError: If tenant with same name exists
        """
        pass

    @abc.abstractmethod
    def get_by_id(self, tenant_id: str) -> Optional[Tenant]:
        """
        Retrieve a tenant by ID.

        Args:
            tenant_id: Unique tenant identifier

        Returns:
            Tenant if found, None otherwise
        """
        pass

    @abc.abstractmethod
    def get_by_name(self, name: str) -> Optional[Tenant]:
        """
        Retrieve a tenant by name.

        Args:
            name: Tenant name

        Returns:
            Tenant if found, None otherwise
        """
        pass

    @abc.abstractmethod
    def list_all(self, skip: int = 0, limit: int = 100) -> list[Tenant]:
        """
        List all tenants with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of tenants
        """
        pass

    @abc.abstractmethod
    def update(self, tenant: Tenant) -> Tenant:
        """
        Update an existing tenant.

        Args:
            tenant: Tenant with updated fields

        Returns:
            Updated tenant

        Raises:
            TenantNotFoundError: If tenant doesn't exist
        """
        pass

    @abc.abstractmethod
    def delete(self, tenant_id: str) -> bool:
        """
        Delete a tenant and all associated data.

        Args:
            tenant_id: ID of tenant to delete

        Returns:
            True if deleted, False if not found
        """
        pass
