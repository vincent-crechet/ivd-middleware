"""Order domain model for test orders from LIS.

This is the canonical Order model used by both LIS Integration and Instrument
Integration services. LIS Integration owns/writes orders, Instrument Integration
reads and updates assignment/status fields.
"""

from sqlmodel import SQLModel, Field, Index
from typing import Optional
from datetime import datetime
from enum import Enum
import json


class OrderStatus(str, Enum):
    """Status of a test order."""
    PENDING = "pending"  # Order received, awaiting instrument processing
    IN_PROGRESS = "in_progress"  # Instrument is processing
    COMPLETED = "completed"  # Results received
    FAILED = "failed"  # Order failed during processing
    CANCELLED = "cancelled"


class OrderPriority(str, Enum):
    """Priority of a test order."""
    ROUTINE = "routine"  # Normal priority
    STAT = "stat"  # Urgent
    CRITICAL = "critical"  # Emergency


class Order(SQLModel, table=True):
    """
    Represents a test order from the LIS that instruments will execute.

    This is the canonical Order model shared between LIS Integration and
    Instrument Integration services:
    - LIS Integration: Creates orders from external LIS systems
    - Instrument Integration: Assigns orders to instruments and tracks execution

    Tracks which tests need to be performed on a sample and their status
    as they flow through the instrument workflow.
    """

    __tablename__ = "orders"
    __table_args__ = (
        Index('ix_orders_tenant_external_lis_order_id', 'tenant_id', 'external_lis_order_id', unique=True),
        Index('ix_orders_sample_id', 'sample_id'),
        Index('ix_orders_status', 'status'),
        Index('ix_orders_tenant_status', 'tenant_id', 'status'),
        Index('ix_orders_instrument_id', 'assigned_instrument_id'),
    )

    id: Optional[str] = Field(default=None, primary_key=True)
    # Note: sample_id references samples table in LIS Integration service
    # FK constraint omitted for cross-service compatibility
    sample_id: str = Field(index=True, nullable=False)
    tenant_id: str = Field(foreign_key="tenants.id", index=True, nullable=False)

    # External order identifier from LIS
    external_lis_order_id: str = Field(nullable=False)

    # Patient information
    patient_id: str = Field(nullable=False)

    # Test information - stored as JSON array for multiple tests per order
    # Example: '["CBC", "BMP", "LFT"]'
    test_codes: str = Field(nullable=False)

    # Priority for instrument processing
    priority: OrderPriority = Field(default=OrderPriority.ROUTINE, nullable=False)

    # Instrument assignment (set by Instrument Integration service)
    # Note: references instruments table in Instrument Integration service
    # FK constraint omitted for cross-service compatibility
    assigned_instrument_id: Optional[str] = Field(
        default=None,
        index=True
    )

    # Order status
    status: OrderStatus = Field(default=OrderStatus.PENDING, nullable=False)

    # Tracking
    created_by: str = Field(default="lis", nullable=False)  # Source: 'lis' or 'manual'

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    assigned_at: Optional[datetime] = Field(default=None)  # When assigned to instrument
    completed_at: Optional[datetime] = Field(default=None)  # When processing completed
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    def update_timestamp(self):
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()

    def get_test_codes_list(self) -> list[str]:
        """Return test_codes as a Python list."""
        try:
            return json.loads(self.test_codes)
        except (json.JSONDecodeError, TypeError):
            # Handle legacy single test code format
            return [self.test_codes] if self.test_codes else []

    def set_test_codes_list(self, codes: list[str]):
        """Set test_codes from a Python list."""
        self.test_codes = json.dumps(codes)

    @staticmethod
    def create_test_codes_json(codes: list[str]) -> str:
        """Create JSON string from list of test codes."""
        return json.dumps(codes)
