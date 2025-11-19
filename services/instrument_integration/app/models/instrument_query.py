"""InstrumentQuery domain model for audit logging of host queries."""

from sqlmodel import SQLModel, Field, Index
from typing import Optional
from datetime import datetime
from enum import Enum


class QueryResponseStatus(str, Enum):
    """Status of query response."""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    INVALID_REQUEST = "invalid_request"


class InstrumentQuery(SQLModel, table=True):
    """
    Audit log entry for host queries received from instruments.

    This immutable entity tracks all queries from instruments, including what
    was requested, what was returned, and the outcome for audit purposes.
    """

    __tablename__ = "instrument_queries"
    __table_args__ = (
        Index('ix_instrument_queries_tenant_id', 'tenant_id'),
        Index('ix_instrument_queries_instrument_id', 'instrument_id'),
        Index('ix_instrument_queries_query_timestamp', 'query_timestamp'),
        Index('ix_instrument_queries_tenant_instrument', 'tenant_id', 'instrument_id'),
    )

    id: Optional[str] = Field(default=None, primary_key=True)
    tenant_id: str = Field(foreign_key="tenants.id", index=True, nullable=False)
    instrument_id: str = Field(foreign_key="instruments.id", nullable=False)

    # Query parameters
    query_patient_id: Optional[str] = Field(default=None)
    query_sample_barcode: Optional[str] = Field(default=None)

    # Timing
    query_timestamp: datetime = Field(nullable=False)
    response_timestamp: datetime = Field(nullable=False)
    response_time_ms: int = Field(nullable=False)  # Response time in milliseconds

    # Results
    orders_returned_count: int = Field(default=0, nullable=False)
    response_status: QueryResponseStatus = Field(
        default=QueryResponseStatus.SUCCESS,
        nullable=False
    )
    error_reason: Optional[str] = Field(default=None)

    # Audit
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    def update_timestamp(self):
        """Update timestamp - queries are immutable, so this is a no-op."""
        pass
