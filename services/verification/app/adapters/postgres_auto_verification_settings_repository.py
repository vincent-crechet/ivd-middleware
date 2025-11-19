"""PostgreSQL implementation of auto-verification settings repository."""

from sqlmodel import Session, select
from typing import Optional
import uuid

from app.ports import IAutoVerificationSettingsRepository
from app.models import AutoVerificationSettings
from app.exceptions import SettingsAlreadyExistsError, SettingsNotFoundError


class PostgresAutoVerificationSettingsRepository(IAutoVerificationSettingsRepository):
    """PostgreSQL implementation of auto-verification settings repository with multi-tenant support."""

    def __init__(self, session: Session):
        """
        Initialize with database session.

        Args:
            session: SQLModel database session
        """
        self._session = session

    def create(self, settings: AutoVerificationSettings) -> AutoVerificationSettings:
        """Create new auto-verification settings in PostgreSQL."""
        # Validate tenant_id and test_code are set
        if not settings.tenant_id:
            raise ValueError("Settings must have a tenant_id")
        if not settings.test_code:
            raise ValueError("Settings must have a test_code")

        # Check for duplicate (tenant_id, test_code) constraint
        existing = self._session.exec(
            select(AutoVerificationSettings).where(
                AutoVerificationSettings.tenant_id == settings.tenant_id,
                AutoVerificationSettings.test_code == settings.test_code
            )
        ).first()

        if existing:
            raise SettingsAlreadyExistsError(
                f"Settings for test code '{settings.test_code}' already exist in tenant"
            )

        # Generate ID if not provided
        if not settings.id:
            settings.id = str(uuid.uuid4())

        self._session.add(settings)
        self._session.commit()
        self._session.refresh(settings)
        return settings

    def get_by_id(self, settings_id: str, tenant_id: str) -> Optional[AutoVerificationSettings]:
        """Retrieve settings by ID, ensuring it belongs to tenant."""
        statement = select(AutoVerificationSettings).where(
            AutoVerificationSettings.id == settings_id,
            AutoVerificationSettings.tenant_id == tenant_id
        )
        return self._session.exec(statement).first()

    def get_by_tenant(self, tenant_id: str) -> list[AutoVerificationSettings]:
        """List all auto-verification settings for a tenant."""
        statement = select(AutoVerificationSettings).where(
            AutoVerificationSettings.tenant_id == tenant_id
        ).order_by(AutoVerificationSettings.test_code)

        return list(self._session.exec(statement).all())

    def get_by_test_code(self, test_code: str, tenant_id: str) -> Optional[AutoVerificationSettings]:
        """Retrieve settings for a specific test code within a tenant."""
        statement = select(AutoVerificationSettings).where(
            AutoVerificationSettings.test_code == test_code,
            AutoVerificationSettings.tenant_id == tenant_id
        )
        return self._session.exec(statement).first()

    def update(self, settings: AutoVerificationSettings) -> AutoVerificationSettings:
        """Update existing auto-verification settings."""
        with self._session.no_autoflush:
            existing = self.get_by_id(settings.id, settings.tenant_id)
            if not existing:
                raise SettingsNotFoundError(f"Settings with id '{settings.id}' not found")

            # Check for duplicate (tenant_id, test_code) constraint if test_code changed
            if existing.test_code != settings.test_code:
                duplicate = self._session.exec(
                    select(AutoVerificationSettings).where(
                        AutoVerificationSettings.id != settings.id,
                        AutoVerificationSettings.tenant_id == settings.tenant_id,
                        AutoVerificationSettings.test_code == settings.test_code
                    )
                ).first()

                if duplicate:
                    raise SettingsAlreadyExistsError(
                        f"Settings for test code '{settings.test_code}' already exist in tenant"
                    )

            # Update fields
            existing.test_code = settings.test_code
            existing.test_name = settings.test_name
            existing.reference_range_low = settings.reference_range_low
            existing.reference_range_high = settings.reference_range_high
            existing.critical_range_low = settings.critical_range_low
            existing.critical_range_high = settings.critical_range_high
            existing.instrument_flags_to_block = settings.instrument_flags_to_block
            existing.delta_check_threshold_percent = settings.delta_check_threshold_percent
            existing.delta_check_lookback_days = settings.delta_check_lookback_days
            existing.update_timestamp()

        self._session.add(existing)
        self._session.commit()
        self._session.refresh(existing)
        return existing

    def delete(self, settings_id: str, tenant_id: str) -> bool:
        """Delete auto-verification settings, ensuring it belongs to the tenant."""
        settings = self.get_by_id(settings_id, tenant_id)
        if not settings:
            return False

        self._session.delete(settings)
        self._session.commit()
        return True

    def list_all(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[AutoVerificationSettings], int]:
        """List all auto-verification settings for a tenant with pagination."""
        # Build base query with tenant filter
        query = select(AutoVerificationSettings).where(
            AutoVerificationSettings.tenant_id == tenant_id
        )

        # Get total count
        count_query = select(AutoVerificationSettings).where(
            AutoVerificationSettings.tenant_id == tenant_id
        )
        total = len(self._session.exec(count_query).all())

        # Apply sorting and pagination
        query = query.order_by(AutoVerificationSettings.test_code).offset(skip).limit(limit)
        settings = list(self._session.exec(query).all())

        return settings, total
