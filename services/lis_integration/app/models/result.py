"""Result domain model."""

from sqlmodel import SQLModel, Field, Index
from typing import Optional
from datetime import datetime
from enum import Enum


class ResultStatus(str, Enum):
    """Verification status of a result."""
    PENDING = "pending"
    VERIFIED = "verified"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"


class UploadStatus(str, Enum):
    """Status of uploading result to external LIS."""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    ACKNOWLEDGED = "acknowledged"


class Result(SQLModel, table=True):
    """
    The analytical outcome of a test performed on a sample.

    Includes measured value, reference range, verification status, and
    upload tracking for bidirectional communication with LIS.
    """

    __tablename__ = "results"
    __table_args__ = (
        Index('ix_results_tenant_external_lis_result_id', 'tenant_id', 'external_lis_result_id', unique=True),
        Index('ix_results_sample_id', 'sample_id'),
        Index('ix_results_tenant_status', 'tenant_id', 'verification_status'),
        Index('ix_results_upload_status', 'upload_status'),
    )

    id: Optional[str] = Field(default=None, primary_key=True)
    sample_id: str = Field(foreign_key="samples.id", index=True, nullable=False)
    tenant_id: str = Field(foreign_key="tenants.id", index=True, nullable=False)

    # External source identifier
    external_lis_result_id: str = Field(nullable=False)

    # Test information
    test_code: str = Field(nullable=False)  # e.g., "GLU" for glucose
    test_name: str = Field(nullable=False)
    value: Optional[str] = Field(default=None)  # Can be numeric or text
    unit: Optional[str] = Field(default=None)

    # Reference range
    reference_range_low: Optional[float] = Field(default=None)
    reference_range_high: Optional[float] = Field(default=None)

    # LIS flags (H=High, L=Low, C=Critical, etc.)
    lis_flags: Optional[str] = Field(default=None)

    # Verification status (integration with Verification Service)
    verification_status: ResultStatus = Field(default=ResultStatus.PENDING, nullable=False)
    verification_method: Optional[str] = Field(default=None)  # "auto" or "manual"
    verified_at: Optional[datetime] = Field(default=None)

    # Upload to LIS tracking
    upload_status: UploadStatus = Field(default=UploadStatus.PENDING, nullable=False)
    sent_to_lis_at: Optional[datetime] = Field(default=None)
    last_upload_attempt_at: Optional[datetime] = Field(default=None)
    upload_failure_count: int = Field(default=0, nullable=False)
    upload_failure_reason: Optional[str] = Field(default=None)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    def update_timestamp(self):
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()

    def is_immutable(self) -> bool:
        """Check if result is immutable (verified or rejected)."""
        return self.verification_status in (ResultStatus.VERIFIED, ResultStatus.REJECTED)
