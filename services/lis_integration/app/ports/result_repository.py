"""Result repository port."""

import abc
from typing import Optional
from datetime import datetime
from app.models import Result, ResultStatus, UploadStatus


class IResultRepository(abc.ABC):
    """
    Port: Abstract contract for result data persistence with multi-tenant support.

    All queries automatically filter by tenant_id to ensure data isolation.
    Supports tracking verification and upload status for bidirectional communication.
    """

    @abc.abstractmethod
    def create(self, result: Result) -> Result:
        """
        Create a new result.

        Args:
            result: Result entity to create (must have tenant_id and sample_id set)

        Returns:
            Created result with generated ID

        Raises:
            DuplicateResultError: If result with same external_lis_result_id exists in tenant
            ValueError: If required fields are missing
        """
        pass

    @abc.abstractmethod
    def get_by_id(self, result_id: str, tenant_id: str) -> Optional[Result]:
        """
        Retrieve a result by ID, ensuring it belongs to the tenant.

        Args:
            result_id: Unique result identifier
            tenant_id: Tenant identifier for isolation

        Returns:
            Result if found and belongs to tenant, None otherwise
        """
        pass

    @abc.abstractmethod
    def get_by_external_id(self, external_lis_result_id: str, tenant_id: str) -> Optional[Result]:
        """
        Retrieve a result by external LIS ID within a tenant.

        Args:
            external_lis_result_id: External LIS result identifier
            tenant_id: Tenant identifier for isolation

        Returns:
            Result if found in tenant, None otherwise
        """
        pass

    @abc.abstractmethod
    def list_by_sample(self, sample_id: str, tenant_id: str) -> list[Result]:
        """
        List all results for a specific sample.

        Args:
            sample_id: Sample identifier
            tenant_id: Tenant identifier for isolation

        Returns:
            List of results for the sample
        """
        pass

    @abc.abstractmethod
    def list_by_tenant(
        self,
        tenant_id: str,
        status: Optional[ResultStatus] = None,
        upload_status: Optional[UploadStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[Result], int]:
        """
        List results for a tenant with optional filtering.

        Args:
            tenant_id: Tenant identifier
            status: Optional verification status filter
            upload_status: Optional upload status filter
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (list of results, total count)
        """
        pass

    @abc.abstractmethod
    def list_by_upload_status(
        self,
        tenant_id: str,
        upload_status: UploadStatus,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[Result], int]:
        """
        List results by upload status for a tenant.

        Args:
            tenant_id: Tenant identifier
            upload_status: Upload status filter
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (list of results, total count)
        """
        pass

    @abc.abstractmethod
    def list_for_upload(
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
            limit: Maximum number of records to return

        Returns:
            Tuple of (list of results with pending upload status, total count)
        """
        pass

    @abc.abstractmethod
    def update(self, result: Result) -> Result:
        """
        Update an existing result.

        Args:
            result: Result with updated fields

        Returns:
            Updated result

        Raises:
            ResultNotFoundError: If result doesn't exist
            ResultImmutableError: If trying to modify a verified or rejected result
        """
        pass

    @abc.abstractmethod
    def update_verification_status(
        self,
        result_id: str,
        tenant_id: str,
        status: ResultStatus,
        method: Optional[str] = None
    ) -> Result:
        """
        Update only the verification status of a result.

        Args:
            result_id: Result identifier
            tenant_id: Tenant identifier
            status: New verification status
            method: Optional verification method ("auto" or "manual")

        Returns:
            Updated result

        Raises:
            ResultNotFoundError: If result doesn't exist
        """
        pass

    @abc.abstractmethod
    def update_upload_status(
        self,
        result_id: str,
        tenant_id: str,
        upload_status: UploadStatus,
        failure_reason: Optional[str] = None
    ) -> Result:
        """
        Update upload status tracking fields for a result.

        Args:
            result_id: Result identifier
            tenant_id: Tenant identifier
            upload_status: New upload status
            failure_reason: Optional reason for failure

        Returns:
            Updated result

        Raises:
            ResultNotFoundError: If result doesn't exist
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
