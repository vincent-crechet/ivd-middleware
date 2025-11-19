"""InstrumentQuery repository port."""

import abc
from typing import Optional
from datetime import datetime
from app.models.instrument_query import InstrumentQuery


class IInstrumentQueryRepository(abc.ABC):
    """
    Port: Abstract contract for instrument query audit log persistence with multi-tenant support.

    InstrumentQuery entities are immutable audit logs that track all queries from instruments.
    All queries automatically filter by tenant_id to ensure data isolation.
    """

    @abc.abstractmethod
    def create(self, query: InstrumentQuery) -> InstrumentQuery:
        """
        Create a new instrument query audit log entry.

        Args:
            query: InstrumentQuery entity to create (must have tenant_id set)

        Returns:
            Created query with generated ID

        Raises:
            ValueError: If query doesn't have tenant_id set
        """
        pass

    @abc.abstractmethod
    def get_by_instrument(
        self,
        instrument_id: str,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[InstrumentQuery], int]:
        """
        List all queries for a specific instrument.

        Args:
            instrument_id: Instrument identifier
            tenant_id: Tenant identifier for isolation
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (list of queries, total count)
        """
        pass

    @abc.abstractmethod
    def search(
        self,
        tenant_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        instrument_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[InstrumentQuery], int]:
        """
        Search queries by date range and optional instrument filter.

        Args:
            tenant_id: Tenant identifier
            start_date: Optional start of query timestamp range
            end_date: Optional end of query timestamp range
            instrument_id: Optional instrument ID filter
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (list of queries, total count)
        """
        pass
