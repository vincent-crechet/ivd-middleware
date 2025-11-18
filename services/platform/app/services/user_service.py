"""User management service."""

from typing import Optional
import re
from app.ports import IUserRepository, IPasswordHasher
from app.models import User, UserRole
from app.exceptions import UserNotFoundError, InvalidPasswordError


class UserService:
    """
    Service for user management operations with multi-tenant support.

    Depends only on IUserRepository and IPasswordHasher interfaces.
    """

    def __init__(
        self,
        user_repo: IUserRepository,
        password_hasher: IPasswordHasher
    ):
        """
        Initialize service with dependencies.

        Args:
            user_repo: User repository implementation
            password_hasher: Password hasher implementation
        """
        self._user_repo = user_repo
        self._password_hasher = password_hasher

    def create_user(
        self,
        tenant_id: str,
        email: str,
        password: str,
        name: str,
        role: UserRole = UserRole.TECHNICIAN
    ) -> User:
        """
        Create a new user for a tenant.

        Business Rules:
        - Password must be at least 8 characters
        - Email must be valid format and unique within tenant
        - User must belong to a tenant

        Args:
            tenant_id: Tenant the user belongs to
            email: User email (unique within tenant)
            password: Plain text password
            name: User full name
            role: User role (default: TECHNICIAN)

        Returns:
            Created user (without password hash)

        Raises:
            DuplicateUserError: If email already exists in tenant
            InvalidPasswordError: If password doesn't meet requirements
            ValueError: If email format is invalid
        """
        # Validate email format
        if not self._is_valid_email(email):
            raise ValueError(f"Invalid email format: {email}")

        # Validate password
        if len(password) < 8:
            raise InvalidPasswordError("Password must be at least 8 characters")

        # Hash password
        password_hash = self._password_hasher.hash(password)

        # Create user
        user = User(
            tenant_id=tenant_id,
            email=email.lower().strip(),
            password_hash=password_hash,
            name=name.strip(),
            role=role,
            is_active=True
        )

        created_user = self._user_repo.create(user)

        # Don't return password hash
        created_user.password_hash = ""
        return created_user

    def get_user(self, user_id: str, tenant_id: str) -> User:
        """
        Retrieve a user by ID within tenant.

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier for isolation

        Returns:
            User entity (without password hash)

        Raises:
            UserNotFoundError: If user doesn't exist in tenant
        """
        user = self._user_repo.get_by_id(user_id, tenant_id)
        if not user:
            raise UserNotFoundError(f"User {user_id} not found in tenant")

        # Don't return password hash
        user.password_hash = ""
        return user

    def get_user_by_email(self, email: str, tenant_id: str) -> User:
        """
        Retrieve a user by email within tenant.

        Args:
            email: User email
            tenant_id: Tenant identifier for isolation

        Returns:
            User entity (without password hash)

        Raises:
            UserNotFoundError: If user doesn't exist in tenant
        """
        user = self._user_repo.get_by_email(email.lower(), tenant_id)
        if not user:
            raise UserNotFoundError(f"User with email '{email}' not found in tenant")

        # Don't return password hash
        user.password_hash = ""
        return user

    def list_users(
        self,
        tenant_id: str,
        page: int = 1,
        page_size: int = 20
    ) -> list[User]:
        """
        List users for a tenant with pagination.

        Args:
            tenant_id: Tenant identifier
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            List of users (without password hashes)
        """
        skip = (page - 1) * page_size
        users = self._user_repo.list_by_tenant(tenant_id, skip=skip, limit=page_size)

        # Don't return password hashes
        for user in users:
            user.password_hash = ""

        return users

    def update_user(
        self,
        user_id: str,
        tenant_id: str,
        name: Optional[str] = None,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None
    ) -> User:
        """
        Update user information.

        Args:
            user_id: User to update
            tenant_id: Tenant identifier for isolation
            name: Optional new name
            role: Optional new role
            is_active: Optional new active status

        Returns:
            Updated user (without password hash)

        Raises:
            UserNotFoundError: If user doesn't exist in tenant
        """
        user = self._user_repo.get_by_id(user_id, tenant_id)
        if not user:
            raise UserNotFoundError(f"User {user_id} not found in tenant")

        if name is not None:
            user.name = name.strip()
        if role is not None:
            user.role = role
        if is_active is not None:
            user.is_active = is_active

        updated_user = self._user_repo.update(user)

        # Don't return password hash
        updated_user.password_hash = ""
        return updated_user

    def change_password(
        self,
        user_id: str,
        tenant_id: str,
        new_password: str
    ) -> None:
        """
        Change user password.

        Args:
            user_id: User to update
            tenant_id: Tenant identifier for isolation
            new_password: New plain text password

        Raises:
            UserNotFoundError: If user doesn't exist in tenant
            InvalidPasswordError: If password doesn't meet requirements
        """
        # Validate password
        if len(new_password) < 8:
            raise InvalidPasswordError("Password must be at least 8 characters")

        user = self._user_repo.get_by_id(user_id, tenant_id)
        if not user:
            raise UserNotFoundError(f"User {user_id} not found in tenant")

        # Hash new password
        user.password_hash = self._password_hasher.hash(new_password)

        self._user_repo.update(user)

    def delete_user(self, user_id: str, tenant_id: str) -> None:
        """
        Delete a user.

        Args:
            user_id: User to delete
            tenant_id: Tenant identifier for isolation

        Raises:
            UserNotFoundError: If user doesn't exist in tenant
        """
        if not self._user_repo.delete(user_id, tenant_id):
            raise UserNotFoundError(f"User {user_id} not found in tenant")

    @staticmethod
    def _is_valid_email(email: str) -> bool:
        """
        Validate email format.

        Args:
            email: Email address to validate

        Returns:
            True if valid email format
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
