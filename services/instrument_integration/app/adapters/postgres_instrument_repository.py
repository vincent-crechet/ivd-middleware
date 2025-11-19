"""PostgreSQL implementation of instrument repository."""

from sqlmodel import Session, select
from typing import Optional
import uuid

from app.ports import IInstrumentRepository
from app.models.instrument import Instrument
from app.exceptions import InstrumentAlreadyExistsError, InstrumentNotFoundError


class PostgresInstrumentRepository(IInstrumentRepository):
    """PostgreSQL implementation of instrument repository with multi-tenant support."""

    def __init__(self, session: Session):
        """
        Initialize with database session.

        Args:
            session: SQLModel database session
        """
        self._session = session

    def create(self, instrument: Instrument) -> Instrument:
        """Create a new instrument in PostgreSQL."""
        # Validate tenant_id is set
        if not instrument.tenant_id:
            raise ValueError("Instrument must have a tenant_id")

        # Check for duplicate name within tenant
        existing = self._session.exec(
            select(Instrument).where(
                Instrument.name == instrument.name,
                Instrument.tenant_id == instrument.tenant_id
            )
        ).first()

        if existing:
            raise InstrumentAlreadyExistsError(
                f"Instrument with name '{instrument.name}' already exists in tenant"
            )

        # Check for duplicate API token (global uniqueness)
        existing_token = self._session.exec(
            select(Instrument).where(Instrument.api_token == instrument.api_token)
        ).first()

        if existing_token:
            raise InstrumentAlreadyExistsError(
                f"Instrument with api_token '{instrument.api_token}' already exists"
            )

        # Generate ID if not provided
        if not instrument.id:
            instrument.id = str(uuid.uuid4())

        self._session.add(instrument)
        self._session.commit()
        self._session.refresh(instrument)
        return instrument

    def get_by_id(self, instrument_id: str, tenant_id: str) -> Optional[Instrument]:
        """Retrieve instrument by ID, ensuring it belongs to tenant."""
        statement = select(Instrument).where(
            Instrument.id == instrument_id,
            Instrument.tenant_id == tenant_id
        )
        return self._session.exec(statement).first()

    def get_by_tenant(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[Instrument], int]:
        """List instruments for a tenant."""
        # Build base query
        query = select(Instrument).where(Instrument.tenant_id == tenant_id)

        # Get total count
        count_query = select(Instrument).where(Instrument.tenant_id == tenant_id)
        total = len(self._session.exec(count_query).all())

        # Sort by name and apply pagination
        query = query.order_by(Instrument.name).offset(skip).limit(limit)
        instruments = list(self._session.exec(query).all())

        return instruments, total

    def get_by_api_token(self, api_token: str) -> Optional[Instrument]:
        """Retrieve instrument by API token."""
        statement = select(Instrument).where(Instrument.api_token == api_token)
        return self._session.exec(statement).first()

    def update(self, instrument: Instrument) -> Instrument:
        """Update existing instrument."""
        with self._session.no_autoflush:
            existing = self.get_by_id(instrument.id, instrument.tenant_id)
            if not existing:
                raise InstrumentNotFoundError(f"Instrument with id '{instrument.id}' not found")

            # Check for name conflict with other instruments in tenant
            conflict = self._session.exec(
                select(Instrument).where(
                    Instrument.id != instrument.id,
                    Instrument.name == instrument.name,
                    Instrument.tenant_id == instrument.tenant_id
                )
            ).first()

            if conflict:
                raise InstrumentAlreadyExistsError(
                    f"Instrument with name '{instrument.name}' already exists in tenant"
                )

            # Update fields
            existing.name = instrument.name
            existing.instrument_type = instrument.instrument_type
            existing.api_token = instrument.api_token
            existing.api_token_created_at = instrument.api_token_created_at
            existing.status = instrument.status
            existing.last_successful_query_at = instrument.last_successful_query_at
            existing.last_successful_result_at = instrument.last_successful_result_at
            existing.connection_failure_count = instrument.connection_failure_count
            existing.last_failure_at = instrument.last_failure_at
            existing.last_failure_reason = instrument.last_failure_reason
            existing.update_timestamp()

        self._session.add(existing)
        self._session.commit()
        self._session.refresh(existing)
        return existing

    def delete(self, instrument_id: str, tenant_id: str) -> bool:
        """Delete an instrument, ensuring it belongs to the tenant."""
        instrument = self.get_by_id(instrument_id, tenant_id)
        if not instrument:
            return False

        self._session.delete(instrument)
        self._session.commit()
        return True
