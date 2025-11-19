"""Result business logic service."""

from typing import Optional
from datetime import datetime

from app.models import Result, ResultStatus, UploadStatus
from app.ports import IResultRepository
from app.exceptions import ResultNotFoundError, InvalidResultDataError, ResultImmutableError


class ResultService:
    """
    Service for managing results with business logic.

    Handles creation, retrieval, querying, verification status updates,
    and upload tracking for bidirectional communication with LIS.
    Depends only on IResultRepository port.
    """

    def __init__(self, result_repo: IResultRepository):
        """
        Initialize result service with repository.

        Args:
            result_repo: Result repository (injected port)
        """
        self._result_repo = result_repo

    def create_result(
        self,
        tenant_id: str,
        sample_id: str,
        external_lis_result_id: str,
        test_code: str,
        test_name: str,
        value: Optional[str],
        unit: Optional[str],
        reference_range_low: Optional[float] = None,
        reference_range_high: Optional[float] = None,
        lis_flags: Optional[str] = None
    ) -> Result:
        """
        Create a new result with validation.

        Args:
            tenant_id: Tenant identifier
            sample_id: Parent sample ID
            external_lis_result_id: External LIS result ID
            test_code: Test code
            test_name: Test name
            value: Result value
            unit: Result unit
            reference_range_low: Reference range low value
            reference_range_high: Reference range high value
            lis_flags: LIS flags (H, L, C, etc.)

        Returns:
            Created result

        Raises:
            InvalidResultDataError: If data validation fails
            DuplicateResultError: If result with same external_lis_result_id exists
        """
        # Validate reference range
        if (reference_range_low is not None and reference_range_high is not None and
            reference_range_low > reference_range_high):
            raise InvalidResultDataError(
                "Reference range low cannot be greater than high"
            )

        # Create result
        result = Result(
            tenant_id=tenant_id,
            sample_id=sample_id,
            external_lis_result_id=external_lis_result_id,
            test_code=test_code,
            test_name=test_name,
            value=value,
            unit=unit,
            reference_range_low=reference_range_low,
            reference_range_high=reference_range_high,
            lis_flags=lis_flags,
            verification_status=ResultStatus.PENDING,
            upload_status=UploadStatus.PENDING
        )

        # Persist via repository
        return self._result_repo.create(result)

    def get_result(self, result_id: str, tenant_id: str) -> Result:
        """
        Get a result by ID.

        Args:
            result_id: Result identifier
            tenant_id: Tenant identifier (for isolation)

        Returns:
            Result

        Raises:
            ResultNotFoundError: If result not found
        """
        result = self._result_repo.get_by_id(result_id, tenant_id)
        if not result:
            raise ResultNotFoundError(f"Result '{result_id}' not found")
        return result

    def get_result_by_external_id(self, external_lis_result_id: str, tenant_id: str) -> Optional[Result]:
        """
        Get a result by external LIS ID.

        Args:
            external_lis_result_id: External LIS result ID
            tenant_id: Tenant identifier

        Returns:
            Result if found, None otherwise
        """
        return self._result_repo.get_by_external_id(external_lis_result_id, tenant_id)

    def list_results_by_sample(self, sample_id: str, tenant_id: str) -> list[Result]:
        """
        List all results for a sample.

        Args:
            sample_id: Sample identifier
            tenant_id: Tenant identifier

        Returns:
            List of results
        """
        return self._result_repo.list_by_sample(sample_id, tenant_id)

    def search_results(
        self,
        tenant_id: str,
        status: Optional[ResultStatus] = None,
        upload_status: Optional[UploadStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[Result], int]:
        """
        Search results with optional filters.

        Args:
            tenant_id: Tenant identifier
            status: Optional verification status
            upload_status: Optional upload status
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            Tuple of (results, total count)
        """
        return self._result_repo.list_by_tenant(
            tenant_id=tenant_id,
            status=status,
            upload_status=upload_status,
            skip=skip,
            limit=limit
        )

    def list_results_for_upload(
        self,
        tenant_id: str,
        include_verified: bool = True,
        include_rejected: bool = False,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[Result], int]:
        """
        List results ready for upload to LIS.

        Args:
            tenant_id: Tenant identifier
            include_verified: Include verified results
            include_rejected: Include rejected results
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            Tuple of (results with pending upload status, total count)
        """
        return self._result_repo.list_for_upload(
            tenant_id=tenant_id,
            include_verified=include_verified,
            include_rejected=include_rejected,
            skip=skip,
            limit=limit
        )

    def update_verification_status(
        self,
        result_id: str,
        tenant_id: str,
        status: ResultStatus,
        method: Optional[str] = None
    ) -> Result:
        """
        Update result verification status (from Verification Service).

        Args:
            result_id: Result identifier
            tenant_id: Tenant identifier
            status: New verification status
            method: Verification method ("auto" or "manual")

        Returns:
            Updated result

        Raises:
            ResultNotFoundError: If result not found
        """
        return self._result_repo.update_verification_status(
            result_id=result_id,
            tenant_id=tenant_id,
            status=status,
            method=method
        )

    def update_upload_status(
        self,
        result_id: str,
        tenant_id: str,
        upload_status: UploadStatus,
        failure_reason: Optional[str] = None
    ) -> Result:
        """
        Update result upload status (for LIS communication).

        Args:
            result_id: Result identifier
            tenant_id: Tenant identifier
            upload_status: New upload status
            failure_reason: Optional failure reason

        Returns:
            Updated result

        Raises:
            ResultNotFoundError: If result not found
        """
        return self._result_repo.update_upload_status(
            result_id=result_id,
            tenant_id=tenant_id,
            upload_status=upload_status,
            failure_reason=failure_reason
        )

    def mark_result_sent(self, result_id: str, tenant_id: str) -> Result:
        """
        Mark a result as successfully sent to LIS.

        Args:
            result_id: Result identifier
            tenant_id: Tenant identifier

        Returns:
            Updated result
        """
        return self.update_upload_status(
            result_id=result_id,
            tenant_id=tenant_id,
            upload_status=UploadStatus.SENT,
            failure_reason=None
        )

    def mark_result_upload_failed(
        self,
        result_id: str,
        tenant_id: str,
        failure_reason: str
    ) -> Result:
        """
        Mark a result as failed to upload.

        Args:
            result_id: Result identifier
            tenant_id: Tenant identifier
            failure_reason: Reason for failure

        Returns:
            Updated result
        """
        return self.update_upload_status(
            result_id=result_id,
            tenant_id=tenant_id,
            upload_status=UploadStatus.FAILED,
            failure_reason=failure_reason
        )

    def delete_result(self, result_id: str, tenant_id: str) -> bool:
        """
        Delete a result.

        Args:
            result_id: Result identifier
            tenant_id: Tenant identifier

        Returns:
            True if deleted, False if not found
        """
        return self._result_repo.delete(result_id, tenant_id)
