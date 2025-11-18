"""PostgreSQL implementation of user repository."""

from sqlmodel import Session, select
from typing import Optional
import uuid

from app.ports import IUserRepository
from app.models import User
from app.exceptions import DuplicateUserError, UserNotFoundError


class PostgresUserRepository(IUserRepository):
    """PostgreSQL implementation of user repository with multi-tenant support."""

    def __init__(self, session: Session):
        """
        Initialize with database session.

        Args:
            session: SQLModel database session
        """
        self._session = session

    def create(self, user: User) -> User:
        """Create a new user in PostgreSQL."""
        # Validate tenant_id is set
        if not user.tenant_id:
            raise ValueError("User must have a tenant_id")

        # Check for duplicate email within tenant
        existing = self._session.exec(
            select(User).where(
                User.email == user.email,
                User.tenant_id == user.tenant_id
            )
        ).first()

        if existing:
            raise DuplicateUserError(
                f"User with email '{user.email}' already exists in tenant"
            )

        # Generate ID if not provided
        if not user.id:
            user.id = str(uuid.uuid4())

        self._session.add(user)
        self._session.commit()
        self._session.refresh(user)
        return user

    def get_by_id(self, user_id: str, tenant_id: str) -> Optional[User]:
        """Retrieve user by ID, ensuring it belongs to tenant."""
        statement = select(User).where(
            User.id == user_id,
            User.tenant_id == tenant_id
        )
        return self._session.exec(statement).first()

    def get_by_email(self, email: str, tenant_id: str) -> Optional[User]:
        """Retrieve user by email within tenant."""
        statement = select(User).where(
            User.email == email,
            User.tenant_id == tenant_id
        )
        return self._session.exec(statement).first()

    def list_by_tenant(self, tenant_id: str, skip: int = 0, limit: int = 100) -> list[User]:
        """List all users for a tenant."""
        statement = select(User).where(
            User.tenant_id == tenant_id
        ).offset(skip).limit(limit)
        return list(self._session.exec(statement).all())

    def update(self, user: User) -> User:
        """Update existing user."""
        # Use no_autoflush to prevent flushing pending changes to user object
        # before we can filter out immutable fields
        with self._session.no_autoflush:
            existing = self.get_by_id(user.id, user.tenant_id)
            if not existing:
                raise UserNotFoundError(f"User {user.id} not found")

        # Update fields
        for key, value in user.model_dump(exclude_unset=True).items():
            if key not in ['id', 'tenant_id', 'created_at']:  # Don't update immutable fields
                setattr(existing, key, value)

        # Update timestamp
        existing.update_timestamp()

        self._session.add(existing)
        self._session.commit()
        self._session.refresh(existing)
        return existing

    def delete(self, user_id: str, tenant_id: str) -> bool:
        """Delete user, ensuring it belongs to tenant."""
        user = self.get_by_id(user_id, tenant_id)
        if not user:
            return False

        self._session.delete(user)
        self._session.commit()
        return True
