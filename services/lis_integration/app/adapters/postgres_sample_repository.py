"""PostgreSQL implementation of sample repository."""

from sqlmodel import Session, select
from typing import Optional
from datetime import datetime
import uuid

from app.ports import ISampleRepository
from app.models import Sample, SampleStatus
from app.exceptions import DuplicateSampleError, SampleNotFoundError


class PostgresSampleRepository(ISampleRepository):
    """PostgreSQL implementation of sample repository with multi-tenant support."""

    def __init__(self, session: Session):
        """
        Initialize with database session.

        Args:
            session: SQLModel database session
        """
        self._session = session

    def create(self, sample: Sample) -> Sample:
        """Create a new sample in PostgreSQL."""
        # Validate tenant_id is set
        if not sample.tenant_id:
            raise ValueError("Sample must have a tenant_id")

        # Check for duplicate external LIS ID within tenant
        existing = self._session.exec(
            select(Sample).where(
                Sample.external_lis_id == sample.external_lis_id,
                Sample.tenant_id == sample.tenant_id
            )
        ).first()

        if existing:
            raise DuplicateSampleError(
                f"Sample with external_lis_id '{sample.external_lis_id}' already exists in tenant"
            )

        # Generate ID if not provided
        if not sample.id:
            sample.id = str(uuid.uuid4())

        self._session.add(sample)
        self._session.commit()
        self._session.refresh(sample)
        return sample

    def get_by_id(self, sample_id: str, tenant_id: str) -> Optional[Sample]:
        """Retrieve sample by ID, ensuring it belongs to tenant."""
        statement = select(Sample).where(
            Sample.id == sample_id,
            Sample.tenant_id == tenant_id
        )
        return self._session.exec(statement).first()

    def get_by_external_id(self, external_lis_id: str, tenant_id: str) -> Optional[Sample]:
        """Retrieve sample by external LIS ID within tenant."""
        statement = select(Sample).where(
            Sample.external_lis_id == external_lis_id,
            Sample.tenant_id == tenant_id
        )
        return self._session.exec(statement).first()

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
        # Build base query
        query = select(Sample).where(Sample.tenant_id == tenant_id)

        # Apply filters
        if patient_id:
            query = query.where(Sample.patient_id.ilike(f"%{patient_id}%"))
        if start_date:
            query = query.where(Sample.collection_date >= start_date)
        if end_date:
            query = query.where(Sample.collection_date <= end_date)
        if status:
            query = query.where(Sample.status == status)
        if specimen_type:
            query = query.where(Sample.specimen_type == specimen_type)

        # Get total count before pagination
        count_query = select(Sample).where(Sample.tenant_id == tenant_id)
        if patient_id:
            count_query = count_query.where(Sample.patient_id.ilike(f"%{patient_id}%"))
        if start_date:
            count_query = count_query.where(Sample.collection_date >= start_date)
        if end_date:
            count_query = count_query.where(Sample.collection_date <= end_date)
        if status:
            count_query = count_query.where(Sample.status == status)
        if specimen_type:
            count_query = count_query.where(Sample.specimen_type == specimen_type)

        total = len(self._session.exec(count_query).all())

        # Sort by collection_date (newest first) and apply pagination
        query = query.order_by(Sample.collection_date.desc()).offset(skip).limit(limit)
        samples = list(self._session.exec(query).all())

        return samples, total

    def update(self, sample: Sample) -> Sample:
        """Update existing sample."""
        with self._session.no_autoflush:
            existing = self.get_by_id(sample.id, sample.tenant_id)
            if not existing:
                raise SampleNotFoundError(f"Sample with id '{sample.id}' not found")

            # Update fields
            existing.patient_id = sample.patient_id
            existing.specimen_type = sample.specimen_type
            existing.collection_date = sample.collection_date
            existing.received_date = sample.received_date
            existing.status = sample.status
            existing.update_timestamp()

        self._session.add(existing)
        self._session.commit()
        self._session.refresh(existing)
        return existing

    def delete(self, sample_id: str, tenant_id: str) -> bool:
        """Delete a sample, ensuring it belongs to the tenant."""
        sample = self.get_by_id(sample_id, tenant_id)
        if not sample:
            return False

        self._session.delete(sample)
        self._session.commit()
        return True
