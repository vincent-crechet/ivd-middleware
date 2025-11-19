"""Instrument domain model."""

from sqlmodel import SQLModel, Field, Index
from typing import Optional
from datetime import datetime
from enum import Enum


class InstrumentType(str, Enum):
    """Type of analytical instrument."""
    HEMATOLOGY = "hematology"
    CHEMISTRY = "chemistry"
    IMMUNOASSAY = "immunoassay"
    COAGULATION = "coagulation"
    URINALYSIS = "urinalysis"
    OTHER = "other"


class InstrumentStatus(str, Enum):
    """Connection status of an instrument."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISCONNECTED = "disconnected"
    MAINTENANCE = "maintenance"


class Instrument(SQLModel, table=True):
    """
    Configuration for an analytical instrument connected to the middleware.

    Instruments are registered by lab administrators and communicate with the
    middleware via HTTP REST APIs using unique API tokens for authentication.
    """

    __tablename__ = "instruments"
    __table_args__ = (
        Index('ix_instruments_tenant_id', 'tenant_id'),
        Index('ix_instruments_api_token', 'api_token', unique=True),
        Index('ix_instruments_tenant_name', 'tenant_id', 'name', unique=True),
    )

    id: Optional[str] = Field(default=None, primary_key=True)
    tenant_id: str = Field(foreign_key="tenants.id", index=True, nullable=False)

    # Identification
    name: str = Field(nullable=False)
    instrument_type: InstrumentType = Field(nullable=False)

    # Authentication
    api_token: str = Field(nullable=False, unique=True)
    api_token_created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Status tracking
    status: InstrumentStatus = Field(default=InstrumentStatus.INACTIVE, nullable=False)
    last_successful_query_at: Optional[datetime] = Field(default=None)
    last_successful_result_at: Optional[datetime] = Field(default=None)
    connection_failure_count: int = Field(default=0, nullable=False)
    last_failure_at: Optional[datetime] = Field(default=None)
    last_failure_reason: Optional[str] = Field(default=None)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    def update_timestamp(self):
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()
