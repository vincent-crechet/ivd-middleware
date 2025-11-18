"""Unit tests for UserService."""

import pytest
from app.services import UserService
from app.adapters import InMemoryUserRepository, BcryptPasswordHasher
from app.models import UserRole
from app.exceptions import UserNotFoundError, DuplicateUserError, InvalidPasswordError


class TestUserService:
    """Test UserService business logic."""

    @pytest.fixture
    def service(self):
        """Provide UserService with in-memory repository and password hasher."""
        user_repo = InMemoryUserRepository()
        password_hasher = BcryptPasswordHasher()
        return UserService(user_repo, password_hasher)

    def test_create_user_success(self, service):
        """Test creating a user with valid data."""
        # Act
        user = service.create_user(
            tenant_id="tenant-1",
            email="john@example.com",
            password="password123",
            name="John Doe",
            role=UserRole.TECHNICIAN
        )

        # Assert
        assert user.id is not None
        assert user.email == "john@example.com"
        assert user.name == "John Doe"
        assert user.role == UserRole.TECHNICIAN
        assert user.tenant_id == "tenant-1"
        assert user.is_active is True
        assert user.password_hash == ""  # Shouldn't be returned

    def test_create_user_email_normalized(self, service):
        """Test that email is normalized to lowercase."""
        # Act
        user = service.create_user(
            tenant_id="tenant-1",
            email="JOHN@EXAMPLE.COM",
            password="password123",
            name="John Doe"
        )

        # Assert
        assert user.email == "john@example.com"

    def test_create_user_invalid_email(self, service):
        """Test that invalid email is rejected."""
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            service.create_user(
                tenant_id="tenant-1",
                email="invalid-email",
                password="password123",
                name="John Doe"
            )

        assert "Invalid email format" in str(exc_info.value)

    def test_create_user_short_password(self, service):
        """Test that short password is rejected."""
        # Act & Assert
        with pytest.raises(InvalidPasswordError) as exc_info:
            service.create_user(
                tenant_id="tenant-1",
                email="john@example.com",
                password="short",
                name="John Doe"
            )

        assert "at least 8 characters" in str(exc_info.value)

    def test_create_user_duplicate_email_same_tenant(self, service):
        """Test that duplicate email in same tenant is rejected."""
        # Arrange
        service.create_user(
            tenant_id="tenant-1",
            email="john@example.com",
            password="password123",
            name="John Doe"
        )

        # Act & Assert
        with pytest.raises(DuplicateUserError) as exc_info:
            service.create_user(
                tenant_id="tenant-1",
                email="john@example.com",
                password="password123",
                name="John Smith"
            )

        assert "already exists" in str(exc_info.value)

    def test_create_user_same_email_different_tenant(self, service):
        """Test that same email in different tenant is allowed."""
        # Arrange
        user1 = service.create_user(
            tenant_id="tenant-1",
            email="john@example.com",
            password="password123",
            name="John Doe"
        )

        # Act - same email, different tenant
        user2 = service.create_user(
            tenant_id="tenant-2",
            email="john@example.com",
            password="password123",
            name="John Smith"
        )

        # Assert
        assert user1.id != user2.id
        assert user1.email == user2.email
        assert user1.tenant_id != user2.tenant_id

    def test_get_user_success(self, service):
        """Test retrieving a user by ID."""
        # Arrange
        created = service.create_user(
            tenant_id="tenant-1",
            email="john@example.com",
            password="password123",
            name="John Doe"
        )

        # Act
        user = service.get_user(created.id, "tenant-1")

        # Assert
        assert user.id == created.id
        assert user.email == "john@example.com"

    def test_get_user_wrong_tenant(self, service):
        """Test that getting user from wrong tenant fails."""
        # Arrange
        created = service.create_user(
            tenant_id="tenant-1",
            email="john@example.com",
            password="password123",
            name="John Doe"
        )

        # Act & Assert
        with pytest.raises(UserNotFoundError):
            service.get_user(created.id, "tenant-2")  # Wrong tenant

    def test_get_user_by_email_success(self, service):
        """Test retrieving user by email."""
        # Arrange
        created = service.create_user(
            tenant_id="tenant-1",
            email="john@example.com",
            password="password123",
            name="John Doe"
        )

        # Act
        user = service.get_user_by_email("john@example.com", "tenant-1")

        # Assert
        assert user.id == created.id
        assert user.email == "john@example.com"

    def test_get_user_by_email_case_insensitive(self, service):
        """Test that email lookup is case-insensitive."""
        # Arrange
        created = service.create_user(
            tenant_id="tenant-1",
            email="john@example.com",
            password="password123",
            name="John Doe"
        )

        # Act
        user = service.get_user_by_email("JOHN@EXAMPLE.COM", "tenant-1")

        # Assert
        assert user.id == created.id

    def test_list_users(self, service):
        """Test listing users for a tenant."""
        # Arrange
        service.create_user("tenant-1", "user1@example.com", "password123", "User 1")
        service.create_user("tenant-1", "user2@example.com", "password123", "User 2")
        service.create_user("tenant-2", "user3@example.com", "password123", "User 3")

        # Act
        users = service.list_users("tenant-1")

        # Assert
        assert len(users) == 2
        assert all(u.tenant_id == "tenant-1" for u in users)

    def test_update_user_name(self, service):
        """Test updating user name."""
        # Arrange
        user = service.create_user(
            tenant_id="tenant-1",
            email="john@example.com",
            password="password123",
            name="Old Name"
        )

        # Act
        updated = service.update_user(user.id, "tenant-1", name="New Name")

        # Assert
        assert updated.name == "New Name"

    def test_update_user_role(self, service):
        """Test updating user role."""
        # Arrange
        user = service.create_user(
            tenant_id="tenant-1",
            email="john@example.com",
            password="password123",
            name="John Doe",
            role=UserRole.TECHNICIAN
        )

        # Act
        updated = service.update_user(user.id, "tenant-1", role=UserRole.ADMIN)

        # Assert
        assert updated.role == UserRole.ADMIN

    def test_update_user_is_active(self, service):
        """Test updating user active status."""
        # Arrange
        user = service.create_user(
            tenant_id="tenant-1",
            email="john@example.com",
            password="password123",
            name="John Doe"
        )

        # Act
        updated = service.update_user(user.id, "tenant-1", is_active=False)

        # Assert
        assert updated.is_active is False

    def test_change_password_success(self, service):
        """Test changing user password."""
        # Arrange
        user = service.create_user(
            tenant_id="tenant-1",
            email="john@example.com",
            password="oldpassword123",
            name="John Doe"
        )

        # Act - should not raise
        service.change_password(user.id, "tenant-1", "newpassword123")

    def test_change_password_too_short(self, service):
        """Test that short new password is rejected."""
        # Arrange
        user = service.create_user(
            tenant_id="tenant-1",
            email="john@example.com",
            password="password123",
            name="John Doe"
        )

        # Act & Assert
        with pytest.raises(InvalidPasswordError):
            service.change_password(user.id, "tenant-1", "short")

    def test_delete_user_success(self, service):
        """Test deleting a user."""
        # Arrange
        user = service.create_user(
            tenant_id="tenant-1",
            email="john@example.com",
            password="password123",
            name="John Doe"
        )

        # Act
        service.delete_user(user.id, "tenant-1")

        # Assert
        with pytest.raises(UserNotFoundError):
            service.get_user(user.id, "tenant-1")

    def test_delete_user_wrong_tenant(self, service):
        """Test deleting user from wrong tenant fails."""
        # Arrange
        user = service.create_user(
            tenant_id="tenant-1",
            email="john@example.com",
            password="password123",
            name="John Doe"
        )

        # Act & Assert
        with pytest.raises(UserNotFoundError):
            service.delete_user(user.id, "tenant-2")  # Wrong tenant
