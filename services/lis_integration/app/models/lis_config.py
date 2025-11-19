"""LIS Configuration domain model."""

from sqlmodel import SQLModel, Field, Index
from typing import Optional
from datetime import datetime
from enum import Enum


class LISType(str, Enum):
    """Type of LIS system."""
    MOCK = "mock"
    FILE_UPLOAD = "file_upload"
    REST_API_PUSH = "rest_api_push"
    REST_API_PULL = "rest_api_pull"


class IntegrationModel(str, Enum):
    """Data flow direction for LIS integration."""
    PUSH = "push"  # LIS sends data to middleware
    PULL = "pull"  # Middleware retrieves data from LIS


class ConnectionStatus(str, Enum):
    """Status of LIS connection."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"


class LISConfig(SQLModel, table=True):
    """
    Configuration for connecting to a laboratory's LIS system.

    Supports bidirectional communication with settings for both receiving
    samples/results and sending verified results back to LIS.
    """

    __tablename__ = "lis_configs"
    __table_args__ = (
        Index('ix_lis_configs_tenant_id', 'tenant_id', unique=True),
    )

    id: Optional[str] = Field(default=None, primary_key=True)
    tenant_id: str = Field(foreign_key="tenants.id", index=True, nullable=False)

    # Receive side configuration
    lis_type: LISType = Field(nullable=False)
    integration_model: IntegrationModel = Field(nullable=False)

    # API endpoint for pull model or external LIS REST API
    api_endpoint_url: Optional[str] = Field(default=None)

    # Encrypted credentials for pull model (encrypted at rest in real implementation)
    api_auth_credentials: Optional[str] = Field(default=None)

    # API key for push model (tenant-specific, encrypted at rest)
    tenant_api_key: Optional[str] = Field(default=None)

    # Pull model settings
    pull_interval_minutes: int = Field(default=5, nullable=False)
    last_successful_retrieval_at: Optional[datetime] = Field(default=None)
    connection_status: ConnectionStatus = Field(default=ConnectionStatus.INACTIVE, nullable=False)
    connection_failure_count: int = Field(default=0, nullable=False)

    # Send side configuration (upload to LIS)
    auto_upload_enabled: bool = Field(default=False, nullable=False)
    upload_verified_results: bool = Field(default=True, nullable=False)
    upload_rejected_results: bool = Field(default=False, nullable=False)
    upload_batch_size: int = Field(default=100, nullable=False)
    upload_rate_limit: int = Field(default=100, nullable=False)  # max results per minute

    # Upload tracking
    last_successful_upload_at: Optional[datetime] = Field(default=None)
    last_upload_failure_at: Optional[datetime] = Field(default=None)
    upload_failure_count: int = Field(default=0, nullable=False)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    def update_timestamp(self):
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()
