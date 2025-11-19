"""InstrumentResult repository port."""

import abc
from typing import Optional
from app.models.instrument_result import InstrumentResult, InstrumentResultStatus


class IInstrumentResultRepository(abc.ABC):
    """
    Port: Abstract contract for instrument result data persistence with multi-tenant support.

    All queries automatically filter by tenant_id to ensure data isolation.
    """

    @abc.abstractmethod
    def create(self, result: InstrumentResult) -> InstrumentResult:
        """
        Create a new instrument result.

        Args:
            result: InstrumentResult entity to create (must have tenant_id set)

        Returns:
            Created result with generated ID

        Raises:
            InstrumentResultAlreadyExistsError: If result with same external_instrument_result_id
                                                exists for tenant and instrument
            ValueError: If result doesn't have tenant_id set
        """
        pass

    @abc.abstractmethod
    def get_by_id(self, result_id: str, tenant_id: str) -> Optional[InstrumentResult]:
        """
        Retrieve a result by ID, ensuring it belongs to the tenant.

        Args:
            result_id: Unique result identifier
            tenant_id: Tenant identifier for isolation

        Returns:
            InstrumentResult if found and belongs to tenant, None otherwise
        """
        pass

    @abc.abstractmethod
    def get_by_external_id(
        self,
        external_instrument_result_id: str,
        instrument_id: str,
        tenant_id: str
    ) -> Optional[InstrumentResult]:
        """
        Retrieve a result by external instrument result ID.

        Args:
            external_instrument_result_id: External instrument result identifier
            instrument_id: Instrument identifier
            tenant_id: Tenant identifier for isolation

        Returns:
            InstrumentResult if found, None otherwise
        """
        pass

    @abc.abstractmethod
    def search(
        self,
        tenant_id: str,
        status: Optional[InstrumentResultStatus] = None,
        instrument_id: Optional[str] = None,
        order_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[InstrumentResult], int]:
        """
        Search results by criteria.

        Args:
            tenant_id: Tenant identifier
            status: Optional result status filter
            instrument_id: Optional instrument ID filter
            order_id: Optional order ID filter
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (list of results, total count)
        """
        pass

    @abc.abstractmethod
    def update(self, result: InstrumentResult) -> InstrumentResult:
        """
        Update an existing result.

        Args:
            result: InstrumentResult with updated fields

        Returns:
            Updated result

        Raises:
            InstrumentResultNotFoundError: If result doesn't exist
        """
        pass

    @abc.abstractmethod
    def delete(self, result_id: str, tenant_id: str) -> bool:
        """
        Delete a result, ensuring it belongs to the tenant.

        Args:
            result_id: ID of result to delete
            tenant_id: Tenant identifier for isolation

        Returns:
            True if deleted, False if not found
        """
        pass
