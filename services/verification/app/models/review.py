"""Review domain model."""

from sqlmodel import SQLModel, Field, Index
from typing import Optional
from datetime import datetime
from enum import Enum


class ReviewState(str, Enum):
    """State of a sample review."""
    PENDING = "pending"  # Sample awaiting assignment
    IN_PROGRESS = "in_progress"  # Sample assigned to a reviewer
    APPROVED = "approved"  # Reviewer confirmed all results are valid
    REJECTED = "rejected"  # Reviewer determined one or more results are invalid
    ESCALATED = "escalated"  # Sent to pathologist for expert review


class ReviewDecision(str, Enum):
    """Overall decision for the review."""
    APPROVE_ALL = "approve_all"  # All flagged results approved
    REJECT_ALL = "reject_all"  # All flagged results rejected
    PARTIAL = "partial"  # Mixed decisions (some approved, some rejected)


class Review(SQLModel, table=True):
    """
    A decision record for a sample with results that failed auto-verification.

    Reviews are performed at the sample level, covering all non-auto-verified results.
    """

    __tablename__ = "reviews"
    __table_args__ = (
        Index('ix_reviews_tenant_id', 'tenant_id'),
        Index('ix_reviews_sample_id', 'sample_id'),
        Index('ix_reviews_state', 'state'),
        Index('ix_reviews_tenant_state', 'tenant_id', 'state'),
    )

    id: Optional[str] = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True, nullable=False)
    sample_id: str = Field(nullable=False)  # References samples table from LIS service

    # Reviewer assignment
    reviewer_user_id: Optional[str] = Field(
        default=None,
        nullable=True
    )

    # Review state and decision
    state: ReviewState = Field(default=ReviewState.PENDING, nullable=False)
    decision: Optional[ReviewDecision] = Field(default=None)

    # Review comments and reasoning
    comments: Optional[str] = Field(default=None)
    escalation_reason: Optional[str] = Field(default=None)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    submitted_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    def update_timestamp(self):
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()


class ResultDecision(SQLModel, table=True):
    """
    Individual decision for each result in a sample review.

    Immutable once submitted.
    """

    __tablename__ = "result_decisions"
    __table_args__ = (
        Index('ix_decisions_review_id', 'review_id'),
        Index('ix_decisions_result_id', 'result_id'),
        Index('ix_decisions_tenant_id', 'tenant_id'),
    )

    id: Optional[str] = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True, nullable=False)
    review_id: str = Field(nullable=False)  # References reviews table
    result_id: str = Field(nullable=False)  # References results table from LIS service

    # Decision
    decision: str = Field(nullable=False)  # "approved" or "rejected"
    comments: Optional[str] = Field(default=None)

    # Timestamp
    decided_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
