"""PostgreSQL implementation of LIS config repository."""

from sqlmodel import Session, select
from typing import Optional
import uuid

from app.ports import ILISConfigRepository
from app.models import LISConfig, IntegrationModel
from app.exceptions import LISConfigNotFoundError


class PostgresLISConfigRepository(ILISConfigRepository):
    """PostgreSQL implementation of LIS config repository with multi-tenant support."""

    def __init__(self, session: Session):
        """
        Initialize with database session.

        Args:
            session: SQLModel database session
        """
        self._session = session

    def create(self, config: LISConfig) -> LISConfig:
        """Create a new LIS configuration for a tenant."""
        # Validate tenant_id is set
        if not config.tenant_id:
            raise ValueError("LISConfig must have a tenant_id")

        # Check if tenant already has a configuration
        existing = self._session.exec(
            select(LISConfig).where(LISConfig.tenant_id == config.tenant_id)
        ).first()

        if existing:
            raise ValueError(f"Tenant '{config.tenant_id}' already has a LIS configuration")

        # Generate ID if not provided
        if not config.id:
            config.id = str(uuid.uuid4())

        self._session.add(config)
        self._session.commit()
        self._session.refresh(config)
        return config

    def get_by_tenant(self, tenant_id: str) -> Optional[LISConfig]:
        """Retrieve LIS configuration for a specific tenant."""
        statement = select(LISConfig).where(LISConfig.tenant_id == tenant_id)
        return self._session.exec(statement).first()

    def get_by_id(self, config_id: str, tenant_id: str) -> Optional[LISConfig]:
        """Retrieve LIS configuration by ID, ensuring it belongs to the tenant."""
        statement = select(LISConfig).where(
            LISConfig.id == config_id,
            LISConfig.tenant_id == tenant_id
        )
        return self._session.exec(statement).first()

    def get_by_api_key(self, api_key: str) -> Optional[LISConfig]:
        """Retrieve LIS configuration by tenant API key."""
        statement = select(LISConfig).where(LISConfig.tenant_api_key == api_key)
        return self._session.exec(statement).first()

    def list_all(self, skip: int = 0, limit: int = 100) -> tuple[list[LISConfig], int]:
        """List all LIS configurations (admin only)."""
        query = select(LISConfig)
        total = len(self._session.exec(query).all())

        query = query.offset(skip).limit(limit)
        configs = list(self._session.exec(query).all())

        return configs, total

    def list_with_pull_model(self, skip: int = 0, limit: int = 100) -> list[LISConfig]:
        """List all LIS configurations using pull model."""
        query = select(LISConfig).where(
            LISConfig.integration_model == IntegrationModel.PULL
        ).offset(skip).limit(limit)
        return list(self._session.exec(query).all())

    def update(self, config: LISConfig) -> LISConfig:
        """Update an existing LIS configuration."""
        with self._session.no_autoflush:
            existing = self.get_by_id(config.id, config.tenant_id)
            if not existing:
                raise LISConfigNotFoundError(f"LIS config with id '{config.id}' not found")

            # Update fields
            existing.lis_type = config.lis_type
            existing.integration_model = config.integration_model
            existing.api_endpoint_url = config.api_endpoint_url
            existing.api_auth_credentials = config.api_auth_credentials
            existing.tenant_api_key = config.tenant_api_key
            existing.pull_interval_minutes = config.pull_interval_minutes
            existing.last_successful_retrieval_at = config.last_successful_retrieval_at
            existing.connection_status = config.connection_status
            existing.connection_failure_count = config.connection_failure_count
            existing.auto_upload_enabled = config.auto_upload_enabled
            existing.upload_verified_results = config.upload_verified_results
            existing.upload_rejected_results = config.upload_rejected_results
            existing.upload_batch_size = config.upload_batch_size
            existing.upload_rate_limit = config.upload_rate_limit
            existing.last_successful_upload_at = config.last_successful_upload_at
            existing.last_upload_failure_at = config.last_upload_failure_at
            existing.upload_failure_count = config.upload_failure_count
            existing.update_timestamp()

        self._session.add(existing)
        self._session.commit()
        self._session.refresh(existing)
        return existing

    def delete(self, config_id: str, tenant_id: str) -> bool:
        """Delete a LIS configuration, ensuring it belongs to the tenant."""
        config = self.get_by_id(config_id, tenant_id)
        if not config:
            return False

        self._session.delete(config)
        self._session.commit()
        return True
