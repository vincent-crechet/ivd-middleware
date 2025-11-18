"""Tenant domain model."""

from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON
from typing import Optional
from datetime import datetime


class Tenant(SQLModel, table=True):
    """
    Represents a laboratory or organization.

    Each tenant operates independently with complete data isolation.
    """

    __tablename__ = "tenants"

    id: Optional[str] = Field(default=None, primary_key=True)
    name: str = Field(index=True, nullable=False, unique=True)
    description: Optional[str] = None
    is_active: bool = Field(default=True, nullable=False)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # LIS Configuration (stored as JSON in database)
    lis_config: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    def update_timestamp(self):
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()
