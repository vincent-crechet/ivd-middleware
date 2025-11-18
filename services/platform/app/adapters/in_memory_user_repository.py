"""In-memory implementation of user repository for testing."""

from typing import Optional
import uuid

from app.ports import IUserRepository
from app.models import User
from app.exceptions import DuplicateUserError, UserNotFoundError


class InMemoryUserRepository(IUserRepository):
    """In-memory implementation with multi-tenant support."""

    def __init__(self):
        """Initialize with empty storage."""
        self._users: dict[str, User] = {}
        # Composite index: (email, tenant_id) -> user_id
        self._email_tenant_index: dict[tuple[str, str], str] = {}

    def create(self, user: User) -> User:
        """Create user in memory."""
        # Validate tenant_id is set
        if not user.tenant_id:
            raise ValueError("User must have a tenant_id")

        # Check for duplicate email within tenant
        key = (user.email, user.tenant_id)
        if key in self._email_tenant_index:
            raise DuplicateUserError(
                f"User with email '{user.email}' already exists in tenant"
            )

        # Generate ID if not provided
        if not user.id:
            user.id = str(uuid.uuid4())

        self._users[user.id] = user
        self._email_tenant_index[key] = user.id
        return user

    def get_by_id(self, user_id: str, tenant_id: str) -> Optional[User]:
        """Get user by ID, ensuring it belongs to tenant."""
        user = self._users.get(user_id)
        if user and user.tenant_id == tenant_id:
            return user
        return None

    def get_by_email(self, email: str, tenant_id: str) -> Optional[User]:
        """Get user by email within tenant."""
        key = (email, tenant_id)
        user_id = self._email_tenant_index.get(key)
        if user_id:
            return self._users.get(user_id)
        return None

    def list_by_tenant(self, tenant_id: str, skip: int = 0, limit: int = 100) -> list[User]:
        """List all users for a tenant."""
        tenant_users = [
            u for u in self._users.values()
            if u.tenant_id == tenant_id
        ]
        return tenant_users[skip:skip + limit]

    def update(self, user: User) -> User:
        """Update user in memory."""
        if user.id not in self._users:
            raise UserNotFoundError(f"User {user.id} not found")

        # Update email index if email changed
        old_user = self._users[user.id]
        if old_user.email != user.email:
            old_key = (old_user.email, old_user.tenant_id)
            new_key = (user.email, user.tenant_id)
            del self._email_tenant_index[old_key]
            self._email_tenant_index[new_key] = user.id

        self._users[user.id] = user
        return user

    def delete(self, user_id: str, tenant_id: str) -> bool:
        """Delete user from memory."""
        user = self.get_by_id(user_id, tenant_id)
        if not user:
            return False

        key = (user.email, user.tenant_id)
        del self._email_tenant_index[key]
        del self._users[user_id]
        return True
