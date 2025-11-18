"""Unit tests for TenantService."""

import pytest
from app.services import TenantService
from app.adapters import InMemoryTenantRepository
from app.exceptions import TenantNotFoundError, DuplicateTenantError


class TestTenantService:
    """Test TenantService business logic."""

    @pytest.fixture
    def service(self):
        """Provide TenantService with in-memory repository."""
        tenant_repo = InMemoryTenantRepository()
        return TenantService(tenant_repo)

    def test_create_tenant_success(self, service):
        """Test creating a tenant with valid data."""
        # Act
        tenant = service.create_tenant(
            name="Test Laboratory",
            description="A test lab"
        )

        # Assert
        assert tenant.id is not None
        assert tenant.name == "Test Laboratory"
        assert tenant.description == "A test lab"
        assert tenant.is_active is True
        assert tenant.created_at is not None
        assert tenant.updated_at is not None

    def test_create_tenant_strips_whitespace(self, service):
        """Test that tenant name is stripped of whitespace."""
        # Act
        tenant = service.create_tenant(
            name="  Test Lab  ",
            description=None
        )

        # Assert
        assert tenant.name == "Test Lab"

    def test_create_tenant_duplicate_name_fails(self, service):
        """Test that duplicate tenant name is rejected."""
        # Arrange
        service.create_tenant(name="Test Lab", description=None)

        # Act & Assert
        with pytest.raises(DuplicateTenantError) as exc_info:
            service.create_tenant(name="Test Lab", description=None)

        assert "already exists" in str(exc_info.value)

    def test_get_tenant_success(self, service):
        """Test retrieving a tenant by ID."""
        # Arrange
        created = service.create_tenant(name="Test Lab", description=None)

        # Act
        tenant = service.get_tenant(created.id)

        # Assert
        assert tenant.id == created.id
        assert tenant.name == "Test Lab"

    def test_get_tenant_not_found(self, service):
        """Test that getting nonexistent tenant raises error."""
        # Act & Assert
        with pytest.raises(TenantNotFoundError) as exc_info:
            service.get_tenant("nonexistent-id")

        assert "not found" in str(exc_info.value)

    def test_get_tenant_by_name_success(self, service):
        """Test retrieving a tenant by name."""
        # Arrange
        created = service.create_tenant(name="Test Lab", description=None)

        # Act
        tenant = service.get_tenant_by_name("Test Lab")

        # Assert
        assert tenant.id == created.id
        assert tenant.name == "Test Lab"

    def test_get_tenant_by_name_not_found(self, service):
        """Test that getting tenant by nonexistent name raises error."""
        # Act & Assert
        with pytest.raises(TenantNotFoundError) as exc_info:
            service.get_tenant_by_name("Nonexistent Lab")

        assert "not found" in str(exc_info.value)

    def test_list_tenants(self, service):
        """Test listing tenants with pagination."""
        # Arrange
        service.create_tenant(name="Lab 1", description=None)
        service.create_tenant(name="Lab 2", description=None)
        service.create_tenant(name="Lab 3", description=None)

        # Act
        tenants = service.list_tenants(page=1, page_size=2)

        # Assert
        assert len(tenants) == 2

    def test_list_tenants_pagination(self, service):
        """Test pagination works correctly."""
        # Arrange
        for i in range(5):
            service.create_tenant(name=f"Lab {i}", description=None)

        # Act
        page1 = service.list_tenants(page=1, page_size=2)
        page2 = service.list_tenants(page=2, page_size=2)
        page3 = service.list_tenants(page=3, page_size=2)

        # Assert
        assert len(page1) == 2
        assert len(page2) == 2
        assert len(page3) == 1

    def test_update_tenant_name(self, service):
        """Test updating tenant name."""
        # Arrange
        tenant = service.create_tenant(name="Old Name", description=None)

        # Act
        updated = service.update_tenant(tenant.id, name="New Name")

        # Assert
        assert updated.name == "New Name"

    def test_update_tenant_description(self, service):
        """Test updating tenant description."""
        # Arrange
        tenant = service.create_tenant(name="Lab", description="Old desc")

        # Act
        updated = service.update_tenant(tenant.id, description="New desc")

        # Assert
        assert updated.description == "New desc"
        assert updated.name == "Lab"  # Unchanged

    def test_update_tenant_is_active(self, service):
        """Test updating tenant active status."""
        # Arrange
        tenant = service.create_tenant(name="Lab", description=None)

        # Act
        updated = service.update_tenant(tenant.id, is_active=False)

        # Assert
        assert updated.is_active is False

    def test_update_tenant_not_found(self, service):
        """Test updating nonexistent tenant raises error."""
        # Act & Assert
        with pytest.raises(TenantNotFoundError):
            service.update_tenant("nonexistent-id", name="New Name")

    def test_deactivate_tenant(self, service):
        """Test deactivating a tenant."""
        # Arrange
        tenant = service.create_tenant(name="Lab", description=None)
        assert tenant.is_active is True

        # Act
        deactivated = service.deactivate_tenant(tenant.id)

        # Assert
        assert deactivated.is_active is False

    def test_delete_tenant_success(self, service):
        """Test deleting a tenant."""
        # Arrange
        tenant = service.create_tenant(name="Lab", description=None)

        # Act
        service.delete_tenant(tenant.id)

        # Assert - should not be found
        with pytest.raises(TenantNotFoundError):
            service.get_tenant(tenant.id)

    def test_delete_tenant_not_found(self, service):
        """Test deleting nonexistent tenant raises error."""
        # Act & Assert
        with pytest.raises(TenantNotFoundError):
            service.delete_tenant("nonexistent-id")
