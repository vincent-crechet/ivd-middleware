"""Sample repository port."""

import abc
from typing import Optional
from datetime import datetime
from app.models import Sample, SampleStatus


class ISampleRepository(abc.ABC):
    """
    Port: Abstract contract for sample data persistence with multi-tenant support.

    All queries automatically filter by tenant_id to ensure data isolation.
    """

    @abc.abstractmethod
    def create(self, sample: Sample) -> Sample:
        """
        Create a new sample.

        Args:
            sample: Sample entity to create (must have tenant_id set)

        Returns:
            Created sample with generated ID

        Raises:
            DuplicateSampleError: If sample with same external_lis_id exists in tenant
            ValueError: If sample doesn't have tenant_id set
        """
        pass

    @abc.abstractmethod
    def get_by_id(self, sample_id: str, tenant_id: str) -> Optional[Sample]:
        """
        Retrieve a sample by ID, ensuring it belongs to the tenant.

        Args:
            sample_id: Unique sample identifier
            tenant_id: Tenant identifier for isolation

        Returns:
            Sample if found and belongs to tenant, None otherwise
        """
        pass

    @abc.abstractmethod
    def get_by_external_id(self, external_lis_id: str, tenant_id: str) -> Optional[Sample]:
        """
        Retrieve a sample by external LIS ID within a tenant.

        Args:
            external_lis_id: External LIS identifier
            tenant_id: Tenant identifier for isolation

        Returns:
            Sample if found in tenant, None otherwise
        """
        pass

    @abc.abstractmethod
    def list_by_tenant(
        self,
        tenant_id: str,
        patient_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[SampleStatus] = None,
        specimen_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[Sample], int]:
        """
        List samples for a tenant with optional filtering.

        Args:
            tenant_id: Tenant identifier
            patient_id: Optional patient ID (partial match)
            start_date: Optional start of collection date range
            end_date: Optional end of collection date range
            status: Optional sample status filter
            specimen_type: Optional specimen type filter
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (list of samples, total count)
        """
        pass

    @abc.abstractmethod
    def update(self, sample: Sample) -> Sample:
        """
        Update an existing sample.

        Args:
            sample: Sample with updated fields

        Returns:
            Updated sample

        Raises:
            SampleNotFoundError: If sample doesn't exist
        """
        pass

    @abc.abstractmethod
    def delete(self, sample_id: str, tenant_id: str) -> bool:
        """
        Delete a sample, ensuring it belongs to the tenant.

        Args:
            sample_id: ID of sample to delete
            tenant_id: Tenant identifier for isolation

        Returns:
            True if deleted, False if not found
        """
        pass
