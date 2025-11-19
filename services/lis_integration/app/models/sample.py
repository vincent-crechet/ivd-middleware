"""Sample domain model."""

from sqlmodel import SQLModel, Field, Index
from typing import Optional
from datetime import datetime
from enum import Enum


class SampleStatus(str, Enum):
    """Sample processing status."""
    PENDING = "pending"
    VERIFIED = "verified"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"


class Sample(SQLModel, table=True):
    """
    Represents a physical specimen submitted to the laboratory for testing.

    Contains patient identification and specimen details. Each sample can have
    multiple test results associated with it.
    """

    __tablename__ = "samples"
    __table_args__ = (
        Index('ix_samples_tenant_external_lis_id', 'tenant_id', 'external_lis_id', unique=True),
        Index('ix_samples_tenant_patient_id', 'tenant_id', 'patient_id'),
        Index('ix_samples_tenant_collection_date', 'tenant_id', 'collection_date'),
    )

    id: Optional[str] = Field(default=None, primary_key=True)
    tenant_id: str = Field(foreign_key="tenants.id", index=True, nullable=False)

    # External source identifiers
    external_lis_id: str = Field(nullable=False)  # Uniqueness enforced by composite index

    # Patient identification
    patient_id: str = Field(nullable=False)  # Can be anonymized or direct

    # Specimen details
    specimen_type: str = Field(nullable=False)  # blood, urine, etc.

    # Dates
    collection_date: datetime = Field(nullable=False)
    received_date: datetime = Field(nullable=False)

    # Status tracking
    status: SampleStatus = Field(default=SampleStatus.PENDING, nullable=False)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    def update_timestamp(self):
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()
