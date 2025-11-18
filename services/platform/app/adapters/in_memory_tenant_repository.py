"""In-memory implementation of tenant repository for testing."""

from typing import Optional
import uuid

from app.ports import ITenantRepository
from app.models import Tenant
from app.exceptions import DuplicateTenantError, TenantNotFoundError


class InMemoryTenantRepository(ITenantRepository):
    """In-memory implementation for testing."""

    def __init__(self):
        """Initialize with empty storage."""
        self._tenants: dict[str, Tenant] = {}
        self._name_index: dict[str, str] = {}  # name -> tenant_id mapping

    def create(self, tenant: Tenant) -> Tenant:
        """Create tenant in memory."""
        # Check for duplicate name
        if tenant.name in self._name_index:
            raise DuplicateTenantError(f"Tenant with name '{tenant.name}' already exists")

        # Generate ID if not provided
        if not tenant.id:
            tenant.id = str(uuid.uuid4())

        self._tenants[tenant.id] = tenant
        self._name_index[tenant.name] = tenant.id
        return tenant

    def get_by_id(self, tenant_id: str) -> Optional[Tenant]:
        """Get tenant by ID."""
        return self._tenants.get(tenant_id)

    def get_by_name(self, name: str) -> Optional[Tenant]:
        """Get tenant by name."""
        tenant_id = self._name_index.get(name)
        if tenant_id:
            return self._tenants.get(tenant_id)
        return None

    def list_all(self, skip: int = 0, limit: int = 100) -> list[Tenant]:
        """List tenants with pagination."""
        all_tenants = list(self._tenants.values())
        return all_tenants[skip:skip + limit]

    def update(self, tenant: Tenant) -> Tenant:
        """Update tenant in memory."""
        if tenant.id not in self._tenants:
            raise TenantNotFoundError(f"Tenant {tenant.id} not found")

        # Update name index if name changed
        old_tenant = self._tenants[tenant.id]
        if old_tenant.name != tenant.name:
            del self._name_index[old_tenant.name]
            self._name_index[tenant.name] = tenant.id

        self._tenants[tenant.id] = tenant
        return tenant

    def delete(self, tenant_id: str) -> bool:
        """Delete tenant from memory."""
        if tenant_id not in self._tenants:
            return False

        tenant = self._tenants[tenant_id]
        del self._name_index[tenant.name]
        del self._tenants[tenant_id]
        return True
