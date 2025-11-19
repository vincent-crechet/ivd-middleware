"""PostgreSQL implementation of instrument query repository."""

from sqlmodel import Session, select
from typing import Optional
from datetime import datetime
import uuid

from app.ports import IInstrumentQueryRepository
from app.models.instrument_query import InstrumentQuery


class PostgresInstrumentQueryRepository(IInstrumentQueryRepository):
    """PostgreSQL implementation of instrument query repository with multi-tenant support."""

    def __init__(self, session: Session):
        """
        Initialize with database session.

        Args:
            session: SQLModel database session
        """
        self._session = session

    def create(self, query: InstrumentQuery) -> InstrumentQuery:
        """Create a new instrument query audit log entry in PostgreSQL."""
        # Validate tenant_id is set
        if not query.tenant_id:
            raise ValueError("InstrumentQuery must have a tenant_id")

        # Generate ID if not provided
        if not query.id:
            query.id = str(uuid.uuid4())

        self._session.add(query)
        self._session.commit()
        self._session.refresh(query)
        return query

    def get_by_instrument(
        self,
        instrument_id: str,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[InstrumentQuery], int]:
        """List all queries for a specific instrument."""
        # Build query
        query = select(InstrumentQuery).where(
            InstrumentQuery.instrument_id == instrument_id,
            InstrumentQuery.tenant_id == tenant_id
        )

        # Get total count
        count_query = select(InstrumentQuery).where(
            InstrumentQuery.instrument_id == instrument_id,
            InstrumentQuery.tenant_id == tenant_id
        )
        total = len(self._session.exec(count_query).all())

        # Sort by query_timestamp (newest first) and apply pagination
        query = query.order_by(InstrumentQuery.query_timestamp.desc()).offset(skip).limit(limit)
        queries = list(self._session.exec(query).all())

        return queries, total

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
        # Build base query
        query = select(InstrumentQuery).where(InstrumentQuery.tenant_id == tenant_id)

        # Apply filters
        if start_date:
            query = query.where(InstrumentQuery.query_timestamp >= start_date)
        if end_date:
            query = query.where(InstrumentQuery.query_timestamp <= end_date)
        if instrument_id:
            query = query.where(InstrumentQuery.instrument_id == instrument_id)

        # Get total count before pagination
        count_query = select(InstrumentQuery).where(InstrumentQuery.tenant_id == tenant_id)
        if start_date:
            count_query = count_query.where(InstrumentQuery.query_timestamp >= start_date)
        if end_date:
            count_query = count_query.where(InstrumentQuery.query_timestamp <= end_date)
        if instrument_id:
            count_query = count_query.where(InstrumentQuery.instrument_id == instrument_id)

        total = len(self._session.exec(count_query).all())

        # Sort by query_timestamp (newest first) and apply pagination
        query = query.order_by(InstrumentQuery.query_timestamp.desc()).offset(skip).limit(limit)
        queries = list(self._session.exec(query).all())

        return queries, total
