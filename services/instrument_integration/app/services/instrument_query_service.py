"""Instrument query audit log service."""

from typing import Optional
from datetime import datetime

from app.models import InstrumentQuery, QueryResponseStatus
from app.ports import IInstrumentQueryRepository


class InstrumentQueryService:
    """
    Service for managing instrument query audit logs.

    Handles recording and retrieval of query audit logs.
    InstrumentQuery entities are immutable audit logs.
    Depends only on IInstrumentQueryRepository port.
    """

    def __init__(self, query_repo: IInstrumentQueryRepository):
        """
        Initialize instrument query service with repository.

        Args:
            query_repo: Instrument query repository (injected port)
        """
        self._query_repo = query_repo

    def record_query(
        self,
        tenant_id: str,
        instrument_id: str,
        patient_id: Optional[str],
        sample_barcode: Optional[str],
        orders_returned: int,
        response_status: QueryResponseStatus,
        error_reason: Optional[str] = None
    ) -> InstrumentQuery:
        """
        Record a query audit log entry.

        Args:
            tenant_id: Tenant identifier
            instrument_id: Instrument identifier
            patient_id: Optional patient ID queried
            sample_barcode: Optional sample barcode queried
            orders_returned: Number of orders returned in response
            response_status: Response status (SUCCESS, ERROR, etc.)
            error_reason: Optional error reason if response_status is ERROR

        Returns:
            Created query audit log entry
        """
        now = datetime.utcnow()
        query_timestamp = now
        response_timestamp = now

        # Calculate response time (in a real implementation this would be measured)
        # For now, we'll use a minimal placeholder value
        response_time_ms = 10

        # Create query audit log
        query = InstrumentQuery(
            tenant_id=tenant_id,
            instrument_id=instrument_id,
            query_patient_id=patient_id,
            query_sample_barcode=sample_barcode,
            query_timestamp=query_timestamp,
            response_timestamp=response_timestamp,
            response_time_ms=response_time_ms,
            orders_returned_count=orders_returned,
            response_status=response_status,
            error_reason=error_reason
        )

        # Persist via repository (immutable, no updates)
        return self._query_repo.create(query)

    def get_query_history(
        self,
        tenant_id: str,
        instrument_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[InstrumentQuery], int]:
        """
        Get query history for an instrument.

        Args:
            tenant_id: Tenant identifier
            instrument_id: Instrument identifier
            start_date: Optional start of query timestamp range
            end_date: Optional end of query timestamp range
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            Tuple of (query logs, total count)
        """
        return self._query_repo.search(
            tenant_id=tenant_id,
            instrument_id=instrument_id,
            start_date=start_date,
            end_date=end_date,
            skip=skip,
            limit=limit
        )
