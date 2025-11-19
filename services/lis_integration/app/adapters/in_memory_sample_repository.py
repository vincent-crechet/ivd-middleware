"""In-memory implementation of sample repository for testing."""

from typing import Optional
from datetime import datetime
import uuid
import copy

from app.ports import ISampleRepository
from app.models import Sample, SampleStatus
from app.exceptions import DuplicateSampleError, SampleNotFoundError


class InMemorySampleRepository(ISampleRepository):
    """In-memory implementation of sample repository for testing."""

    def __init__(self):
        """Initialize with empty storage."""
        self._samples: dict[str, Sample] = {}

    def create(self, sample: Sample) -> Sample:
        """Create a new sample in memory."""
        if not sample.tenant_id:
            raise ValueError("Sample must have a tenant_id")

        # Check for duplicate
        for existing in self._samples.values():
            if (existing.external_lis_id == sample.external_lis_id and
                existing.tenant_id == sample.tenant_id):
                raise DuplicateSampleError(
                    f"Sample with external_lis_id '{sample.external_lis_id}' already exists in tenant"
                )

        if not sample.id:
            sample.id = str(uuid.uuid4())

        # Store copy to avoid external mutations
        self._samples[sample.id] = copy.deepcopy(sample)
        return copy.deepcopy(self._samples[sample.id])

    def get_by_id(self, sample_id: str, tenant_id: str) -> Optional[Sample]:
        """Retrieve sample by ID, ensuring it belongs to tenant."""
        sample = self._samples.get(sample_id)
        if sample and sample.tenant_id == tenant_id:
            return copy.deepcopy(sample)
        return None

    def get_by_external_id(self, external_lis_id: str, tenant_id: str) -> Optional[Sample]:
        """Retrieve sample by external LIS ID within tenant."""
        for sample in self._samples.values():
            if sample.external_lis_id == external_lis_id and sample.tenant_id == tenant_id:
                return copy.deepcopy(sample)
        return None

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
        """List samples for a tenant with optional filtering."""
        # Filter by tenant
        samples = [s for s in self._samples.values() if s.tenant_id == tenant_id]

        # Apply filters
        if patient_id:
            samples = [s for s in samples if patient_id.lower() in s.patient_id.lower()]
        if start_date:
            samples = [s for s in samples if s.collection_date >= start_date]
        if end_date:
            samples = [s for s in samples if s.collection_date <= end_date]
        if status:
            samples = [s for s in samples if s.status == status]
        if specimen_type:
            samples = [s for s in samples if s.specimen_type == specimen_type]

        # Sort by collection_date (newest first)
        samples.sort(key=lambda s: s.collection_date, reverse=True)

        total = len(samples)
        paginated = samples[skip:skip + limit]

        return [copy.deepcopy(s) for s in paginated], total

    def update(self, sample: Sample) -> Sample:
        """Update existing sample."""
        if sample.id not in self._samples:
            raise SampleNotFoundError(f"Sample with id '{sample.id}' not found")

        existing = self._samples[sample.id]
        if existing.tenant_id != sample.tenant_id:
            raise SampleNotFoundError(f"Sample with id '{sample.id}' not found")

        sample.update_timestamp()
        self._samples[sample.id] = copy.deepcopy(sample)
        return copy.deepcopy(sample)

    def delete(self, sample_id: str, tenant_id: str) -> bool:
        """Delete a sample, ensuring it belongs to the tenant."""
        sample = self._samples.get(sample_id)
        if sample and sample.tenant_id == tenant_id:
            del self._samples[sample_id]
            return True
        return False
