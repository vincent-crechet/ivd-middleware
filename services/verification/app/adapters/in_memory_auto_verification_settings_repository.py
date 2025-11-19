"""In-memory implementation of auto-verification settings repository for testing."""

from typing import Optional
import uuid
import copy

from app.ports import IAutoVerificationSettingsRepository
from app.models import AutoVerificationSettings
from app.exceptions import SettingsAlreadyExistsError, SettingsNotFoundError


class InMemoryAutoVerificationSettingsRepository(IAutoVerificationSettingsRepository):
    """In-memory implementation of auto-verification settings repository for testing."""

    def __init__(self):
        """Initialize with empty storage."""
        self._settings: dict[str, AutoVerificationSettings] = {}

    def create(self, settings: AutoVerificationSettings) -> AutoVerificationSettings:
        """Create new auto-verification settings in memory."""
        if not settings.tenant_id:
            raise ValueError("Settings must have a tenant_id")
        if not settings.test_code:
            raise ValueError("Settings must have a test_code")

        # Check for duplicate (tenant_id, test_code) constraint
        for existing in self._settings.values():
            if (existing.tenant_id == settings.tenant_id and
                existing.test_code == settings.test_code):
                raise SettingsAlreadyExistsError(
                    f"Settings for test code '{settings.test_code}' already exist in tenant"
                )

        # Generate ID if not provided
        if not settings.id:
            settings.id = str(uuid.uuid4())

        # Store copy to avoid external mutations
        self._settings[settings.id] = copy.deepcopy(settings)
        return copy.deepcopy(self._settings[settings.id])

    def get_by_id(self, settings_id: str, tenant_id: str) -> Optional[AutoVerificationSettings]:
        """Retrieve settings by ID, ensuring it belongs to tenant."""
        settings = self._settings.get(settings_id)
        if settings and settings.tenant_id == tenant_id:
            return copy.deepcopy(settings)
        return None

    def get_by_tenant(self, tenant_id: str) -> list[AutoVerificationSettings]:
        """List all auto-verification settings for a tenant."""
        settings_list = [
            copy.deepcopy(s) for s in self._settings.values()
            if s.tenant_id == tenant_id
        ]
        # Sort by test_code for consistent ordering
        settings_list.sort(key=lambda s: s.test_code)
        return settings_list

    def get_by_test_code(self, test_code: str, tenant_id: str) -> Optional[AutoVerificationSettings]:
        """Retrieve settings for a specific test code within a tenant."""
        for settings in self._settings.values():
            if settings.tenant_id == tenant_id and settings.test_code == test_code:
                return copy.deepcopy(settings)
        return None

    def update(self, settings: AutoVerificationSettings) -> AutoVerificationSettings:
        """Update existing auto-verification settings."""
        if not settings.id or settings.id not in self._settings:
            raise SettingsNotFoundError(f"Settings with id '{settings.id}' not found")

        existing = self._settings[settings.id]
        if existing.tenant_id != settings.tenant_id:
            raise SettingsNotFoundError(f"Settings with id '{settings.id}' not found")

        # Check for duplicate (tenant_id, test_code) constraint if test_code changed
        if existing.test_code != settings.test_code:
            for other in self._settings.values():
                if (other.id != settings.id and
                    other.tenant_id == settings.tenant_id and
                    other.test_code == settings.test_code):
                    raise SettingsAlreadyExistsError(
                        f"Settings for test code '{settings.test_code}' already exist in tenant"
                    )

        settings.update_timestamp()
        self._settings[settings.id] = copy.deepcopy(settings)
        return copy.deepcopy(settings)

    def delete(self, settings_id: str, tenant_id: str) -> bool:
        """Delete auto-verification settings, ensuring it belongs to the tenant."""
        settings = self._settings.get(settings_id)
        if settings and settings.tenant_id == tenant_id:
            del self._settings[settings_id]
            return True
        return False

    def list_all(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[AutoVerificationSettings], int]:
        """List all auto-verification settings for a tenant with pagination."""
        # Filter by tenant
        settings_list = [
            s for s in self._settings.values()
            if s.tenant_id == tenant_id
        ]

        # Sort by test_code for consistent ordering
        settings_list.sort(key=lambda s: s.test_code)

        total = len(settings_list)
        paginated = settings_list[skip:skip + limit]

        return [copy.deepcopy(s) for s in paginated], total
