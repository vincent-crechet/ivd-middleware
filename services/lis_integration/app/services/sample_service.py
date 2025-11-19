"""Sample business logic service."""

from typing import Optional
from datetime import datetime

from app.models import Sample, SampleStatus
from app.ports import ISampleRepository
from app.exceptions import SampleNotFoundError, InvalidSampleDataError


class SampleService:
    """
    Service for managing samples with business logic.

    Handles creation, retrieval, querying, and status management of samples.
    Depends only on ISampleRepository port (not on any specific adapter).
    """

    def __init__(self, sample_repo: ISampleRepository):
        """
        Initialize sample service with repository.

        Args:
            sample_repo: Sample repository (injected port)
        """
        self._sample_repo = sample_repo

    def create_sample(
        self,
        tenant_id: str,
        external_lis_id: str,
        patient_id: str,
        specimen_type: str,
        collection_date: datetime,
        received_date: datetime
    ) -> Sample:
        """
        Create a new sample with validation.

        Args:
            tenant_id: Tenant identifier
            external_lis_id: External LIS sample ID
            patient_id: Patient identifier
            specimen_type: Type of specimen (blood, urine, etc.)
            collection_date: When sample was collected
            received_date: When sample was received

        Returns:
            Created sample

        Raises:
            InvalidSampleDataError: If data validation fails
            DuplicateSampleError: If sample with same external_lis_id exists
        """
        # Validate dates
        if collection_date > received_date:
            raise InvalidSampleDataError(
                "Collection date cannot be after received date"
            )

        # Create sample
        sample = Sample(
            tenant_id=tenant_id,
            external_lis_id=external_lis_id,
            patient_id=patient_id,
            specimen_type=specimen_type,
            collection_date=collection_date,
            received_date=received_date,
            status=SampleStatus.PENDING
        )

        # Persist via repository
        return self._sample_repo.create(sample)

    def get_sample(self, sample_id: str, tenant_id: str) -> Sample:
        """
        Get a sample by ID.

        Args:
            sample_id: Sample identifier
            tenant_id: Tenant identifier (for isolation)

        Returns:
            Sample

        Raises:
            SampleNotFoundError: If sample not found
        """
        sample = self._sample_repo.get_by_id(sample_id, tenant_id)
        if not sample:
            raise SampleNotFoundError(f"Sample '{sample_id}' not found")
        return sample

    def get_sample_by_external_id(self, external_lis_id: str, tenant_id: str) -> Optional[Sample]:
        """
        Get a sample by external LIS ID.

        Args:
            external_lis_id: External LIS sample ID
            tenant_id: Tenant identifier (for isolation)

        Returns:
            Sample if found, None otherwise
        """
        return self._sample_repo.get_by_external_id(external_lis_id, tenant_id)

    def search_samples(
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
        Search samples with optional filters.

        Args:
            tenant_id: Tenant identifier
            patient_id: Optional patient ID (partial match)
            start_date: Optional start of collection date range
            end_date: Optional end of collection date range
            status: Optional sample status
            specimen_type: Optional specimen type
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            Tuple of (samples, total count)
        """
        return self._sample_repo.list_by_tenant(
            tenant_id=tenant_id,
            patient_id=patient_id,
            start_date=start_date,
            end_date=end_date,
            status=status,
            specimen_type=specimen_type,
            skip=skip,
            limit=limit
        )

    def update_sample_status(
        self,
        sample_id: str,
        tenant_id: str,
        new_status: SampleStatus
    ) -> Sample:
        """
        Update a sample's status.

        Args:
            sample_id: Sample identifier
            tenant_id: Tenant identifier
            new_status: New status

        Returns:
            Updated sample

        Raises:
            SampleNotFoundError: If sample not found
        """
        sample = self.get_sample(sample_id, tenant_id)
        sample.status = new_status
        sample.update_timestamp()
        return self._sample_repo.update(sample)

    def delete_sample(self, sample_id: str, tenant_id: str) -> bool:
        """
        Delete a sample.

        Args:
            sample_id: Sample identifier
            tenant_id: Tenant identifier

        Returns:
            True if deleted, False if not found
        """
        return self._sample_repo.delete(sample_id, tenant_id)
