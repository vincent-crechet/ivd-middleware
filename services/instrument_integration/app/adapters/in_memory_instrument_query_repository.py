"""In-memory implementation of instrument query repository for testing."""

from typing import Optional
from datetime import datetime
import uuid
import copy

from app.ports import IInstrumentQueryRepository
from app.models.instrument_query import InstrumentQuery


class InMemoryInstrumentQueryRepository(IInstrumentQueryRepository):
    """In-memory implementation of instrument query repository for testing."""

    def __init__(self):
        """Initialize with empty storage."""
        self._queries: dict[str, InstrumentQuery] = {}

    def create(self, query: InstrumentQuery) -> InstrumentQuery:
        """Create a new instrument query audit log entry in memory."""
        if not query.tenant_id:
            raise ValueError("InstrumentQuery must have a tenant_id")

        if not query.id:
            query.id = str(uuid.uuid4())

        # Store copy to avoid external mutations
        self._queries[query.id] = copy.deepcopy(query)
        return copy.deepcopy(self._queries[query.id])

    def get_by_instrument(
        self,
        instrument_id: str,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[InstrumentQuery], int]:
        """List all queries for a specific instrument."""
        # Filter by instrument and tenant
        queries = [
            q for q in self._queries.values()
            if q.instrument_id == instrument_id and q.tenant_id == tenant_id
        ]

        # Sort by query_timestamp (newest first)
        queries.sort(key=lambda q: q.query_timestamp, reverse=True)

        total = len(queries)
        paginated = queries[skip:skip + limit]

        return [copy.deepcopy(q) for q in paginated], total

    def search(
        self,
        tenant_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        instrument_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[InstrumentQuery], int]:
        """Search queries by date range and optional instrument filter."""
        # Filter by tenant
        queries = [q for q in self._queries.values() if q.tenant_id == tenant_id]

        # Apply filters
        if start_date:
            queries = [q for q in queries if q.query_timestamp >= start_date]
        if end_date:
            queries = [q for q in queries if q.query_timestamp <= end_date]
        if instrument_id:
            queries = [q for q in queries if q.instrument_id == instrument_id]

        # Sort by query_timestamp (newest first)
        queries.sort(key=lambda q: q.query_timestamp, reverse=True)

        total = len(queries)
        paginated = queries[skip:skip + limit]

        return [copy.deepcopy(q) for q in paginated], total
