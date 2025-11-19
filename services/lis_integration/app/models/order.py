"""Order domain model for test orders from LIS."""

from sqlmodel import SQLModel, Field, Index
from typing import Optional
from datetime import datetime
from enum import Enum


class OrderStatus(str, Enum):
    """Status of a test order."""
    PENDING = "pending"  # Order received, awaiting instrument processing
    IN_PROGRESS = "in_progress"  # Instrument is processing
    COMPLETED = "completed"  # Results received
    CANCELLED = "cancelled"


class Order(SQLModel, table=True):
    """
    Represents a test order from the LIS that instruments will execute.

    Tracks which tests need to be performed on a sample and their status
    as they flow through the instrument workflow.
    """

    __tablename__ = "orders"
    __table_args__ = (
        Index('ix_orders_tenant_external_lis_order_id', 'tenant_id', 'external_lis_order_id', unique=True),
        Index('ix_orders_sample_id', 'sample_id'),
        Index('ix_orders_status', 'status'),
    )

    id: Optional[str] = Field(default=None, primary_key=True)
    sample_id: str = Field(foreign_key="samples.id", index=True, nullable=False)
    tenant_id: str = Field(foreign_key="tenants.id", index=True, nullable=False)

    # External order identifier from LIS
    external_lis_order_id: str = Field(nullable=False)

    # Test information
    test_code: str = Field(nullable=False)
    test_name: str = Field(nullable=False)

    # Order status
    status: OrderStatus = Field(default=OrderStatus.PENDING, nullable=False)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    def update_timestamp(self):
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()
