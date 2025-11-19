"""Auto-verification settings domain model."""

from sqlmodel import SQLModel, Field, Index
from typing import Optional
from datetime import datetime
import json


class AutoVerificationSettings(SQLModel, table=True):
    """
    Configuration for automatic result verification per test code and tenant.

    Defines reference ranges, critical ranges, instrument flags, and delta check thresholds
    that determine which results can be auto-verified.
    """

    __tablename__ = "auto_verification_settings"
    __table_args__ = (
        Index('ix_settings_tenant_test', 'tenant_id', 'test_code', unique=True),
        Index('ix_settings_tenant_id', 'tenant_id'),
    )

    id: Optional[str] = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True, nullable=False)

    # Test identification
    test_code: str = Field(nullable=False)  # e.g., "GLU", "WBC", "HGB"
    test_name: str = Field(nullable=False)  # e.g., "Glucose", "White Blood Count"

    # Reference range (normal values)
    reference_range_low: Optional[float] = Field(default=None)
    reference_range_high: Optional[float] = Field(default=None)

    # Critical range (abnormal/critical values)
    critical_range_low: Optional[float] = Field(default=None)
    critical_range_high: Optional[float] = Field(default=None)

    # Instrument flags that prevent auto-verification
    # Stored as JSON array: ["H", "L", "C", ...]
    instrument_flags_to_block: str = Field(default="[]", nullable=False)

    # Delta check configuration (percentage change from previous result)
    delta_check_threshold_percent: Optional[float] = Field(default=None)
    delta_check_lookback_days: int = Field(default=30, nullable=False)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    def update_timestamp(self):
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()

    def get_instrument_flags_to_block(self) -> list[str]:
        """Parse instrument flags from JSON."""
        try:
            return json.loads(self.instrument_flags_to_block)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_instrument_flags_to_block(self, flags: list[str]):
        """Store instrument flags as JSON."""
        self.instrument_flags_to_block = json.dumps(flags)
