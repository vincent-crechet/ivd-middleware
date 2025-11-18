"""Tenant management service."""

from typing import Optional
from app.ports import ITenantRepository
from app.models import Tenant
from app.exceptions import TenantNotFoundError


class TenantService:
    """
    Service for tenant management operations.

    Depends only on ITenantRepository interface.
    """

    def __init__(self, tenant_repo: ITenantRepository):
        """
        Initialize service with repository.

        Args:
            tenant_repo: Tenant repository implementation (interface)
        """
        self._tenant_repo = tenant_repo

    def create_tenant(
        self,
        name: str,
        description: Optional[str] = None
    ) -> Tenant:
        """
        Create a new tenant.

        Args:
            name: Tenant name (must be unique)
            description: Optional tenant description

        Returns:
            Created tenant

        Raises:
            DuplicateTenantError: If tenant with name already exists
        """
        tenant = Tenant(
            name=name.strip(),
            description=description,
            is_active=True
        )

        return self._tenant_repo.create(tenant)

    def get_tenant(self, tenant_id: str) -> Tenant:
        """
        Retrieve a tenant by ID.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Tenant entity

        Raises:
            TenantNotFoundError: If tenant doesn't exist
        """
        tenant = self._tenant_repo.get_by_id(tenant_id)
        if not tenant:
            raise TenantNotFoundError(f"Tenant {tenant_id} not found")
        return tenant

    def get_tenant_by_name(self, name: str) -> Tenant:
        """
        Retrieve a tenant by name.

        Args:
            name: Tenant name

        Returns:
            Tenant entity

        Raises:
            TenantNotFoundError: If tenant doesn't exist
        """
        tenant = self._tenant_repo.get_by_name(name)
        if not tenant:
            raise TenantNotFoundError(f"Tenant '{name}' not found")
        return tenant

    def list_tenants(self, page: int = 1, page_size: int = 20) -> list[Tenant]:
        """
        List tenants with pagination.

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            List of tenants
        """
        skip = (page - 1) * page_size
        return self._tenant_repo.list_all(skip=skip, limit=page_size)

    def update_tenant(
        self,
        tenant_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Tenant:
        """
        Update tenant information.

        Args:
            tenant_id: Tenant to update
            name: Optional new name
            description: Optional new description
            is_active: Optional new active status

        Returns:
            Updated tenant

        Raises:
            TenantNotFoundError: If tenant doesn't exist
        """
        tenant = self.get_tenant(tenant_id)

        if name is not None:
            tenant.name = name.strip()
        if description is not None:
            tenant.description = description
        if is_active is not None:
            tenant.is_active = is_active

        return self._tenant_repo.update(tenant)

    def deactivate_tenant(self, tenant_id: str) -> Tenant:
        """
        Deactivate a tenant (soft delete).

        Args:
            tenant_id: Tenant to deactivate

        Returns:
            Updated tenant

        Raises:
            TenantNotFoundError: If tenant doesn't exist
        """
        return self.update_tenant(tenant_id, is_active=False)

    def delete_tenant(self, tenant_id: str) -> None:
        """
        Delete a tenant and all associated data.

        Args:
            tenant_id: Tenant to delete

        Raises:
            TenantNotFoundError: If tenant doesn't exist
        """
        if not self._tenant_repo.delete(tenant_id):
            raise TenantNotFoundError(f"Tenant {tenant_id} not found")
