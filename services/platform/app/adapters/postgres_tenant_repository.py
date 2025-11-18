"""PostgreSQL implementation of tenant repository."""

from sqlmodel import Session, select
from typing import Optional
import uuid

from app.ports import ITenantRepository
from app.models import Tenant
from app.exceptions import DuplicateTenantError, TenantNotFoundError


class PostgresTenantRepository(ITenantRepository):
    """PostgreSQL implementation of tenant repository."""

    def __init__(self, session: Session):
        """
        Initialize with database session.

        Args:
            session: SQLModel database session
        """
        self._session = session

    def create(self, tenant: Tenant) -> Tenant:
        """Create a new tenant in PostgreSQL."""
        # Check for duplicate name
        existing = self._session.exec(
            select(Tenant).where(Tenant.name == tenant.name)
        ).first()

        if existing:
            raise DuplicateTenantError(f"Tenant with name '{tenant.name}' already exists")

        # Generate ID if not provided
        if not tenant.id:
            tenant.id = str(uuid.uuid4())

        self._session.add(tenant)
        self._session.commit()
        self._session.refresh(tenant)
        return tenant

    def get_by_id(self, tenant_id: str) -> Optional[Tenant]:
        """Retrieve tenant by ID from PostgreSQL."""
        statement = select(Tenant).where(Tenant.id == tenant_id)
        return self._session.exec(statement).first()

    def get_by_name(self, name: str) -> Optional[Tenant]:
        """Retrieve tenant by name from PostgreSQL."""
        statement = select(Tenant).where(Tenant.name == name)
        return self._session.exec(statement).first()

    def list_all(self, skip: int = 0, limit: int = 100) -> list[Tenant]:
        """List tenants with pagination."""
        statement = select(Tenant).offset(skip).limit(limit)
        return list(self._session.exec(statement).all())

    def update(self, tenant: Tenant) -> Tenant:
        """Update existing tenant."""
        # Use no_autoflush to prevent flushing pending changes to tenant object
        # before we can filter out immutable fields
        with self._session.no_autoflush:
            existing = self.get_by_id(tenant.id)
            if not existing:
                raise TenantNotFoundError(f"Tenant {tenant.id} not found")

        # Update fields
        for key, value in tenant.model_dump(exclude_unset=True).items():
            if key not in ['id', 'created_at']:  # Don't update immutable fields
                setattr(existing, key, value)

        # Update timestamp
        existing.update_timestamp()

        self._session.add(existing)
        self._session.commit()
        self._session.refresh(existing)
        return existing

    def delete(self, tenant_id: str) -> bool:
        """Delete tenant by ID."""
        tenant = self.get_by_id(tenant_id)
        if not tenant:
            return False

        self._session.delete(tenant)
        self._session.commit()
        return True
