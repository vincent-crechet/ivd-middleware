"""InstrumentResult domain model for results from instruments.

This model represents the first stage in the result pipeline:
    Instrument → InstrumentResult → Verification → Result → LIS

InstrumentResult captures raw data from analytical instruments before
verification. After verification, the data flows to the Result model
in LIS Integration for upload to external LIS systems.
"""

from sqlmodel import SQLModel, Field, Index
from typing import Optional
from datetime import datetime
from enum import Enum


class InstrumentResultStatus(str, Enum):
    """Status of a result from instrument in the verification pipeline."""
    RECEIVED = "received"  # Just received from instrument
    VALIDATED = "validated"  # Passed basic validation checks
    VERIFICATION_QUEUED = "verification_queued"  # Sent to verification service
    VERIFICATION_COMPLETED = "verification_completed"  # Verification passed
    VERIFICATION_FAILED = "verification_failed"  # Verification failed
    REJECTED = "rejected"  # Result rejected (invalid data, duplicate, etc.)


class InstrumentResult(SQLModel, table=True):
    """
    Test result received from an analytical instrument.

    This is the FIRST stage in the result data flow:

    1. Instrument sends result → InstrumentResult (this model)
    2. Validation checks performed
    3. Sent to Verification service for auto-verification rules
    4. If verified, creates Result in LIS Integration
    5. Result uploaded to external LIS

    Key differences from Result (LIS Integration):
    - Contains instrument-specific fields (instrument_id, instrument_flags)
    - No LIS upload tracking (that's in Result)
    - May be rejected before becoming a Result

    Results are received via REST API from instruments, validated,
    deduplicated, and queued for verification workflow.
    """

    __tablename__ = "instrument_results"
    __table_args__ = (
        Index('ix_instrument_results_tenant_id', 'tenant_id'),
        Index('ix_instrument_results_instrument_id', 'instrument_id'),
        Index('ix_instrument_results_order_id', 'order_id'),
        Index('ix_instrument_results_status', 'status'),
        Index('ix_instrument_results_external_result_id', 'external_instrument_result_id', 'tenant_id', 'instrument_id', unique=True),
    )

    id: Optional[str] = Field(default=None, primary_key=True)
    tenant_id: str = Field(foreign_key="tenants.id", index=True, nullable=False)
    instrument_id: str = Field(foreign_key="instruments.id", nullable=False)
    order_id: Optional[str] = Field(foreign_key="orders.id", default=None)

    # Result identification from instrument
    external_instrument_result_id: str = Field(nullable=False)
    
    # Test information
    test_code: str = Field(nullable=False)
    test_name: str = Field(nullable=False)
    
    # Result value
    value: Optional[str] = Field(default=None)  # Can be numeric or text
    unit: Optional[str] = Field(default=None)
    reference_range_low: Optional[float] = Field(default=None)
    reference_range_high: Optional[float] = Field(default=None)
    
    # Instrument flags
    instrument_flags: Optional[str] = Field(default=None)  # H, L, C, etc.
    
    # Timing
    collection_timestamp: datetime = Field(nullable=False)
    received_timestamp: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    
    # Status and tracking
    status: InstrumentResultStatus = Field(
        default=InstrumentResultStatus.RECEIVED,
        nullable=False
    )
    validation_error: Optional[str] = Field(default=None)
    
    # Audit timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    def update_timestamp(self):
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()
