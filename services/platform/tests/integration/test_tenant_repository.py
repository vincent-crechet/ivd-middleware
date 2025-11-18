"""Integration tests for TenantRepository with real database."""

import pytest
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool

from app.adapters import PostgresTenantRepository
from app.models import Tenant
from app.exceptions import DuplicateTenantError, TenantNotFoundError


@pytest.fixture(scope="function")
def db_session():
    """Provide a clean database session for each test."""
    # Use in-memory SQLite for testing
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )

    # Create all tables
    SQLModel.metadata.create_all(engine)

    # Provide session
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def tenant_repo(db_session):
    """Provide PostgreSQL tenant repository with test database."""
    return PostgresTenantRepository(db_session)


class TestPostgresTenantRepository:
    """Integration tests for PostgreSQL Tenant Repository."""

    def test_create_tenant(self, tenant_repo):
        """Test creating a tenant in database."""
        # Arrange
        tenant = Tenant(
            name="Test Laboratory",
            description="A test lab",
            is_active=True
        )

        # Act
        created = tenant_repo.create(tenant)

        # Assert
        assert created.id is not None
        assert created.name == "Test Laboratory"
        assert created.description == "A test lab"
        assert created.is_active is True
        assert created.created_at is not None
        assert created.updated_at is not None

    def test_create_tenant_duplicate_name(self, tenant_repo):
        """Test that duplicate tenant name is rejected by database."""
        # Arrange
        tenant1 = Tenant(name="Test Lab", is_active=True)
        tenant_repo.create(tenant1)

        # Act & Assert
        tenant2 = Tenant(name="Test Lab", is_active=True)
        with pytest.raises(DuplicateTenantError):
            tenant_repo.create(tenant2)

    def test_get_by_id(self, tenant_repo):
        """Test retrieving tenant by ID from database."""
        # Arrange
        tenant = Tenant(name="Test Lab", is_active=True)
        created = tenant_repo.create(tenant)

        # Act
        retrieved = tenant_repo.get_by_id(created.id)

        # Assert
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "Test Lab"

    def test_get_by_id_not_found(self, tenant_repo):
        """Test that getting nonexistent tenant returns None."""
        # Act
        result = tenant_repo.get_by_id("nonexistent-id")

        # Assert
        assert result is None

    def test_get_by_name(self, tenant_repo):
        """Test retrieving tenant by name from database."""
        # Arrange
        tenant = Tenant(name="Test Lab", is_active=True)
        created = tenant_repo.create(tenant)

        # Act
        retrieved = tenant_repo.get_by_name("Test Lab")

        # Assert
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "Test Lab"

    def test_list_all(self, tenant_repo):
        """Test listing tenants with pagination."""
        # Arrange
        for i in range(5):
            tenant = Tenant(name=f"Lab {i}", is_active=True)
            tenant_repo.create(tenant)

        # Act
        page1 = tenant_repo.list_all(skip=0, limit=2)
        page2 = tenant_repo.list_all(skip=2, limit=2)

        # Assert
        assert len(page1) == 2
        assert len(page2) == 2

    def test_update_tenant(self, tenant_repo):
        """Test updating a tenant in database."""
        # Arrange
        tenant = Tenant(name="Old Name", description="Old desc", is_active=True)
        created = tenant_repo.create(tenant)

        # Act
        created.name = "New Name"
        created.description = "New desc"
        updated = tenant_repo.update(created)

        # Assert
        assert updated.name == "New Name"
        assert updated.description == "New desc"

        # Verify persistence
        retrieved = tenant_repo.get_by_id(created.id)
        assert retrieved.name == "New Name"
        assert retrieved.description == "New desc"

    def test_update_timestamp_maintained(self, tenant_repo):
        """Test that updated_at timestamp is maintained."""
        # Arrange
        tenant = Tenant(name="Test Lab", is_active=True)
        created = tenant_repo.create(tenant)
        original_updated_at = created.updated_at

        # Act
        import time
        time.sleep(0.1)  # Ensure time difference
        created.description = "Updated"
        updated = tenant_repo.update(created)

        # Assert
        assert updated.updated_at > original_updated_at

    def test_update_nonexistent_tenant(self, tenant_repo):
        """Test updating nonexistent tenant raises error."""
        # Arrange
        tenant = Tenant(id="nonexistent", name="Test", is_active=True)

        # Act & Assert
        with pytest.raises(TenantNotFoundError):
            tenant_repo.update(tenant)

    def test_delete_tenant(self, tenant_repo):
        """Test deleting a tenant from database."""
        # Arrange
        tenant = Tenant(name="Test Lab", is_active=True)
        created = tenant_repo.create(tenant)

        # Act
        deleted = tenant_repo.delete(created.id)

        # Assert
        assert deleted is True

        # Verify deletion
        retrieved = tenant_repo.get_by_id(created.id)
        assert retrieved is None

    def test_delete_nonexistent_tenant(self, tenant_repo):
        """Test deleting nonexistent tenant returns False."""
        # Act
        deleted = tenant_repo.delete("nonexistent-id")

        # Assert
        assert deleted is False

    def test_immutable_fields_not_updated(self, tenant_repo):
        """Test that immutable fields (id, created_at) are not updated."""
        # Arrange
        tenant = Tenant(name="Test Lab", is_active=True)
        created = tenant_repo.create(tenant)
        original_id = created.id
        original_created_at = created.created_at

        # Act - Create a new Tenant object with same id but trying to change immutable fields
        # This simulates an attempt to update immutable fields
        from datetime import datetime, timedelta
        fake_created_at = datetime.utcnow() - timedelta(days=365)

        update_attempt = Tenant(
            id=original_id,
            name="Updated Lab",
            created_at=fake_created_at,  # Try to change immutable field
            is_active=True
        )
        updated = tenant_repo.update(update_attempt)

        # Assert - immutable fields unchanged, mutable fields updated
        assert updated.id == original_id
        assert updated.created_at == original_created_at  # Should not be fake date
        assert updated.name == "Updated Lab"  # Mutable field should update
