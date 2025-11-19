"""In-memory implementation of instrument result repository for testing."""

from typing import Optional
import uuid
import copy

from app.ports import IInstrumentResultRepository
from app.models.instrument_result import InstrumentResult, InstrumentResultStatus
from app.exceptions import InstrumentResultAlreadyExistsError, InstrumentResultNotFoundError


class InMemoryInstrumentResultRepository(IInstrumentResultRepository):
    """In-memory implementation of instrument result repository for testing."""

    def __init__(self):
        """Initialize with empty storage."""
        self._results: dict[str, InstrumentResult] = {}

    def create(self, result: InstrumentResult) -> InstrumentResult:
        """Create a new instrument result in memory."""
        if not result.tenant_id:
            raise ValueError("InstrumentResult must have a tenant_id")

        # Check for duplicate external_instrument_result_id within tenant and instrument
        for existing in self._results.values():
            if (existing.external_instrument_result_id == result.external_instrument_result_id and
                existing.tenant_id == result.tenant_id and
                existing.instrument_id == result.instrument_id):
                raise InstrumentResultAlreadyExistsError(
                    f"Result with external_instrument_result_id '{result.external_instrument_result_id}' "
                    f"already exists for tenant and instrument"
                )

        if not result.id:
            result.id = str(uuid.uuid4())

        # Store copy to avoid external mutations
        self._results[result.id] = copy.deepcopy(result)
        return copy.deepcopy(self._results[result.id])

    def get_by_id(self, result_id: str, tenant_id: str) -> Optional[InstrumentResult]:
        """Retrieve result by ID, ensuring it belongs to tenant."""
        result = self._results.get(result_id)
        if result and result.tenant_id == tenant_id:
            return copy.deepcopy(result)
        return None

    def get_by_external_id(
        self,
        external_instrument_result_id: str,
        instrument_id: str,
        tenant_id: str
    ) -> Optional[InstrumentResult]:
        """Retrieve result by external instrument result ID."""
        for result in self._results.values():
            if (result.external_instrument_result_id == external_instrument_result_id and
                result.instrument_id == instrument_id and
                result.tenant_id == tenant_id):
                return copy.deepcopy(result)
        return None

    def search(
        self,
        tenant_id: str,
        status: Optional[InstrumentResultStatus] = None,
        instrument_id: Optional[str] = None,
        order_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[InstrumentResult], int]:
        """Search results by criteria."""
        # Filter by tenant
        results = [r for r in self._results.values() if r.tenant_id == tenant_id]

        # Apply filters
        if status:
            results = [r for r in results if r.status == status]
        if instrument_id:
            results = [r for r in results if r.instrument_id == instrument_id]
        if order_id:
            results = [r for r in results if r.order_id == order_id]

        # Sort by received_timestamp (newest first)
        results.sort(key=lambda r: r.received_timestamp, reverse=True)

        total = len(results)
        paginated = results[skip:skip + limit]

        return [copy.deepcopy(r) for r in paginated], total

    def update(self, result: InstrumentResult) -> InstrumentResult:
        """Update existing result."""
        if result.id not in self._results:
            raise InstrumentResultNotFoundError(f"InstrumentResult with id '{result.id}' not found")

        existing = self._results[result.id]
        if existing.tenant_id != result.tenant_id:
            raise InstrumentResultNotFoundError(f"InstrumentResult with id '{result.id}' not found")

        result.update_timestamp()
        self._results[result.id] = copy.deepcopy(result)
        return copy.deepcopy(result)

    def delete(self, result_id: str, tenant_id: str) -> bool:
        """Delete a result, ensuring it belongs to the tenant."""
        result = self._results.get(result_id)
        if result and result.tenant_id == tenant_id:
            del self._results[result_id]
            return True
        return False
