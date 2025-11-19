"""Instrument repository port."""

import abc
from typing import Optional
from app.models.instrument import Instrument


class IInstrumentRepository(abc.ABC):
    """
    Port: Abstract contract for instrument data persistence with multi-tenant support.

    All queries automatically filter by tenant_id to ensure data isolation.
    """

    @abc.abstractmethod
    def create(self, instrument: Instrument) -> Instrument:
        """
        Create a new instrument.

        Args:
            instrument: Instrument entity to create (must have tenant_id set)

        Returns:
            Created instrument with generated ID

        Raises:
            InstrumentAlreadyExistsError: If instrument with same name exists in tenant
            ValueError: If instrument doesn't have tenant_id set
        """
        pass

    @abc.abstractmethod
    def get_by_id(self, instrument_id: str, tenant_id: str) -> Optional[Instrument]:
        """
        Retrieve an instrument by ID, ensuring it belongs to the tenant.

        Args:
            instrument_id: Unique instrument identifier
            tenant_id: Tenant identifier for isolation

        Returns:
            Instrument if found and belongs to tenant, None otherwise
        """
        pass

    @abc.abstractmethod
    def get_by_tenant(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[Instrument], int]:
        """
        List instruments for a tenant.

        Args:
            tenant_id: Tenant identifier
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (list of instruments, total count)
        """
        pass

    @abc.abstractmethod
    def get_by_api_token(self, api_token: str) -> Optional[Instrument]:
        """
        Retrieve an instrument by API token.

        Args:
            api_token: API token for authentication

        Returns:
            Instrument if found, None otherwise
        """
        pass

    @abc.abstractmethod
    def update(self, instrument: Instrument) -> Instrument:
        """
        Update an existing instrument.

        Args:
            instrument: Instrument with updated fields

        Returns:
            Updated instrument

        Raises:
            InstrumentNotFoundError: If instrument doesn't exist
        """
        pass

    @abc.abstractmethod
    def delete(self, instrument_id: str, tenant_id: str) -> bool:
        """
        Delete an instrument, ensuring it belongs to the tenant.

        Args:
            instrument_id: ID of instrument to delete
            tenant_id: Tenant identifier for isolation

        Returns:
            True if deleted, False if not found
        """
        pass
