"""PostgreSQL implementation of instrument result repository."""

from sqlmodel import Session, select
from typing import Optional
import uuid

from app.ports import IInstrumentResultRepository
from app.models.instrument_result import InstrumentResult, InstrumentResultStatus
from app.exceptions import InstrumentResultAlreadyExistsError, InstrumentResultNotFoundError


class PostgresInstrumentResultRepository(IInstrumentResultRepository):
    """PostgreSQL implementation of instrument result repository with multi-tenant support."""

    def __init__(self, session: Session):
        """
        Initialize with database session.

        Args:
            session: SQLModel database session
        """
        self._session = session

    def create(self, result: InstrumentResult) -> InstrumentResult:
        """Create a new instrument result in PostgreSQL."""
        # Validate tenant_id is set
        if not result.tenant_id:
            raise ValueError("InstrumentResult must have a tenant_id")

        # Check for duplicate external_instrument_result_id within tenant and instrument
        existing = self._session.exec(
            select(InstrumentResult).where(
                InstrumentResult.external_instrument_result_id == result.external_instrument_result_id,
                InstrumentResult.tenant_id == result.tenant_id,
                InstrumentResult.instrument_id == result.instrument_id
            )
        ).first()

        if existing:
            raise InstrumentResultAlreadyExistsError(
                f"Result with external_instrument_result_id '{result.external_instrument_result_id}' "
                f"already exists for tenant and instrument"
            )

        # Generate ID if not provided
        if not result.id:
            result.id = str(uuid.uuid4())

        self._session.add(result)
        self._session.commit()
        self._session.refresh(result)
        return result

    def get_by_id(self, result_id: str, tenant_id: str) -> Optional[InstrumentResult]:
        """Retrieve result by ID, ensuring it belongs to tenant."""
        statement = select(InstrumentResult).where(
            InstrumentResult.id == result_id,
            InstrumentResult.tenant_id == tenant_id
        )
        return self._session.exec(statement).first()

    def get_by_external_id(
        self,
        external_instrument_result_id: str,
        instrument_id: str,
        tenant_id: str
    ) -> Optional[InstrumentResult]:
        """Retrieve result by external instrument result ID."""
        statement = select(InstrumentResult).where(
            InstrumentResult.external_instrument_result_id == external_instrument_result_id,
            InstrumentResult.instrument_id == instrument_id,
            InstrumentResult.tenant_id == tenant_id
        )
        return self._session.exec(statement).first()

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
        # Build base query
        query = select(InstrumentResult).where(InstrumentResult.tenant_id == tenant_id)

        # Apply filters
        if status:
            query = query.where(InstrumentResult.status == status)
        if instrument_id:
            query = query.where(InstrumentResult.instrument_id == instrument_id)
        if order_id:
            query = query.where(InstrumentResult.order_id == order_id)

        # Get total count before pagination
        count_query = select(InstrumentResult).where(InstrumentResult.tenant_id == tenant_id)
        if status:
            count_query = count_query.where(InstrumentResult.status == status)
        if instrument_id:
            count_query = count_query.where(InstrumentResult.instrument_id == instrument_id)
        if order_id:
            count_query = count_query.where(InstrumentResult.order_id == order_id)

        total = len(self._session.exec(count_query).all())

        # Sort by received_timestamp (newest first) and apply pagination
        query = query.order_by(InstrumentResult.received_timestamp.desc()).offset(skip).limit(limit)
        results = list(self._session.exec(query).all())

        return results, total

    def update(self, result: InstrumentResult) -> InstrumentResult:
        """Update existing result."""
        with self._session.no_autoflush:
            existing = self.get_by_id(result.id, result.tenant_id)
            if not existing:
                raise InstrumentResultNotFoundError(f"InstrumentResult with id '{result.id}' not found")

            # Update fields
            existing.external_instrument_result_id = result.external_instrument_result_id
            existing.instrument_id = result.instrument_id
            existing.order_id = result.order_id
            existing.test_code = result.test_code
            existing.test_name = result.test_name
            existing.value = result.value
            existing.unit = result.unit
            existing.reference_range_low = result.reference_range_low
            existing.reference_range_high = result.reference_range_high
            existing.instrument_flags = result.instrument_flags
            existing.collection_timestamp = result.collection_timestamp
            existing.received_timestamp = result.received_timestamp
            existing.status = result.status
            existing.validation_error = result.validation_error
            existing.update_timestamp()

        self._session.add(existing)
        self._session.commit()
        self._session.refresh(existing)
        return existing

    def delete(self, result_id: str, tenant_id: str) -> bool:
        """Delete a result, ensuring it belongs to the tenant."""
        result = self.get_by_id(result_id, tenant_id)
        if not result:
            return False

        self._session.delete(result)
        self._session.commit()
        return True
