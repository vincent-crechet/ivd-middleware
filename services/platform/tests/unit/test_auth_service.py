"""Unit tests for AuthService."""

import pytest
from app.services import AuthService
from app.adapters import (
    InMemoryUserRepository,
    BcryptPasswordHasher,
    JWTAuthenticationService
)
from app.models import UserRole
from app.exceptions import InvalidCredentialsError


class TestAuthService:
    """Test AuthService business logic."""

    @pytest.fixture
    def service(self):
        """Provide AuthService with in-memory adapters."""
        user_repo = InMemoryUserRepository()
        password_hasher = BcryptPasswordHasher()
        auth_service = JWTAuthenticationService(
            secret_key="test-secret-key",
            algorithm="HS256"
        )
        return AuthService(user_repo, password_hasher, auth_service)

    @pytest.fixture
    def test_user(self, service):
        """Create a test user."""
        from app.models import User

        user = User(
            id="user-123",
            tenant_id="tenant-1",
            email="john@example.com",
            password_hash=service._password_hasher.hash("password123"),
            name="John Doe",
            role=UserRole.TECHNICIAN,
            is_active=True
        )
        service._user_repo.create(user)
        return user

    def test_login_success(self, service, test_user):
        """Test successful login."""
        # Act
        result = service.login(
            email="john@example.com",
            password="password123",
            tenant_id="tenant-1"
        )

        # Assert
        assert "access_token" in result
        assert "token_type" in result
        assert "user" in result
        assert result["token_type"] == "bearer"
        assert result["user"]["id"] == test_user.id
        assert result["user"]["email"] == "john@example.com"
        assert result["user"]["tenant_id"] == "tenant-1"
        assert result["user"]["role"] == "technician"

    def test_login_email_case_insensitive(self, service, test_user):
        """Test that login email is case-insensitive."""
        # Act
        result = service.login(
            email="JOHN@EXAMPLE.COM",  # Uppercase
            password="password123",
            tenant_id="tenant-1"
        )

        # Assert
        assert result["user"]["email"] == "john@example.com"

    def test_login_invalid_email(self, service, test_user):
        """Test login with nonexistent email."""
        # Act & Assert
        with pytest.raises(InvalidCredentialsError) as exc_info:
            service.login(
                email="wrong@example.com",
                password="password123",
                tenant_id="tenant-1"
            )

        assert "Invalid email or password" in str(exc_info.value)

    def test_login_wrong_password(self, service, test_user):
        """Test login with wrong password."""
        # Act & Assert
        with pytest.raises(InvalidCredentialsError) as exc_info:
            service.login(
                email="john@example.com",
                password="wrongpassword",
                tenant_id="tenant-1"
            )

        assert "Invalid email or password" in str(exc_info.value)

    def test_login_wrong_tenant(self, service, test_user):
        """Test login with wrong tenant ID."""
        # Act & Assert
        with pytest.raises(InvalidCredentialsError):
            service.login(
                email="john@example.com",
                password="password123",
                tenant_id="wrong-tenant"
            )

    def test_login_inactive_user(self, service, test_user):
        """Test login with inactive user."""
        # Arrange - deactivate user
        test_user.is_active = False
        service._user_repo.update(test_user)

        # Act & Assert
        with pytest.raises(InvalidCredentialsError) as exc_info:
            service.login(
                email="john@example.com",
                password="password123",
                tenant_id="tenant-1"
            )

        assert "inactive" in str(exc_info.value).lower()

    def test_login_updates_last_login(self, service, test_user):
        """Test that login updates last_login timestamp."""
        # Arrange
        assert test_user.last_login is None

        # Act
        service.login(
            email="john@example.com",
            password="password123",
            tenant_id="tenant-1"
        )

        # Assert - get updated user
        updated_user = service._user_repo.get_by_id(test_user.id, "tenant-1")
        assert updated_user.last_login is not None

    def test_verify_token_valid(self, service, test_user):
        """Test verifying a valid token."""
        # Arrange
        result = service.login(
            email="john@example.com",
            password="password123",
            tenant_id="tenant-1"
        )
        token = result["access_token"]

        # Act
        payload = service.verify_token(token)

        # Assert
        assert payload is not None
        assert payload["sub"] == test_user.id
        assert payload["tenant_id"] == "tenant-1"
        assert payload["role"] == "technician"

    def test_verify_token_invalid(self, service):
        """Test verifying an invalid token."""
        # Act
        payload = service.verify_token("invalid-token")

        # Assert
        assert payload is None

    def test_get_current_user(self, service, test_user):
        """Test getting current user from token."""
        # Arrange
        result = service.login(
            email="john@example.com",
            password="password123",
            tenant_id="tenant-1"
        )
        token = result["access_token"]

        # Act
        user_info = service.get_current_user(token)

        # Assert
        assert user_info["id"] == test_user.id
        assert user_info["email"] == "john@example.com"
        assert user_info["name"] == "John Doe"
        assert user_info["role"] == "technician"
        assert user_info["tenant_id"] == "tenant-1"

    def test_get_current_user_invalid_token(self, service):
        """Test getting current user with invalid token."""
        # Act & Assert
        with pytest.raises(InvalidCredentialsError) as exc_info:
            service.get_current_user("invalid-token")

        assert "Invalid or expired token" in str(exc_info.value)

    def test_token_includes_tenant_context(self, service, test_user):
        """Test that JWT token includes tenant_id for multi-tenancy."""
        # Act
        result = service.login(
            email="john@example.com",
            password="password123",
            tenant_id="tenant-1"
        )

        # Assert
        payload = service.verify_token(result["access_token"])
        assert "tenant_id" in payload
        assert payload["tenant_id"] == "tenant-1"

    def test_token_includes_role(self, service, test_user):
        """Test that JWT token includes user role for authorization."""
        # Act
        result = service.login(
            email="john@example.com",
            password="password123",
            tenant_id="tenant-1"
        )

        # Assert
        payload = service.verify_token(result["access_token"])
        assert "role" in payload
        assert payload["role"] == "technician"
