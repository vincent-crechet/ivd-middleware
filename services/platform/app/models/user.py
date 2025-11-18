"""User domain model."""

from sqlmodel import SQLModel, Field, Index
from typing import Optional
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    """User roles in the system."""
    ADMIN = "admin"
    TECHNICIAN = "technician"
    PATHOLOGIST = "pathologist"


class User(SQLModel, table=True):
    """
    Represents a user with access to the system.

    Each user belongs to exactly one tenant and has a role that determines permissions.
    """

    __tablename__ = "users"
    __table_args__ = (
        Index('ix_users_email_tenant', 'email', 'tenant_id', unique=True),
    )

    id: Optional[str] = Field(default=None, primary_key=True)
    tenant_id: str = Field(foreign_key="tenants.id", index=True, nullable=False)

    # User details
    email: str = Field(nullable=False)  # Uniqueness enforced by composite index
    password_hash: str = Field(nullable=False)
    name: str = Field(nullable=False)
    role: UserRole = Field(default=UserRole.TECHNICIAN, nullable=False)

    # Status
    is_active: bool = Field(default=True, nullable=False)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    last_login: Optional[datetime] = None

    def update_timestamp(self):
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()
