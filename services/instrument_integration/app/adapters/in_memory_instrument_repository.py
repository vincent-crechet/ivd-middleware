"""In-memory implementation of instrument repository for testing."""

from typing import Optional
import uuid
import copy

from app.ports import IInstrumentRepository
from app.models.instrument import Instrument
from app.exceptions import InstrumentAlreadyExistsError, InstrumentNotFoundError


class InMemoryInstrumentRepository(IInstrumentRepository):
    """In-memory implementation of instrument repository for testing."""

    def __init__(self):
        """Initialize with empty storage."""
        self._instruments: dict[str, Instrument] = {}

    def create(self, instrument: Instrument) -> Instrument:
        """Create a new instrument in memory."""
        if not instrument.tenant_id:
            raise ValueError("Instrument must have a tenant_id")

        # Check for duplicate name within tenant
        for existing in self._instruments.values():
            if (existing.name == instrument.name and
                existing.tenant_id == instrument.tenant_id):
                raise InstrumentAlreadyExistsError(
                    f"Instrument with name '{instrument.name}' already exists in tenant"
                )

        # Check for duplicate API token (global uniqueness)
        for existing in self._instruments.values():
            if existing.api_token == instrument.api_token:
                raise InstrumentAlreadyExistsError(
                    f"Instrument with api_token '{instrument.api_token}' already exists"
                )

        if not instrument.id:
            instrument.id = str(uuid.uuid4())

        # Store copy to avoid external mutations
        self._instruments[instrument.id] = copy.deepcopy(instrument)
        return copy.deepcopy(self._instruments[instrument.id])

    def get_by_id(self, instrument_id: str, tenant_id: str) -> Optional[Instrument]:
        """Retrieve instrument by ID, ensuring it belongs to tenant."""
        instrument = self._instruments.get(instrument_id)
        if instrument and instrument.tenant_id == tenant_id:
            return copy.deepcopy(instrument)
        return None

    def get_by_tenant(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[Instrument], int]:
        """List instruments for a tenant."""
        # Filter by tenant
        instruments = [i for i in self._instruments.values() if i.tenant_id == tenant_id]

        # Sort by name
        instruments.sort(key=lambda i: i.name)

        total = len(instruments)
        paginated = instruments[skip:skip + limit]

        return [copy.deepcopy(i) for i in paginated], total

    def get_by_api_token(self, api_token: str) -> Optional[Instrument]:
        """Retrieve instrument by API token."""
        for instrument in self._instruments.values():
            if instrument.api_token == api_token:
                return copy.deepcopy(instrument)
        return None

    def update(self, instrument: Instrument) -> Instrument:
        """Update existing instrument."""
        if instrument.id not in self._instruments:
            raise InstrumentNotFoundError(f"Instrument with id '{instrument.id}' not found")

        existing = self._instruments[instrument.id]
        if existing.tenant_id != instrument.tenant_id:
            raise InstrumentNotFoundError(f"Instrument with id '{instrument.id}' not found")

        # Check for name conflict with other instruments in tenant
        for other in self._instruments.values():
            if (other.id != instrument.id and
                other.name == instrument.name and
                other.tenant_id == instrument.tenant_id):
                raise InstrumentAlreadyExistsError(
                    f"Instrument with name '{instrument.name}' already exists in tenant"
                )

        instrument.update_timestamp()
        self._instruments[instrument.id] = copy.deepcopy(instrument)
        return copy.deepcopy(instrument)

    def delete(self, instrument_id: str, tenant_id: str) -> bool:
        """Delete an instrument, ensuring it belongs to the tenant."""
        instrument = self._instruments.get(instrument_id)
        if instrument and instrument.tenant_id == tenant_id:
            del self._instruments[instrument_id]
            return True
        return False
