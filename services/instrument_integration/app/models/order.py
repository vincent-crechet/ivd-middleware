"""Order domain model for test orders from LIS."""

from sqlmodel import SQLModel, Field, Index
from typing import Optional
from datetime import datetime
from enum import Enum


class OrderStatus(str, Enum):
    """Status of a test order."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OrderPriority(str, Enum):
    """Priority of a test order."""
    ROUTINE = "routine"
    STAT = "stat"
    CRITICAL = "critical"


class Order(SQLModel, table=True):
    """
    A test order from the external LIS that an instrument will execute.

    Orders are created when the LIS Integration Service sends sample/test data
    and are assigned to instruments when they query for pending work.
    """

    __tablename__ = "orders"
    __table_args__ = (
        Index('ix_orders_tenant_id', 'tenant_id'),
        Index('ix_orders_sample_id', 'sample_id'),
        Index('ix_orders_instrument_id', 'assigned_instrument_id'),
        Index('ix_orders_status', 'status'),
        Index('ix_orders_tenant_status', 'tenant_id', 'status'),
        Index('ix_orders_external_lis_order_id', 'external_lis_order_id', 'tenant_id', unique=True),
    )

    id: Optional[str] = Field(default=None, primary_key=True)
    tenant_id: str = Field(foreign_key="tenants.id", index=True, nullable=False)
    sample_id: str = Field(nullable=False)  # References samples from LIS service

    # Order identification
    external_lis_order_id: str = Field(nullable=False)
    patient_id: str = Field(nullable=False)

    # Order content
    test_codes: str = Field(nullable=False)  # CSV or JSON list of test codes
    priority: OrderPriority = Field(default=OrderPriority.ROUTINE, nullable=False)

    # Assignment and status
    assigned_instrument_id: Optional[str] = Field(
        foreign_key="instruments.id",
        default=None
    )
    status: OrderStatus = Field(default=OrderStatus.PENDING, nullable=False)

    # Tracking
    created_by: str = Field(default="lis", nullable=False)  # lis or manual
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    assigned_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    def update_timestamp(self):
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()
