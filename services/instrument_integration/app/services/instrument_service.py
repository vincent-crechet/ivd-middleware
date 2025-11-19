"""Instrument business logic service."""

from typing import Optional
from datetime import datetime
import secrets

from app.models import Instrument, InstrumentType, InstrumentStatus
from app.ports import IInstrumentRepository
from app.exceptions import (
    InstrumentNotFoundError,
    InstrumentAlreadyExistsError,
    InvalidApiTokenError,
)


class InstrumentService:
    """
    Service for managing instruments with business logic.

    Handles creation, retrieval, authentication, status tracking,
    and connection monitoring for analytical instruments.
    Depends only on IInstrumentRepository port.
    """

    def __init__(self, instrument_repo: IInstrumentRepository):
        """
        Initialize instrument service with repository.

        Args:
            instrument_repo: Instrument repository (injected port)
        """
        self._instrument_repo = instrument_repo

    def create_instrument(
        self,
        tenant_id: str,
        name: str,
        instrument_type: InstrumentType,
        api_token: Optional[str] = None
    ) -> Instrument:
        """
        Create a new instrument with validation.

        Args:
            tenant_id: Tenant identifier
            name: Instrument name (must be unique per tenant)
            instrument_type: Type of analytical instrument
            api_token: Optional API token (auto-generated if not provided)

        Returns:
            Created instrument

        Raises:
            InstrumentAlreadyExistsError: If instrument with same name exists in tenant
        """
        # Auto-generate API token if not provided
        if not api_token:
            api_token = self._generate_api_token()

        # Create instrument
        instrument = Instrument(
            tenant_id=tenant_id,
            name=name,
            instrument_type=instrument_type,
            api_token=api_token,
            status=InstrumentStatus.INACTIVE
        )

        # Persist via repository
        return self._instrument_repo.create(instrument)

    def get_instrument(self, tenant_id: str, instrument_id: str) -> Instrument:
        """
        Get an instrument by ID.

        Args:
            tenant_id: Tenant identifier (for isolation)
            instrument_id: Instrument identifier

        Returns:
            Instrument

        Raises:
            InstrumentNotFoundError: If instrument not found
        """
        instrument = self._instrument_repo.get_by_id(instrument_id, tenant_id)
        if not instrument:
            raise InstrumentNotFoundError(f"Instrument '{instrument_id}' not found")
        return instrument

    def get_by_api_token(self, api_token: str) -> Instrument:
        """
        Get an instrument by API token (for authentication).

        Args:
            api_token: API token for authentication

        Returns:
            Instrument

        Raises:
            InvalidApiTokenError: If API token is invalid or instrument not found
        """
        instrument = self._instrument_repo.get_by_api_token(api_token)
        if not instrument:
            raise InvalidApiTokenError("Invalid or unauthorized API token")
        return instrument

    def list_instruments(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[Instrument], int]:
        """
        List all instruments for a tenant.

        Args:
            tenant_id: Tenant identifier
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            Tuple of (instruments, total count)
        """
        return self._instrument_repo.get_by_tenant(
            tenant_id=tenant_id,
            skip=skip,
            limit=limit
        )

    def update_instrument(
        self,
        tenant_id: str,
        instrument_id: str,
        name: Optional[str] = None,
        instrument_type: Optional[InstrumentType] = None,
        status: Optional[InstrumentStatus] = None
    ) -> Instrument:
        """
        Update an instrument.

        Args:
            tenant_id: Tenant identifier
            instrument_id: Instrument identifier
            name: Optional new name
            instrument_type: Optional new instrument type
            status: Optional new status

        Returns:
            Updated instrument

        Raises:
            InstrumentNotFoundError: If instrument not found
        """
        instrument = self.get_instrument(tenant_id, instrument_id)

        if name is not None:
            instrument.name = name
        if instrument_type is not None:
            instrument.instrument_type = instrument_type
        if status is not None:
            instrument.status = status

        instrument.update_timestamp()
        return self._instrument_repo.update(instrument)

    def delete_instrument(self, tenant_id: str, instrument_id: str) -> Instrument:
        """
        Soft delete (deactivate) an instrument.

        Args:
            tenant_id: Tenant identifier
            instrument_id: Instrument identifier

        Returns:
            Deactivated instrument

        Raises:
            InstrumentNotFoundError: If instrument not found
        """
        return self.update_instrument(
            tenant_id=tenant_id,
            instrument_id=instrument_id,
            status=InstrumentStatus.INACTIVE
        )

    def test_connection(self, tenant_id: str, instrument_id: str) -> bool:
        """
        Test instrument connection.

        This is a placeholder for connection testing logic.
        In a real implementation, this would attempt to connect to the instrument.

        Args:
            tenant_id: Tenant identifier
            instrument_id: Instrument identifier

        Returns:
            True if connection successful, False otherwise

        Raises:
            InstrumentNotFoundError: If instrument not found
        """
        instrument = self.get_instrument(tenant_id, instrument_id)

        # In a real implementation, this would test the actual connection
        # For now, we just return True if the instrument exists
        return instrument.status == InstrumentStatus.ACTIVE

    def record_successful_query(self, tenant_id: str, instrument_id: str) -> Instrument:
        """
        Update last_successful_query_at timestamp and reset failure tracking.

        Args:
            tenant_id: Tenant identifier
            instrument_id: Instrument identifier

        Returns:
            Updated instrument

        Raises:
            InstrumentNotFoundError: If instrument not found
        """
        instrument = self.get_instrument(tenant_id, instrument_id)

        instrument.last_successful_query_at = datetime.utcnow()
        instrument.connection_failure_count = 0
        instrument.last_failure_at = None
        instrument.last_failure_reason = None
        instrument.status = InstrumentStatus.ACTIVE
        instrument.update_timestamp()

        return self._instrument_repo.update(instrument)

    def record_query_failure(
        self,
        tenant_id: str,
        instrument_id: str,
        reason: str
    ) -> Instrument:
        """
        Update failure tracking when a query fails.

        Args:
            tenant_id: Tenant identifier
            instrument_id: Instrument identifier
            reason: Reason for failure

        Returns:
            Updated instrument

        Raises:
            InstrumentNotFoundError: If instrument not found
        """
        instrument = self.get_instrument(tenant_id, instrument_id)

        instrument.connection_failure_count += 1
        instrument.last_failure_at = datetime.utcnow()
        instrument.last_failure_reason = reason

        # Mark as disconnected after multiple failures
        if instrument.connection_failure_count >= 3:
            instrument.status = InstrumentStatus.DISCONNECTED

        instrument.update_timestamp()

        return self._instrument_repo.update(instrument)

    def regenerate_api_token(self, tenant_id: str, instrument_id: str) -> Instrument:
        """
        Generate a new API token for an instrument.

        Args:
            tenant_id: Tenant identifier
            instrument_id: Instrument identifier

        Returns:
            Updated instrument with new API token

        Raises:
            InstrumentNotFoundError: If instrument not found
        """
        instrument = self.get_instrument(tenant_id, instrument_id)

        instrument.api_token = self._generate_api_token()
        instrument.api_token_created_at = datetime.utcnow()
        instrument.update_timestamp()

        return self._instrument_repo.update(instrument)

    def record_successful_result(self, tenant_id: str, instrument_id: str) -> Instrument:
        """
        Update last_successful_result_at timestamp.

        Args:
            tenant_id: Tenant identifier
            instrument_id: Instrument identifier

        Returns:
            Updated instrument

        Raises:
            InstrumentNotFoundError: If instrument not found
        """
        instrument = self.get_instrument(tenant_id, instrument_id)

        instrument.last_successful_result_at = datetime.utcnow()
        instrument.update_timestamp()

        return self._instrument_repo.update(instrument)

    def record_result_failure(self, tenant_id: str, instrument_id: str) -> Instrument:
        """
        Update result failure tracking.

        Args:
            tenant_id: Tenant identifier
            instrument_id: Instrument identifier

        Returns:
            Updated instrument

        Raises:
            InstrumentNotFoundError: If instrument not found
        """
        instrument = self.get_instrument(tenant_id, instrument_id)

        # For now, we just update the timestamp
        # In the future, we could add result-specific failure tracking
        instrument.update_timestamp()

        return self._instrument_repo.update(instrument)

    def _generate_api_token(self) -> str:
        """
        Generate a secure API token.

        Returns:
            Secure random API token
        """
        return secrets.token_urlsafe(32)
