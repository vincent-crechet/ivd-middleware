"""User repository port."""

import abc
from typing import Optional
from app.models import User


class IUserRepository(abc.ABC):
    """
    Port: Abstract contract for user data persistence with multi-tenant support.

    All queries automatically filter by tenant_id to ensure data isolation.
    """

    @abc.abstractmethod
    def create(self, user: User) -> User:
        """
        Create a new user.

        Args:
            user: User entity to create (must have tenant_id set)

        Returns:
            Created user with generated ID

        Raises:
            DuplicateUserError: If user with same email exists in tenant
            ValueError: If user doesn't have tenant_id set
        """
        pass

    @abc.abstractmethod
    def get_by_id(self, user_id: str, tenant_id: str) -> Optional[User]:
        """
        Retrieve a user by ID, ensuring it belongs to the tenant.

        Args:
            user_id: Unique user identifier
            tenant_id: Tenant identifier for isolation

        Returns:
            User if found and belongs to tenant, None otherwise
        """
        pass

    @abc.abstractmethod
    def get_by_email(self, email: str, tenant_id: str) -> Optional[User]:
        """
        Retrieve a user by email within a tenant.

        Args:
            email: User email
            tenant_id: Tenant identifier for isolation

        Returns:
            User if found in tenant, None otherwise
        """
        pass

    @abc.abstractmethod
    def list_by_tenant(self, tenant_id: str, skip: int = 0, limit: int = 100) -> list[User]:
        """
        List all users for a specific tenant.

        Args:
            tenant_id: Tenant identifier
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of users belonging to the tenant
        """
        pass

    @abc.abstractmethod
    def update(self, user: User) -> User:
        """
        Update an existing user.

        Args:
            user: User with updated fields

        Returns:
            Updated user

        Raises:
            UserNotFoundError: If user doesn't exist
        """
        pass

    @abc.abstractmethod
    def delete(self, user_id: str, tenant_id: str) -> bool:
        """
        Delete a user, ensuring it belongs to the tenant.

        Args:
            user_id: ID of user to delete
            tenant_id: Tenant identifier for isolation

        Returns:
            True if deleted, False if not found
        """
        pass
