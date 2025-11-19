"""In-memory implementation of LIS config repository for testing."""

from typing import Optional
import uuid
import copy

from app.ports import ILISConfigRepository
from app.models import LISConfig, IntegrationModel
from app.exceptions import LISConfigNotFoundError


class InMemoryLISConfigRepository(ILISConfigRepository):
    """In-memory implementation of LIS config repository for testing."""

    def __init__(self):
        """Initialize with empty storage."""
        self._configs: dict[str, LISConfig] = {}

    def create(self, config: LISConfig) -> LISConfig:
        """Create a new LIS configuration for a tenant."""
        if not config.tenant_id:
            raise ValueError("LISConfig must have a tenant_id")

        # Check if tenant already has a configuration
        for existing in self._configs.values():
            if existing.tenant_id == config.tenant_id:
                raise ValueError(f"Tenant '{config.tenant_id}' already has a LIS configuration")

        if not config.id:
            config.id = str(uuid.uuid4())

        self._configs[config.id] = copy.deepcopy(config)
        return copy.deepcopy(self._configs[config.id])

    def get_by_tenant(self, tenant_id: str) -> Optional[LISConfig]:
        """Retrieve LIS configuration for a specific tenant."""
        for config in self._configs.values():
            if config.tenant_id == tenant_id:
                return copy.deepcopy(config)
        return None

    def get_by_id(self, config_id: str, tenant_id: str) -> Optional[LISConfig]:
        """Retrieve LIS configuration by ID, ensuring it belongs to the tenant."""
        config = self._configs.get(config_id)
        if config and config.tenant_id == tenant_id:
            return copy.deepcopy(config)
        return None

    def get_by_api_key(self, api_key: str) -> Optional[LISConfig]:
        """Retrieve LIS configuration by tenant API key."""
        for config in self._configs.values():
            if config.tenant_api_key == api_key:
                return copy.deepcopy(config)
        return None

    def list_all(self, skip: int = 0, limit: int = 100) -> tuple[list[LISConfig], int]:
        """List all LIS configurations (admin only)."""
        configs = list(self._configs.values())
        total = len(configs)
        paginated = configs[skip:skip + limit]

        return [copy.deepcopy(c) for c in paginated], total

    def list_with_pull_model(self, skip: int = 0, limit: int = 100) -> list[LISConfig]:
        """List all LIS configurations using pull model."""
        configs = [c for c in self._configs.values()
                   if c.integration_model == IntegrationModel.PULL]
        paginated = configs[skip:skip + limit]

        return [copy.deepcopy(c) for c in paginated]

    def update(self, config: LISConfig) -> LISConfig:
        """Update an existing LIS configuration."""
        if config.id not in self._configs:
            raise LISConfigNotFoundError(f"LIS config with id '{config.id}' not found")

        existing = self._configs[config.id]
        if existing.tenant_id != config.tenant_id:
            raise LISConfigNotFoundError(f"LIS config with id '{config.id}' not found")

        config.update_timestamp()
        self._configs[config.id] = copy.deepcopy(config)
        return copy.deepcopy(config)

    def delete(self, config_id: str, tenant_id: str) -> bool:
        """Delete a LIS configuration, ensuring it belongs to the tenant."""
        config = self._configs.get(config_id)
        if config and config.tenant_id == tenant_id:
            del self._configs[config_id]
            return True
        return False
