"""Unit tests for TenantAdminService (SPEC Feature 1)."""

import pytest
from app.services import TenantAdminService
from app.adapters import (
    InMemoryTenantRepository,
    InMemoryUserRepository,
    BcryptPasswordHasher
)
from app.exceptions import InvalidPasswordError, DuplicateTenantError


class TestTenantAdminService:
    """Test tenant creation with first admin user."""

    @pytest.fixture
    def service(self):
        """Provide TenantAdminService with in-memory adapters."""
        tenant_repo = InMemoryTenantRepository()
        user_repo = InMemoryUserRepository()
        password_hasher = BcryptPasswordHasher()
        return TenantAdminService(tenant_repo, user_repo, password_hasher)

    def test_create_tenant_with_admin_success(self, service):
        """Test successful tenant creation with first admin user."""
        # Act
        result = service.create_tenant_with_admin(
            tenant_name="Test Lab",
            tenant_description="A test laboratory",
            admin_name="John Doe",
            admin_email="john@testlab.com",
            admin_password="password123"
        )

        # Assert
        assert "tenant" in result
        assert "admin_user" in result

        tenant = result["tenant"]
        assert tenant["name"] == "Test Lab"
        assert tenant["description"] == "A test laboratory"
        assert tenant["is_active"] is True
        assert "id" in tenant

        admin = result["admin_user"]
        assert admin["name"] == "John Doe"
        assert admin["email"] == "john@testlab.com"
        assert admin["role"] == "admin"
        assert admin["tenant_id"] == tenant["id"]

    def test_create_tenant_with_admin_invalid_email(self, service):
        """Test that invalid email is rejected."""
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            service.create_tenant_with_admin(
                tenant_name="Test Lab",
                tenant_description=None,
                admin_name="John Doe",
                admin_email="invalid-email",
                admin_password="password123"
            )

        assert "Invalid email format" in str(exc_info.value)

    def test_create_tenant_with_admin_short_password(self, service):
        """Test that short password is rejected."""
        # Act & Assert
        with pytest.raises(InvalidPasswordError) as exc_info:
            service.create_tenant_with_admin(
                tenant_name="Test Lab",
                tenant_description=None,
                admin_name="John Doe",
                admin_email="john@testlab.com",
                admin_password="short"
            )

        assert "at least 8 characters" in str(exc_info.value)

    def test_create_tenant_with_duplicate_name(self, service):
        """Test that duplicate tenant name is rejected."""
        # Arrange - create first tenant
        service.create_tenant_with_admin(
            tenant_name="Test Lab",
            tenant_description=None,
            admin_name="John Doe",
            admin_email="john@testlab.com",
            admin_password="password123"
        )

        # Act & Assert - try to create duplicate
        with pytest.raises(DuplicateTenantError):
            service.create_tenant_with_admin(
                tenant_name="Test Lab",  # Same name
                tenant_description=None,
                admin_name="Jane Smith",
                admin_email="jane@testlab.com",
                admin_password="password123"
            )

    def test_admin_user_has_admin_role(self, service):
        """Test that first user is always an admin."""
        # Act
        result = service.create_tenant_with_admin(
            tenant_name="Test Lab",
            tenant_description=None,
            admin_name="Admin User",
            admin_email="admin@testlab.com",
            admin_password="password123"
        )

        # Assert
        assert result["admin_user"]["role"] == "admin"

    def test_email_normalized_to_lowercase(self, service):
        """Test that email is normalized to lowercase."""
        # Act
        result = service.create_tenant_with_admin(
            tenant_name="Test Lab",
            tenant_description=None,
            admin_name="John Doe",
            admin_email="JOHN@TESTLAB.COM",  # Uppercase
            admin_password="password123"
        )

        # Assert
        assert result["admin_user"]["email"] == "john@testlab.com"  # Lowercase
