"""Instrument result business logic service."""

from typing import Optional
from datetime import datetime

from app.models import InstrumentResult, InstrumentResultStatus
from app.ports import IInstrumentResultRepository
from app.exceptions import (
    InstrumentResultNotFoundError,
    InstrumentResultAlreadyExistsError,
    InvalidResultDataError,
)


class InstrumentResultService:
    """
    Service for managing instrument results with business logic.

    Handles creation, retrieval, validation, status updates, and order linking
    for results received from analytical instruments.
    Depends only on IInstrumentResultRepository port.
    """

    def __init__(self, result_repo: IInstrumentResultRepository):
        """
        Initialize instrument result service with repository.

        Args:
            result_repo: Instrument result repository (injected port)
        """
        self._result_repo = result_repo

    def create_result(
        self,
        tenant_id: str,
        instrument_id: str,
        external_result_id: str,
        test_code: str,
        test_name: str,
        value: Optional[str],
        unit: Optional[str],
        reference_range_low: Optional[float],
        reference_range_high: Optional[float],
        collection_timestamp: datetime
    ) -> InstrumentResult:
        """
        Create a new result received from instrument.

        Args:
            tenant_id: Tenant identifier
            instrument_id: Instrument identifier
            external_result_id: External instrument result ID
            test_code: Test code (must not be empty)
            test_name: Test name
            value: Result value
            unit: Result unit
            reference_range_low: Reference range low value
            reference_range_high: Reference range high value
            collection_timestamp: When sample was collected

        Returns:
            Created result

        Raises:
            InstrumentResultAlreadyExistsError: If result with same external ID exists
            InvalidResultDataError: If data validation fails
        """
        # Validate test code
        if not test_code or not test_code.strip():
            raise InvalidResultDataError("Test code cannot be empty")

        # Validate reference range
        if (reference_range_low is not None and
            reference_range_high is not None and
            reference_range_low > reference_range_high):
            raise InvalidResultDataError(
                "Reference range low cannot be greater than high"
            )

        # Create result
        result = InstrumentResult(
            tenant_id=tenant_id,
            instrument_id=instrument_id,
            external_instrument_result_id=external_result_id,
            test_code=test_code,
            test_name=test_name,
            value=value,
            unit=unit,
            reference_range_low=reference_range_low,
            reference_range_high=reference_range_high,
            collection_timestamp=collection_timestamp,
            status=InstrumentResultStatus.RECEIVED
        )

        # Persist via repository
        return self._result_repo.create(result)

    def get_result(self, tenant_id: str, result_id: str) -> InstrumentResult:
        """
        Get a result by ID.

        Args:
            tenant_id: Tenant identifier (for isolation)
            result_id: Result identifier

        Returns:
            Result

        Raises:
            InstrumentResultNotFoundError: If result not found
        """
        result = self._result_repo.get_by_id(result_id, tenant_id)
        if not result:
            raise InstrumentResultNotFoundError(f"Result '{result_id}' not found")
        return result

    def get_result_by_external_id(
        self,
        tenant_id: str,
        instrument_id: str,
        external_result_id: str
    ) -> Optional[InstrumentResult]:
        """
        Get a result by external instrument result ID (for deduplication).

        Args:
            tenant_id: Tenant identifier
            instrument_id: Instrument identifier
            external_result_id: External instrument result ID

        Returns:
            Result if found, None otherwise
        """
        return self._result_repo.get_by_external_id(
            external_instrument_result_id=external_result_id,
            instrument_id=instrument_id,
            tenant_id=tenant_id
        )

    def list_results(
        self,
        tenant_id: str,
        status: Optional[InstrumentResultStatus] = None,
        instrument_id: Optional[str] = None,
        order_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[InstrumentResult], int]:
        """
        List results with optional filters.

        Args:
            tenant_id: Tenant identifier
            status: Optional result status filter
            instrument_id: Optional instrument ID filter
            order_id: Optional order ID filter
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            Tuple of (results, total count)
        """
        return self._result_repo.search(
            tenant_id=tenant_id,
            status=status,
            instrument_id=instrument_id,
            order_id=order_id,
            skip=skip,
            limit=limit
        )

    def validate_result_data(self, result_data: dict) -> dict:
        """
        Validate result data format.

        Args:
            result_data: Dictionary containing result data

        Returns:
            Validated result data

        Raises:
            InvalidResultDataError: If validation fails
        """
        required_fields = [
            "external_result_id",
            "test_code",
            "test_name",
            "collection_timestamp"
        ]

        # Check required fields
        for field in required_fields:
            if field not in result_data or not result_data[field]:
                raise InvalidResultDataError(f"Missing required field: {field}")

        # Validate test code
        if not result_data["test_code"].strip():
            raise InvalidResultDataError("Test code cannot be empty")

        # Validate reference range if both provided
        if ("reference_range_low" in result_data and
            "reference_range_high" in result_data and
            result_data["reference_range_low"] is not None and
            result_data["reference_range_high"] is not None):

            try:
                low = float(result_data["reference_range_low"])
                high = float(result_data["reference_range_high"])
                if low > high:
                    raise InvalidResultDataError(
                        "Reference range low cannot be greater than high"
                    )
            except (ValueError, TypeError) as e:
                raise InvalidResultDataError(
                    f"Invalid reference range values: {str(e)}"
                )

        return result_data

    def update_result_status(
        self,
        tenant_id: str,
        result_id: str,
        status: InstrumentResultStatus
    ) -> InstrumentResult:
        """
        Update result status.

        Args:
            tenant_id: Tenant identifier
            result_id: Result identifier
            status: New status

        Returns:
            Updated result

        Raises:
            InstrumentResultNotFoundError: If result not found
        """
        result = self.get_result(tenant_id, result_id)
        result.status = status
        result.update_timestamp()

        return self._result_repo.update(result)

    def link_result_to_order(
        self,
        tenant_id: str,
        result_id: str,
        order_id: str
    ) -> InstrumentResult:
        """
        Link a result to an order.

        Args:
            tenant_id: Tenant identifier
            result_id: Result identifier
            order_id: Order identifier

        Returns:
            Updated result

        Raises:
            InstrumentResultNotFoundError: If result not found
        """
        result = self.get_result(tenant_id, result_id)
        result.order_id = order_id
        result.update_timestamp()

        return self._result_repo.update(result)
