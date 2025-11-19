"""Verification rule domain model."""

from sqlmodel import SQLModel, Field, Index
from typing import Optional
from datetime import datetime
from enum import Enum


class RuleType(str, Enum):
    """Types of verification rules."""
    REFERENCE_RANGE = "reference_range"  # Value within normal range?
    CRITICAL_RANGE = "critical_range"  # Value within critical thresholds?
    INSTRUMENT_FLAG = "instrument_flag"  # Result has flag blocking auto-verify?
    DELTA_CHECK = "delta_check"  # Value changed too much from previous?


class VerificationRule(SQLModel, table=True):
    """
    Metadata defining which verification rules are active for a tenant.

    The actual parameters (ranges, thresholds, flags) are in AutoVerificationSettings.
    """

    __tablename__ = "verification_rules"
    __table_args__ = (
        Index('ix_rules_tenant_type', 'tenant_id', 'rule_type', unique=True),
        Index('ix_rules_tenant_id', 'tenant_id'),
    )

    id: Optional[str] = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True, nullable=False)

    # Rule identification
    rule_type: RuleType = Field(nullable=False)
    enabled: bool = Field(default=True, nullable=False)
    priority: int = Field(default=0, nullable=False)  # Evaluation order

    # Description for UI display
    description: Optional[str] = Field(default=None)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    def update_timestamp(self):
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()
